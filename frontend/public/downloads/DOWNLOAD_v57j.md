# PMC Managers — v57j (29 Oct 2026)

Fix release on top of v57i.
- Backend  → `pmc-backend-v57j.zip`             → Elastic Beanstalk
- Frontend → `pmc-frontend-v57j-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Footer should read "Frontend v57j · Backend v57j"

## Changes since v57i
- Fee rules → Quick calculator "Compute" no longer errors ("computeEmdMaster is not a function").

See DOWNLOAD_v57i.md for the full v57i feature list and AWS/Stripe steps.
