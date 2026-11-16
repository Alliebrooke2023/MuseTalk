// web/sw.js — minimal offline shell for the Binks PWA.
// Caches the app UI so it installs/opens like a native app. Live camera
// feeds and API calls always go to the network (never cached).
const CACHE = 'binks-v1';
const SHELL = ['./', './index.html', './styles.css', './app.js',
  './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return; // never cache live data
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
