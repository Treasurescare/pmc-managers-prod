# PMC Managers Limited — Release v49d

## Fix in this release
* **Unified `/login` (Option E) sign-in is now functional.**
  The Option E `SignInE.jsx` shipped as a pure static template — no state,
  no `onSubmit`, and the password input held a hardcoded value
  (`value="••••••••••••"`). That's why the "Continue" button did nothing
  and users got stuck at the password field.
  Portal-specific routes (`/vendor/login`, `/admin/login`, `/staff/login`)
  worked because they still use the legacy forms — but the unified `/login`
  page (which is where most users land) was decorative only.

  Rewrote `SignInE.jsx` as a real form:
  - Working role selector (Supplier / PMC staff / Administrator).
  - Real `useState` inputs, no hardcoded placeholder value.
  - Real API calls: `vendorApi.login`, `staffApi.login` (with role fallback
    across `reviewer`, `management`, `agent`, `committee_member`, `admin`),
    `adminApi.login` (final fallback for admin card).
  - Redirects to `/vendor/change-password` when the vendor's account has
    `must_change_password=true`.
  - Existing Option E visual chrome preserved (forest-green rail,
    brass CTA, cream body).
  - `data-testid`s added: `signin-e-form`, `signin-e-email`,
    `signin-e-password`, `signin-e-submit`, `signin-role-supplier|staff|admin`.

* **`/register` now serves the working `RegistrationStart` flow directly.**
  Previously the `/register` route rendered `RegistrationE` — a static
  "Step 4 of 5 KYC" mockup with no data collection. New suppliers landing
  there could not actually register. Route now points to `RegistrationStart`
  (PDF form download, resume-by-email, real submission).

## Everything else unchanged from v49c
* Option E is the sole UI (55 pages, 52 branded email templates, live-data
  wiring, `PmcLinkPatcher` SPA navigation, admin email preview endpoints).
* `_wrap()` in `emails.py` still renders Option E chrome for all 24 legacy
  send sites.

## Bundles
* **Frontend:** `pmc-frontend-v49d-prod-build.zip`
  Built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront ready.
* **Backend:** `pmc-backend-v49d.zip`
  No backend code change vs v49c; you may re-use the v49c EB deployment
  if it's already live.

## Deploy checklist
1. **Frontend to S3** — unzip the `.zip` into your bucket root; invalidate
   CloudFront `/*`.
2. **CloudFront SPA rule (once)** — Custom error responses: both `403` and
   `404` → `/index.html` with HTTP `200`. Without this, direct loads of
   deep links like `/tenders/live` will 404.
3. **Backend to Elastic Beanstalk** — unzip contains `Dockerfile`,
   `Dockerrun.aws.json` and `.platform/` at the archive root, as EB
   requires for the Docker platform.

## Test credentials (same as prior releases)
* Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
* Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
* Fall back to `v49c` or `v48c` if needed.
