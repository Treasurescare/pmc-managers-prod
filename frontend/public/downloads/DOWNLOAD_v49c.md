# PMC Managers Limited — Release v49c

## What's in this release
* **Option E v2 — 55-template design overhaul** wired behind `?ui=e`
  (legacy Navy UI remains the default).
* **Live-data v49c**: homepage stats bar (17/41/48/911), tenders list rows &
  filters, notice detail per-ref fetch, vendor home KPIs (Active/Closing/
  Matched/KYC now driven by `/api/v1/vendor/auth/me` + `/vendor/bids`),
  **admin dashboard EMD KPI now shows real USD-equivalent from
  `/api/v1/meta/public/escrow-summary`** (per-currency totals plus paid/pending counts),
  admin pipeline, KPIs and sidebar counts all real.
* **Option E email templates** in `/app/backend/emails_option_e.py` (6 typed
  builders, plugs into existing Resend integration).
* **Design references**: `/design/dialogs`, `/states`, `/emails`,
  `/printables` are showcase surfaces; safe to link from admin docs.

## Bundles
* Frontend: `pmc-frontend-v49c-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` → same-origin S3/CloudFront)
* Backend:  `pmc-backend-v49c.zip` (excludes `.env`, `__pycache__`)

## Deploy
* Frontend: unzip into your S3 bucket; invalidate CloudFront cache.
* Backend: unzip into your Elastic Beanstalk root. No new env vars needed.

## New/changed endpoints
* `GET /api/v1/meta/public/stats` — now includes `ledger_events`.
* `GET /api/v1/meta/public/escrow-summary` — new; per-currency EMD totals +
  USD-equivalent estimate + paid/pending counts. No PII.

## Rollback
* Roll back to `v48c` if needed, or disable Option E at runtime with
  `?ui=default` on any URL.
