const CACHE_NAME = 'fareflow-v1';
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/favicon.svg',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

// Install - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch - network first, cache fallback
self.addEventListener('fetch', event => {
  // Skip WebSocket and API calls
  if (event.request.url.includes('/ws/') ||
      event.request.url.includes('/trips/') ||
      event.request.url.includes('/seats/') ||
      event.request.url.includes('/payments/') ||
      event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache successful responses
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache when offline
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // Offline fallback page
          return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
              <title>FareFlow - Offline</title>
              <meta name="viewport" content="width=device-width, initial-scale=1"/>
              <style>
                body { background:#060f1a; color:white; font-family:-apple-system,sans-serif;
                       display:flex; align-items:center; justify-content:center;
                       min-height:100vh; margin:0; text-align:center; padding:20px; }
                h1 { font-size:1.5rem; margin-bottom:10px; }
                p { color:rgba(255,255,255,0.5); }
                .emoji { font-size:3rem; margin-bottom:20px; }
              </style>
            </head>
            <body>
              <div>
                <div class="emoji">🚕</div>
                <h1>You're offline</h1>
                <p>Connect to the internet to use FareFlow</p>
              </div>
            </body>
            </html>
          `, { headers: { 'Content-Type': 'text/html' } });
        });
      })
  );
});

// Push notifications
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'FareFlow', {
      body: data.body || 'New notification',
      icon: '/static/icon-192.png',
      badge: '/static/favicon.svg',
      vibrate: [200, 100, 200],
    })
  );
});
