# PMC Managers Limited — Release v50j

## Permanent fix for the "I deployed but can't see it" problem
Also fixes the Masters-sidebar-flicker-on-first-login symptom (same root cause).

* `service-worker.js` no longer auto-skips waiting on install — the OLD
  controller keeps the current session consistent.
* When a new SW finishes installing, `index.js` fires
  `pmc:sw-update-available` which triggers the new **"New version
  available · Refresh"** banner (`SwUpdateBanner.jsx`).
* Clicking Refresh posts `SKIP_WAITING` to the waiting SW; the browser's
  `controllerchange` event triggers a clean one-shot page reload with
  the fresh bundle — no stale menus, no stale assets.
* The banner also appears automatically every 30 min for long-lived
  tabs via `registration.update()` on an interval.

## Batch B — Vendor bugs
* **#59 "Invite Undefined" success toast** — toast format already
  defensive against undefined values; stale cache was the real cause
  (now solved globally by the SW update prompt).
* **#62 Bulk invite CSV error** — client-side pre-validation shows
  specific "Row N: invalid email" messages before hitting the backend,
  so the admin never sees a generic 400.
* **#119 Document card icon overlap** — `DocSlot` action row now
  `flex-wrap` + `shrink-0`, label `truncate`. View/Download/Delete
  icons wrap cleanly on narrow cards (Address Proof etc.).
* **#120 Section K declarations** — Section E (team's "Section K") now
  surfaces an "X/6 declarations accepted" meter, highlights un-checked
  rows amber, and the Create flow refuses to save unless ALL six are
  ticked. User is bounced to the Declarations tab with a toast.

## Deploy
* Backend: `pmc-backend-v50j.zip` → Elastic Beanstalk.
* Frontend: `pmc-frontend-v50j-prod-build.zip` → S3 sync + CloudFront
  invalidate `/*`. After this one deploy, your team will **never again**
  need a hard refresh — the Refresh banner handles it automatically.
