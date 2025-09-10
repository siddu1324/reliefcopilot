// backend/static/sw.js
const VERSION = 'v9';                            // <— bump this anytime you change UI files
const CACHE   = 'reliefcopilot-' + VERSION;

const ASSETS = [
  `/static/index.html?v=${VERSION}`,
  `/static/styles.css?v=${VERSION}`,
  `/static/app.js?v=${VERSION}`,
  `/static/manifest.webmanifest?v=${VERSION}`
];

self.addEventListener('install', (evt) => {
  evt.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS))
  );
  self.skipWaiting(); // activate immediately
});

self.addEventListener('activate', (evt) => {
  evt.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim(); // start controlling pages now
});

self.addEventListener('fetch', (evt) => {
  const url = new URL(evt.request.url);

  // Serve versioned static assets from cache first
  if (url.pathname.startsWith('/static/')) {
    evt.respondWith(
      caches.match(evt.request).then(res => res || fetch(evt.request))
    );
    return;
  }
});
