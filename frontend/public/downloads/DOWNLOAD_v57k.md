# PMC Managers — v57k (29 Oct 2026)

- Backend  → `pmc-backend-v57k.zip`             → Elastic Beanstalk
- Frontend → `pmc-frontend-v57k-prod-build.zip` → delete old files in S3 bucket root, upload unzipped contents → CloudFront invalidation `/*`
- Footer must read "Frontend v57k · Backend v57k"

## Changes since v57i
- Fee rules → Quick calculator "Compute" fixed.
- Charge Fee → waits for the email provider; shows a box with the Stripe link and "Emailed to …" (green) or "Email NOT sent" (red).
