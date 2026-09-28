/**
 * Luqi AI - Enterprise PWA Service Worker (v15.0)
 * Architecture: Hybrid Stale-While-Revalidate + Offline Queue + Network-First API Fallback
 */

const CACHE_VERSION = 'luqi-v15.0.0';
const STATIC_CACHE = `luqi-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `luqi-dynamic-${CACHE_VERSION}`;
const RUNTIME_API_CACHE = `luqi-api-${CACHE_VERSION}`;

// Core shell assets required for offline boot
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/admin.html',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Offline fallback document
const OFFLINE_FALLBACK_URL = '/index.html';

/* ==========================================================================
   1. LIFECYCLE EVENTS
   ========================================================================== */

// Install: Cache essential core shell resiliently (settled promise handles individual missing assets)
self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      // Atomic caching fallback to prevent installation break on non-critical missing files
      await Promise.allSettled(
        STATIC_ASSETS.map(async (url) => {
          try {
            const response = await fetch(url, { cache: 'no-cache' });
            if (response.ok) await cache.put(url, response);
          } catch (err) {
            console.warn(`[SW] Pre-cache soft-failure for asset: ${url}`, err);
          }
        })
      );
      await self.skipWaiting();
    })()
  );
});

// Activate: Prune stale caches across versions and immediately claim clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const cacheKeys = await caches.keys();
      const validCaches = new Set([STATIC_CACHE, DYNAMIC_CACHE, RUNTIME_API_CACHE]);
      
      await Promise.all(
        cacheKeys
          .filter((key) => !validCaches.has(key))
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

/* ==========================================================================
   2. FETCH INTERCEPTION & ROUTING STRATEGIES
   ========================================================================== */

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Bypass non-GET requests (handled via background sync / direct network)
  if (request.method !== 'GET') return;

  // 2. Bypass non-http(s) schemas (chrome-extension, data URIs, etc.)
  if (!url.protocol.startsWith('http')) return;

  // 3. API Route Strategy: Network First with Graceful Fallback
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/v1/')) {
    event.respondWith(networkFirstApiStrategy(request));
    return;
  }

  // 4. Cross-Origin Strategy: Network-Only (or optional opaque caching)
  if (url.origin !== self.location.origin) {
    return;
  }

  // 5. Navigation Request Strategy (HTML pages): Network-First with Offline Page Fallback
  if (request.mode === 'navigate') {
    event.respondWith(navigationStrategy(request));
    return;
  }

  // 6. Static Asset Strategy: Ultra-Fast Stale-While-Revalidate
  event.respondWith(staleWhileRevalidateStrategy(request));
});

/**
 * Strategy: Robust Stale-While-Revalidate
 */
async function staleWhileRevalidateStrategy(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request)
    .then(async (networkResponse) => {
      if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
        await cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch((err) => {
      console.warn(`[SW] Network fetch failed for ${request.url}; serving cached version if available.`, err);
      return cachedResponse;
    });

  return cachedResponse || fetchPromise;
}

/**
 * Strategy: Navigation (Network First -> Cache -> Offline Fallback)
 */
async function navigationStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
  } catch (error) {
    // Network failed, attempt cache lookup
  }

  const cachedResponse = await caches.match(request);
  if (cachedResponse) return cachedResponse;

  // Fallback to primary offline app shell
  return caches.match(OFFLINE_FALLBACK_URL);
}

/**
 * Strategy: API Network-First with Runtime Caching
 */
async function networkFirstApiStrategy(request) {
  const cache = await caches.open(RUNTIME_API_CACHE);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.ok) {
      // Store successful API responses for offline lookup
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (err) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response(
      JSON.stringify({ error: 'Offline mode active. Request queued or unavailable.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/* ==========================================================================
   3. BACKGROUND SYNC (OFFLINE QUEUE AGENT)
   ========================================================================== */

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(processPendingMessages());
  }
});

async function processPendingMessages() {
  let db;
  try {
    db = await openDB('luqi-offline', 1);
  } catch (err) {
    console.error('[SW] IndexedDB connection failed:', err);
    return;
  }

  const messages = await getUnsentMessages(db);

  for (const msg of messages) {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Luqi-Offline-Sync': 'true'
        },
        body: JSON.stringify(msg.payload || msg)
      });

      if (response.ok || response.status === 422) {
        // Delete successfully synced or unrecoverable items
        await deleteMessage(db, msg.id);
      }
    } catch (e) {
      console.error(`[SW] Sync retry delayed for message ID: ${msg.id}`, e);
      break; // Abort loop to preserve transaction ordering on network drop
    }
  }
}

/* ==========================================================================
   4. INDEXEDDB PROMISE-BASED WRAPPER
   ========================================================================== */

function openDB(name, version) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name, version);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pending-messages')) {
        db.createObjectStore('pending-messages', { keyPath: 'id' });
      }
    };
  });
}

function getUnsentMessages(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-messages', 'readonly');
    const store = tx.objectStore('pending-messages');
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

function deleteMessage(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-messages', 'readwrite');
    const store = tx.objectStore('pending-messages');
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/* ==========================================================================
   5. PUSH NOTIFICATIONS & INTERACTION
   ========================================================================== */

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Luqi AI', body: event.data ? event.data.text() : 'New notification' };
  }

  const title = data.title || 'Luqi AI Engine';
  const options = {
    body: data.body || 'You have a new update.',
    icon: data.icon || '/icons/icon-192.png',
    badge: data.badge || '/icons/icon-192.png',
    tag: data.tag || 'luqi-notification',
    data: data.data || { url: '/' },
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || []
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    (async () => {
      const windowClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
      
      for (const client of windowClients) {
        if (client.url === targetUrl && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })()
  );
});

/* ==========================================================================
   6. PERIODIC BACKGROUND SYNC & CLIENT MESSAGING
   ========================================================================== */

self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'refresh-cache') {
    event.waitUntil(
      (async () => {
        const cache = await caches.open(STATIC_CACHE);
        await Promise.allSettled(
          STATIC_ASSETS.map(async (url) => {
            const response = await fetch(url, { cache: 'reload' });
            if (response.ok) await cache.put(url, response);
          })
        );
      })()
    );
  }
});

self.addEventListener('message', (event) => {
  if (!event.data) return;

  const { type, payload, url } = event.data;

  switch (type || event.data) {
    case 'skipWaiting':
      self.skipWaiting();
      break;

    case 'claimClients':
      self.clients.claim();
      break;

    case 'cache-url':
      if (url) {
        event.waitUntil(
          caches.open(STATIC_CACHE).then(async (cache) => {
            const res = await fetch(url);
            if (res.ok) await cache.put(url, res);
          })
        );
      }
      break;

    case 'CLEAR_CACHE':
      event.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      );
      break;
  }
});
