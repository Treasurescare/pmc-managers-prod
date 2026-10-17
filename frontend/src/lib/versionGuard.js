import { BUILD_VERSION } from "./buildStamp";

/**
 * Self-heal stale frontend bundles.
 *
 * `/api/*` bypasses the service worker and is served by Elastic Beanstalk
 * with no-store, so `/api/v1/_version` always reports the freshly-deployed
 * backend version. If the running JS bundle is older than the backend, the
 * browser (or a CloudFront edge) is serving a cached build — so we wipe every
 * cache, drop the service worker, and hard-reload exactly once.
 *
 * This is the permanent cure for "I deployed but the user still sees the old
 * behaviour": returning visitors pinned to an old shell recover automatically
 * on their next load instead of needing a manual cache clear.
 */
export async function runVersionGuard() {
  try {
    const res = await fetch("/api/v1/_version", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const backend = data && data.version;
    if (!backend || backend === BUILD_VERSION) return;

    // Only reload once per detected backend version so we never loop when the
    // CDN hasn't been invalidated yet and keeps handing back the old bundle.
    const KEY = "pmc.version_reload";
    if (sessionStorage.getItem(KEY) === backend) return;
    sessionStorage.setItem(KEY, backend);

    try {
      if (window.caches) {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
      }
    } catch (_) { /* cache API unavailable */ }

    try {
      if (navigator.serviceWorker) {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map((r) => r.unregister()));
      }
    } catch (_) { /* SW API unavailable */ }

    window.location.reload();
  } catch (_) {
    /* offline or backend unreachable — keep the current bundle */
  }
}
