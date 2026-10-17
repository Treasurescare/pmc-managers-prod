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

const CACHE_VERSION = "pmc-shell-v54i";
const SHELL_ASSETS = [
  "/",
  "/manifest.json",
  "/pmc-logo.png",
];

/* v50j — accept SKIP_WAITING messages from SwUpdateBanner so the user can
 * trigger the new SW to take control immediately. */
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

/* Push handler — displays the notification and reveals the URL when tapped. */
self.addEventListener("push", (event) => {
  let data = { title: "PMC Managers", body: "You have a new notification", url: "/" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (_) { /* keep defaults */ }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/pmc-logo.png",
      badge: "/pmc-logo.png",
      data: { url: data.url },
      tag: data.tag || "pmc-msg",
      renotify: true,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil((async () => {
    const clientList = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of clientList) {
      if ("focus" in c) { try { await c.navigate(targetUrl); } catch(_){} return c.focus(); }
    }
    return self.clients.openWindow(targetUrl);
  })());
});

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_VERSION);
    try { await cache.addAll(SHELL_ASSETS); } catch (_) { /* offline install */ }
    // v54i — take over promptly so a freshly-deployed build reaches returning
    // visitors without needing them to tap the update banner. Combined with
    // the version guard in src/lib/versionGuard.js this eliminates the
    // "deployed but user still sees old code" class of bug.
    try { await self.skipWaiting(); } catch (_) {}
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
        if (fresh) return fresh;
      } catch (_) { /* fall through */ }
      const cache = await caches.open(CACHE_VERSION);
      const shell = await cache.match("/");
      if (shell) return shell;
      // Always resolve with a real Response so the browser never sees `undefined`.
      return new Response("Offline", { status: 503, statusText: "Offline" });
    })());
    return;
  }

  // 3. Static assets — stale-while-revalidate. Guarantees a Response.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_VERSION);
    const cached = await cache.match(req);
    if (cached) {
      // Refresh in background.
      fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === "basic") {
          cache.put(req, res.clone()).catch(() => {});
        }
      }).catch(() => {});
      return cached;
    }
    try {
      const res = await fetch(req);
      if (res && res.status === 200 && res.type === "basic") {
        cache.put(req, res.clone()).catch(() => {});
      }
      return res;
    } catch (_) {
      return new Response("", { status: 504, statusText: "Gateway Timeout" });
    }
  })());
});
