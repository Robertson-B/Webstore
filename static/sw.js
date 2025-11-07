const CACHE_NAME = 'cardhaven-v2';
const ASSETS = [
  '/',
  '/offline',
  '/static/manifest.json',
  '/static/img/icons/icon-192.svg',
  '/static/img/icons/icon-512.svg'
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

  // navigation requests: network-first, fallback to offline
  if (req.mode === 'navigate') {
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
