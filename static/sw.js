const CACHE_NAME = 'luqi-ai-v1-static-assets';

// Foundational assets stored on the phone during first download.
// Served from ROOT (/) by FastAPI StaticFiles, so paths are root-relative.
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/app.js',
    '/mesh.js',
    '/avatar.js',
    '/skill_client.js',
    '/credentials.html',
    '/loadshedding.html',
    '/languages.html',
    '/dashboard.html',
    '/terms.html',
    '/automation.html',
    '/global_labs.html',
    '/sovereign.html',
    '/manifest.json',
    '/sw.js',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
    'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'
];

// Live voice/emotion streams must NEVER be cached - always hit the network
const LIVE_STREAM_HOSTS = ['elevenlabs.io', 'hume.ai', '/v1/voice/', '/v1/labs/terminal/'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Luqi-AI Cache Engine] Compressing and storing static assets locally...');
            // Per-URL caching: one missing asset can never fail the whole install
            return Promise.all(STATIC_ASSETS.map((url) =>
                cache.add(url).catch((err) => console.warn('[Luqi-AI SW] cache skip:', url, err))
            ));
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // 1. Live streams bypass the cache layer entirely
    if (LIVE_STREAM_HOSTS.some((host) => event.request.url.includes(host))) {
        return;
    }

    // 2. Everything else: NETWORK-FIRST with local cache fallback.
    //    Students always get the freshest content when connected; when data
    //    runs out or signal drops, the platform keeps running from local storage.
    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() =>
                caches.match(event.request).then((cached) => cached || caches.match('/index.html'))
            )
    );
});
