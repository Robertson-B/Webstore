// Bump cache name when changing caching rules so clients pick up updates
const CACHE_NAME = 'cardhaven-v5';
const ASSETS = [
  '/',
  '/offline',
  '/static/manifest.json',
  '/static/img/icons/icon-192.svg',
  '/static/img/icons/icon-512.svg',
  '/static/img/favicon/desktop-icon.svg',
  '/static/img/favicon/desktop-icon-192.png',
  '/static/img/favicon/desktop-icon-512.png',
  '/static/img/favicon/favicon-v2.ico'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).catch(()=>{})
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // navigation requests: by default use network-first fallback to offline,
  // but for product list/detail pages we prefer cache-first runtime caching
  if (req.mode === 'navigate') {
    const path = url.pathname || '/';
      // For product listing and product detail pages use network-first so
      // changes made on the server (archive/unarchive) are reflected quickly.
      if (path.startsWith('/products') || path.startsWith('/product')) {
        event.respondWith(
          fetch(req).then(networkRes => {
            // Update runtime cache for offline use when successful
            if (networkRes && networkRes.status === 200) {
              const copy = networkRes.clone();
              caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
            }
            return networkRes;
          }).catch(() => {
            // If network fails, fall back to any cached copy or the offline page
            return caches.match(req).then(cached => cached || caches.match('/offline'));
          })
        );
        return;
      }

    // default navigation behavior: network-first then offline fallback
    event.respondWith(
      fetch(req).then(res => res).catch(() => caches.match('/offline'))
    );
    return;
  }

  // static assets: cache-first
  if (ASSETS.includes(url.pathname) || (url.origin === location.origin && url.pathname.startsWith('/static/'))) {
    event.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(networkRes => {
        caches.open(CACHE_NAME).then(cache => cache.put(req, networkRes.clone()));
        return networkRes;
      }).catch(()=>{}))
    );
    return;
  }

  // default: network
  event.respondWith(fetch(req));
});
