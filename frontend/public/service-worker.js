// Basic offline-first service worker for PMC Managers PWA
// Precaches app shell + assets; falls back to cache when offline for GET requests.
// API calls (/api/*) are network-first — never served stale.

const CACHE = "pmc-shell-v1";
const APP_SHELL = ["/", "/manifest.json", "/pmc-logo.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Never cache API — always network
  if (url.pathname.startsWith("/api/")) return;

  // App shell → cache-first with network fallback + background update
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetching = fetch(req).then((res) => {
        if (res && res.ok && res.type === "basic") {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone));
        }
        return res;
      }).catch(() => cached);
      return cached || fetching;
    })
  );
});

// Push notification (Firebase / APNs delivery via Capacitor bridge)
self.addEventListener("push", (event) => {
  if (!event.data) return;
  let payload = {};
  try { payload = event.data.json(); } catch { payload = { body: event.data.text() }; }
  const title = payload.title || "PMC Managers";
  const options = {
    body: payload.body || "You have an update",
    icon: "/pmc-logo.png",
    badge: "/pmc-logo.png",
    data: payload.data || {},
    tag: payload.tag || "pmc-notif",
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/m";
  event.waitUntil(self.clients.openWindow(url));
});
