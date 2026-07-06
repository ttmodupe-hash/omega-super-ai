/**
 * Luqi AI v16 -- Service Worker
 * Provides offline caching, background sync, push notifications, and full PWA support.
 *
 * Cache Strategy:
 *   - Static assets: Cache-First  (luqi-static-v1)
 *   - API calls:     Network-First (luqi-api-v1)
 *   - Images/CDN:    Stale-While-Revalidate
 *
 * Features:
 *   1. Install  -- Pre-cache core static assets
 *   2. Activate -- Clean up old caches, claim clients
 *   3. Fetch    -- Route-based caching strategies
 *   4. Sync     -- Background sync for offline actions
 *   5. Push     -- Handle push notifications from backend
 *   6. Message  -- Communicate with main thread
 */

const STATIC_CACHE = 'luqi-static-v1';
const API_CACHE    = 'luqi-api-v1';
const CACHE_NAME   = 'luqi-ai-v16';

const CORE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

const STATIC_ASSETS = [
  ...CORE_ASSETS
  // CDN assets and additional static files are cached on-demand
];

// API routes that should use network-first strategy
const API_ROUTES = ['/api/'];

// Image/CDN hosts for stale-while-revalidate
const CDN_HOSTS = [
  'cdn.tailwindcss.com',
  'cdnjs.cloudflare.com',
  'unpkg.com'
];

/* ============================================================
   INSTALL -- Pre-cache core shell assets
   ============================================================ */
self.addEventListener('install', (event) => {
  console.log('[SW] Install event');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching core assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        // Force activation of new service worker immediately
        return self.skipWaiting();
      })
      .catch((err) => {
        console.error('[SW] Install failed:', err);
      })
  );
});

/* ============================================================
   ACTIVATE -- Clean up old caches, claim clients
   ============================================================ */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activate event');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            // Delete any cache that is not our current static or API cache
            return name !== STATIC_CACHE && name !== API_CACHE;
          })
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      // Take control of all clients immediately
      return self.clients.claim();
    }).then(() => {
      console.log('[SW] Activated and claimed clients');
    })
  );
});

/* ============================================================
   FETCH -- Route-based caching strategies
   ============================================================ */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-HTTP(S) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Skip browser extensions and non-GET for static
  if (request.method !== 'GET') {
    // Allow POST for sync replay via Background Sync
    return;
  }

  // Route: API calls -> Network-First strategy
  if (API_ROUTES.some(route => url.pathname.startsWith(route))) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Route: CDN assets -> Stale-While-Revalidate
  if (CDN_HOSTS.some(host => url.hostname.includes(host))) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  // Route: Navigation requests -> Network-First with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then((cache) => {
            cache.put(request, clone);
          });
          return response;
        })
        .catch(() => {
          return caches.match('/index.html').then((cached) => {
            if (cached) return cached;
            return new Response(
              '<!DOCTYPE html><html><head><title>Luqi AI - Offline</title>' +
              '<meta name="viewport" content="width=device-width,initial-scale=1">' +
              '<style>body{font-family:system-ui;display:flex;align-items:center;' +
              'justify-content:center;height:100vh;margin:0;background:#0f172a;color:#fff;' +
              'text-align:center}h1{margin:0;font-size:2rem}.btn{background:#4f46e5;' +
              'color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;' +
              'display:inline-block;margin-top:16px}</style></head>' +
              '<body><div><h1>Luqi AI</h1><p>You are offline.</p>' +
              '<a href="/" class="btn">Try Again</a></div></body></html>',
              { status: 200, headers: { 'Content-Type': 'text/html' } }
            );
          });
        })
    );
    return;
  }

  // Route: Static assets -> Cache-First strategy
  event.respondWith(cacheFirst(request, STATIC_CACHE));
});

/* ============================================================
   Caching Strategy Implementations
   ============================================================ */

/**
 * Cache-First: Serve from cache, fall back to network.
 * Updates cache in background after serving.
 */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    // Refresh cache in background (stale-while-revalidate lite)
    fetch(request)
      .then((response) => {
        if (response.ok) {
          cache.put(request, response.clone());
        }
      })
      .catch(() => {});
    return cached;
  }

  // Not in cache -- fetch from network
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    console.error('[SW] Cache-first fetch failed:', err);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network-First: Try network, fall back to cache.
 * Best for API calls that need fresh data but work offline.
 */
async function networkFirst(request) {
  const cache = await caches.open(API_CACHE);

  try {
    const response = await fetch(request);
    if (response.ok) {
      // Update cache with fresh response
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    console.warn('[SW] Network request failed, trying cache:', request.url);
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    // Return graceful offline JSON response
    return new Response(
      JSON.stringify({
        error: 'Offline -- no cached data available.',
        offline: true,
        timestamp: new Date().toISOString()
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Stale-While-Revalidate: Serve from cache immediately,
 * refresh from network in background.
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || fetchPromise;
}

/* ============================================================
   BACKGROUND SYNC -- Queue and retry failed requests
   ============================================================ */
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event.tag);

  if (event.tag === 'sync-messages') {
    event.waitUntil(syncPendingMessages());
  } else if (event.tag === 'sync-actions') {
    event.waitUntil(syncPendingActions());
  }
});

/**
 * Process queued chat messages sent while offline.
 */
async function syncPendingMessages() {
  const queue = await getQueuedItems('messages');
  console.log('[SW] Syncing', queue.length, 'pending messages');

  for (const msg of queue) {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(msg)
      });
      if (response.ok) {
        await removeQueuedItem('messages', msg.id);
        // Notify app of successful sync
        await notifyClients({ type: 'SYNC_SUCCESS', item: msg });
      }
    } catch (err) {
      console.error('[SW] Failed to sync message:', err);
    }
  }
}

/**
 * Process queued generic actions sent while offline.
 */
async function syncPendingActions() {
  const queue = await getQueuedItems('actions');
  console.log('[SW] Syncing', queue.length, 'pending actions');

  for (const action of queue) {
    try {
      const response = await fetch(action.url || '/api/actions', {
        method: action.method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.payload || action)
      });
      if (response.ok) {
        await removeQueuedItem('actions', action.id);
        await notifyClients({ type: 'SYNC_SUCCESS', item: action });
      }
    } catch (err) {
      console.error('[SW] Failed to sync action:', err);
    }
  }
}

/* ============================================================
   PUSH NOTIFICATIONS -- Handle incoming push events
   ============================================================ */
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');

  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Luqi AI', body: event.data ? event.data.text() : 'New notification' };
  }

  const title = data.title || 'Luqi AI';
  const options = {
    body: data.body || 'You have a new notification.',
    icon: data.icon || '/icons/icon-192.png',
    badge: data.badge || '/icons/icon-72.png',
    tag: data.tag || 'luqi-default',
    requireInteraction: data.requireInteraction || false,
    silent: data.silent || false,
    data: data.payload || { url: '/' },
    actions: data.actions || [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    // vibration pattern: pause, beep, pause, beep
    vibrate: data.vibrate || [200, 100, 200]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

/**
 * Handle notification click actions.
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action);
  event.notification.close();

  const data = event.notification.data || { url: '/' };
  const targetUrl = data.url || '/';

  if (event.action === 'dismiss') {
    return;
  }

  // Default or 'open' action: focus or open the app
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing client if open
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(targetUrl);
            return client.focus();
          }
        }
        // Open new window if no client exists
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetUrl);
        }
      })
  );
});

/**
 * Handle notification close events (dismissed without click).
 */
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification dismissed');
});

/* ============================================================
   MESSAGE HANDLER -- Communicate with main app thread
   ============================================================ */
self.addEventListener('message', (event) => {
  if (!event.data) return;

  const { type } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_VERSION':
      event.ports[0]?.postMessage({ version: CACHE_NAME });
      break;

    case 'CACHE_STATUS':
      event.waitUntil(
        caches.keys().then((names) => {
          const status = {
            caches: names,
            version: CACHE_NAME
          };
          event.ports[0]?.postMessage(status);
        })
      );
      break;

    case 'CLEAR_CACHES':
      event.waitUntil(
        caches.keys().then((names) =>
          Promise.all(names.map((n) => caches.delete(n)))
        ).then(() => {
          console.log('[SW] All caches cleared');
          event.ports[0]?.postMessage({ cleared: true });
        })
      );
      break;

    default:
      console.log('[SW] Unknown message type:', type);
  }
});

/* ============================================================
   INDEXEDDB HELPERS -- Offline queue management
   ============================================================ */

const DB_NAME = 'luqi-offline-db';
const DB_VERSION = 1;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('messages')) {
        db.createObjectStore('messages', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('actions')) {
        db.createObjectStore('actions', { keyPath: 'id' });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Retrieve queued items from a given store.
 */
async function getQueuedItems(storeName) {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const getAll = store.getAll();
      getAll.onsuccess = () => resolve(getAll.result || []);
      getAll.onerror = () => resolve([]);
    });
  } catch (err) {
    console.error('[SW] Failed to read queue:', err);
    return [];
  }
}

/**
 * Remove a single item from the queue store.
 */
async function removeQueuedItem(storeName, id) {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(storeName, 'readwrite');
      const store = tx.objectStore(storeName);
      store.delete(id);
      tx.oncomplete = resolve;
      tx.onerror = resolve;
    });
  } catch (err) {
    console.error('[SW] Failed to remove queued item:', err);
  }
}

/**
 * Notify all controlled clients of an event.
 */
async function notifyClients(message) {
  const clients = await self.clients.matchAll({ type: 'window' });
  for (const client of clients) {
    client.postMessage(message);
  }
}
