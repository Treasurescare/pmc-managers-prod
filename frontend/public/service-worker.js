/* PMC v46p Progressive Web App service worker.
 *
 * Strategy:
 *   - App shell (HTML + JS + CSS + fonts + crest) — stale-while-revalidate.
 *     Users get instant paint from cache, then a background fetch refreshes it.
 *   - API traffic (/api/*) — network-only. Never cache bid/evaluation/auction
 *     data; those must always be fresh. This resolves the v46d regression
 *     where the old offline-first SW served stale bundles after deploys.
 *   - Housekeeping — any cache older than 30 days is deleted on activate.
 *
 * Bumping CACHE_VERSION on every deploy invalidates the shell within one
 * page load; no manual "clear cache" needed.
 */

const CACHE_VERSION = "pmc-shell-v46p";
const SHELL_ASSETS = [
  "/",
  "/manifest.json",
  "/pmc-logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_VERSION);
    try { await cache.addAll(SHELL_ASSETS); } catch (_) { /* offline install */ }
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    // Nuke any previous version + anything older than 30 days.
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => (k === CACHE_VERSION ? null : caches.delete(k))));
    try { await self.clients.claim(); } catch (_) {}
  })());
});

/**
 * Route every fetch:
 *   - navigation (SPA) → network-first, fall back to cached shell.
 *   - /api/* → network-only, no caching.
 *   - static assets → stale-while-revalidate.
 */
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Same-origin only — never cache cross-origin analytics beacons etc.
  if (url.origin !== self.location.origin) return;

  // 1. API traffic — always network.
  if (url.pathname.startsWith("/api/")) {
    return; // let the browser handle it, no interception
  }

  // 2. Document navigations — network-first with shell fallback.
  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        return fresh;
      } catch (_) {
        const cache = await caches.open(CACHE_VERSION);
        return (await cache.match("/")) || Response.error();
      }
    })());
    return;
  }

  // 3. Static assets — stale-while-revalidate.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_VERSION);
    const cached = await cache.match(req);
    const fetchPromise = fetch(req)
      .then((res) => {
        if (res && res.status === 200 && res.type === "basic") {
          cache.put(req, res.clone()).catch(() => {});
        }
        return res;
      })
      .catch(() => cached);
    return cached || fetchPromise;
  })());
});
