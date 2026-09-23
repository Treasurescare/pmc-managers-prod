// v46d — SELF-DESTRUCTING service worker.
// The previous offline-first SW precached "/" and kept serving stale JS
// bundles after deployments, which masked two production login fixes.
// This replacement: clears every Cache Storage entry, unregisters itself,
// claims open clients, and forces them to reload once so they immediately
// pick up fresh assets. No fetch handler = zero request interception.

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    } catch (_) { /* older browsers */ }
    try { await self.clients.claim(); } catch (_) {}
    try {
      const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      await self.registration.unregister();
      for (const client of windows) {
        try { client.navigate(client.url); } catch (_) {}
      }
    } catch (_) {
      try { await self.registration.unregister(); } catch (_) {}
    }
  })());
});

// No fetch listener: all traffic goes straight to the network.
