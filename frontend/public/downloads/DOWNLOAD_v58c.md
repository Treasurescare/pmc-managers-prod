# PMC Managers — v58c (30 Oct 2026)

- Backend  → `pmc-backend-v58c.zip` → Elastic Beanstalk
- Frontend → `pmc-frontend-v58c-prod-build.zip` → S3 root (delete old index.html + static/ first) → CloudFront invalidation `/*`
- Footer must read "Frontend v58c · Backend v58c"

## New since v58b
- Share bar on every tender page: LinkedIn, WhatsApp, download image, copy link (preview card 1200×630).
- Marketing → Buyer invites: personal invite emails with sent → clicked → joined tracking.
- "Continue with Google" on the sign-in page for suppliers, staff and admins (existing accounts only).
  After deploying, test it on www.pmcmanagers.com. If Google sign-in fails there, we switch to your own Google account credentials.
