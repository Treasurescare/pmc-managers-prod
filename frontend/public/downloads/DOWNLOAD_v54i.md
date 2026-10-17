# PMC Managers v54i — Stale-bundle self-heal (document upload "still broken" fix)

Release target: 17 Feb 2026

**Contains everything from v54a → v54h plus the items below. Deploy this
pair and skip earlier bundles.**

## Why this release exists

A vendor reported that registration document uploads still showed no
View/Download and "vanished on save" — in Section A and Section D
especially — across several releases.

We reproduced the user's **exact** production registration
(`/register/resume?token=…`) in a clean browser against the live site and
confirmed the opposite:

- Section A (`incorporation_certificate`), Section C
  (`articles_of_incorporation`) and Section D (`signed_declaration`) all
  upload correctly, render **VIEW / DOWNLOAD / DELETE**, and **survive both
  Save Draft and a full page reload**.
- The backend persisted every slot and the file endpoint returned
  `HTTP 200`.

So the deployed code was already correct. The reason the vendor kept seeing
the old broken behaviour is that **their browser was running a cached older
bundle** — the service worker / CloudFront edge kept serving stale JS even
after the new build went live. The fixed code simply wasn't reaching them.

## What changed in v54i

### 1. Version self-heal guard (permanent cure)
On every cold load the app now calls `/api/v1/_version` (which bypasses the
service worker and is served no-store by EB, so it is always fresh) and
compares it to the version baked into the running bundle. If the backend is
newer, the bundle is stale: the app wipes every cache, unregisters the
service worker, and hard-reloads **once** (guarded against loops). Returning
visitors on an old shell now recover automatically — no manual cache clear.

Files: `src/lib/versionGuard.js`, `src/index.js`.

### 2. Service worker now updates promptly
`CACHE_VERSION` bumped to `pmc-shell-v54i` and the worker calls
`skipWaiting()` on install (and still `clients.claim()` on activate). A newly
deployed worker takes control and the existing update banner reloads the tab
once, instead of waiting for every tab to close.

File: `public/service-worker.js`.

### 3. Build stamp bump
Footer + `/api/v1/_version` now report **v54i**.

## Deploy

1. EB: upload `pmc-backend-v54i.zip` → wait for Green.
2. S3: sync `pmc-frontend-v54i-prod-build.zip` contents (no `--delete`).
3. **CloudFront: create an invalidation for `/*`** (or at minimum
   `/index.html`, `/`, `/service-worker.js`). This is what flushes the edge
   so currently-stuck browsers fetch the fresh `index.html` immediately.
4. Visit `https://www.pmcmanagers.com/api/v1/_version` → should return
   `{"version":"v54i"}`.
5. Scroll to the homepage footer → should read **Frontend v54i · Backend v54i**.

> After this deploy, any vendor still on an old bundle will auto-reload to
> v54i the next time they open the site, because of the new version guard.

## Artifacts

* Backend: `pmc-backend-v54i.zip`
* Frontend: `pmc-frontend-v54i-prod-build.zip`
