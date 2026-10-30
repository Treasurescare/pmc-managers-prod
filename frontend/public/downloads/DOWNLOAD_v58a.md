# PMC Managers — v58a (30 Oct 2026) — Marketing

- Backend  → `pmc-backend-v58a.zip` → Elastic Beanstalk
- Frontend → `pmc-frontend-v58a-prod-build.zip` → S3 root (delete old index.html + static/ first) → CloudFront invalidation `/*`
- Footer must read "Frontend v58a · Backend v58a"

## New: Admin → Market → Marketing
- Contacts: add platform vendors & buyers, upload CSV (template provided), unsubscribe handled automatically.
- Lists & segments: by vendor/buyer, country, category, source; live count of who can be emailed.
- Email campaigns: AI writer, preview, test send, send to a list, opens/clicks.
- New-tender alerts: toggle on to email vendors in the tender's category when it goes live (OFF by default).
- Referrals: vendors get a link under "Refer & earn"; sign-ups through it are counted.
