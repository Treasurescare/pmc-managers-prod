# PMC Managers Limited — Release v49b

## What's in this release
* **Option E v2 — complete 55-template design overhaul** wired behind `?ui=e`
  (legacy Navy UI remains the default for existing users).
* **Real data**: Option E homepage, tenders list, and vendor home now pull live
  data from the same public/vendor APIs the legacy UI uses. See
  `/app/frontend/src/lib/pmcELiveData.js` for the runtime patching layer.
* **Option E email templates**: 6 branded templates in
  `/app/backend/emails_option_e.py` (new-tender match, corrigendum, deadline,
  EMD received, award issued, result published) sent via existing Resend
  integration in `emails.py`.
* **Design references** (`/design/dialogs`, `/states`, `/emails`,
  `/printables`) are showcase surfaces only — safe to link from admin docs.

## Bundles
* Frontend: `pmc-frontend-v49b-prod-build.zip`
  (already built with `REACT_APP_BACKEND_URL=""` → same-origin S3/CloudFront)
* Backend:  `pmc-backend-v49b.zip` (excludes `.env`, `__pycache__`)

## Deploy
* Frontend: unzip into your S3 bucket; invalidate CloudFront cache.
* Backend: unzip into your Elastic Beanstalk deployment root. No env-var changes
  from v49a; existing keys (`RESEND_API_KEY`, `STRIPE_*`, `DOCUSIGN_*`,
  `MONGO_URL`, `DB_NAME`) apply unchanged.

## Rollback
* Roll back to `v48c` if needed — Option E can also be disabled at runtime by
  appending `?ui=default` to any URL.
