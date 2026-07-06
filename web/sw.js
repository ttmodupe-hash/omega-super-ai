const CACHE_NAME = 'luqi-v14';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/admin.html',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: stale-while-revalidate strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
        }
        return networkResponse;
      }).catch(() => cached);

      return cached || fetchPromise;
    })
  );
});

// Background sync for offline form submissions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages() {
  const db = await openDB('luqi-offline', 1);
  const messages = await db.getAll('pending-messages');
  for (const msg of messages) {
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(msg)
      });
      await db.delete('pending-messages', msg.id);
    } catch (e) {
      console.error('Sync failed for message:', msg.id);
    }
  }
}

// IndexedDB helper
function openDB(name, version) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name, version);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore('pending-messages', { keyPath: 'id' });
    };
  });
}

// Push notification handling
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'Luqi AI', {
      body: data.body || 'New notification',
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-72.png',
      tag: data.tag || 'default',
      requireInteraction: data.requireInteraction || false,
      actions: data.actions || []
    })
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      const url = event.notification.data?.url || '/';
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

// Periodic background sync for cache refresh
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'refresh-cache') {
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) => {
        return Promise.all(
          STATIC_ASSETS.map((url) =>
            fetch(url).then((response) => {
              if (response.status === 200) {
                return cache.put(url, response);
              }
            }).catch((err) => console.error('Failed to refresh:', url, err))
          )
        );
      })
    );
  }
});

// Message handling from clients
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
  if (event.data === 'claimClients') {
    self.clients.claim();
  }
  if (event.data.type === 'cache-url') {
    const url = event.data.url;
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) =>
        fetch(url).then((response) => {
          if (response.status === 200) {
            return cache.put(url, response);
          }
        })
      )
    );
  }
});