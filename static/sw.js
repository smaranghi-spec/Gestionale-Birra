/* Service Worker — PWA Gestionale Birrificio
 * Strategia: le pagine sono sempre richieste alla rete (dati sempre aggiornati e nessuna pagina
 * privata salvata sul dispositivo); in assenza di connessione mostra /offline.
 * Le risorse statiche (/static) usano cache-first.
 */
const VERSION = 'v1';
const STATIC_CACHE = 'static-' + VERSION;
const PRECACHE = ['/offline', '/static/icons/icon-192.png', '/static/manifest.webmanifest'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(STATIC_CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== STATIC_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(() => caches.match('/offline')));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
  }
});
