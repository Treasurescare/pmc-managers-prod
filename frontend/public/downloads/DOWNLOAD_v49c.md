# PMC Managers Limited — Release v49c (v50-ship-rev2)

## What's in this release
- **Option E is now the SOLE UI** — legacy Navy retired. `UiThemeContext` returns `isE:true` unconditionally.
- **55 template screens wired** — 37 pages have live-data hooks fetching from real backend endpoints (notices, vendors, bids, packages, escrow, audit, registrations, notifications). 8 are marketing/legal static by design; 3 are auth/form-only pages.
- **All `href="#"` templates re-wired** via `PmcLinkPatcher.jsx` — public top nav, vendor sidebar, admin sidebar (all 20 items), buttons (chips, Create, Sign in, Register), help drawer, brand logo. SPA navigation only — no full reloads.
- **Tenders list filter engine** — real status radios, notice-type checkboxes, country + category facets rebuilt from live data, budget min/max in USD-equivalent, live search, sort, Clear all.
- **52 real transactional email templates** ported to `/app/backend/email_templates/` with rendering engine (`emails_option_e.py`) + admin preview endpoints (`/api/v1/admin/emails/templates`, `/preview/<name>`, `/test-send`).
- **All 24 legacy `send_email(..., wrap(...))` call-sites now render Option E chrome** (forest-green header + brass CTA + cream background + Cormorant Garamond) because `emails.py::_wrap()` was rewritten. Zero router changes required.
- **v50 backend routes**:
  - `GET /api/v1/meta/public/stats` — 4 real counters (notices/suppliers/packages/ledger_events)
  - `GET /api/v1/meta/public/escrow-summary` — per-currency EMD totals + USD-equivalent + paid/pending
  - `GET /api/v1/admin/emails/templates` — 52 templates listed with subjects
  - `GET /api/v1/admin/emails/preview/{name}` — renders one template with demo ctx
  - `POST /api/v1/admin/emails/test-send` — dispatches one via Resend

## Bundles
- `pmc-frontend-v49c-prod-build.zip` (2.7 MB) — built with `REACT_APP_BACKEND_URL=""` for same-origin S3/CloudFront
- `pmc-backend-v49c.zip` (413 KB) — includes `Dockerfile`, `Dockerrun.aws.json`, `.platform/` at zip root; excludes `.env`, `__pycache__`, `tests/`, `keys/`

## Deploy
1. **Frontend to S3 + CloudFront**:
   - Unzip contents into your S3 bucket.
   - Invalidate CloudFront cache: `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`.
   - **IMPORTANT for SPA routing**: in CloudFront, add two custom error responses:
     - HTTP 403 → response path `/index.html`, response code `200`
     - HTTP 404 → response path `/index.html`, response code `200`
     - Without these, direct deep-link loads like `/tenders/live` will 404.
2. **Backend to Elastic Beanstalk**:
   - Upload the zip via the EB console (or `eb deploy`). No new env vars needed.
   - Existing env vars still valid: `MONGO_URL`, `DB_NAME`, `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME`, `STRIPE_*`, `DOCUSIGN_*`.

## Rollback
- Roll back to `v48c` if needed. Alternately, append `?ui=default` to any URL (still respected by the router — legacy pages remain in the codebase as fallbacks).

## Testing status
- iteration_35: 15/16 clicks + nav flows pass; email preview endpoint returns 52 templates in forest-green Option E chrome
- iteration_36: retest of `+ Create` button — PASS after adding `create`/`+ create` to ADMIN_LINKS map
- Sibling bug caught by tester: `style=""` in `RegistrationE.jsx` — fixed globally + guarded in converter script
