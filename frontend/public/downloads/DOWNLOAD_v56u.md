# PMC Managers — v56u (26 Jun 2026)

Fix release on top of v56t.

Production bundles (upload to your AWS stack):

- Backend  → `pmc-backend-v56u.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56u-prod-build.zip` → unzip, upload contents to S3 bucket root
- Then invalidate CloudFront `/*`
- Confirm footer: "Frontend v56u · Backend v56u"

## What's fixed in v56u

1. **Duplicate contract types / sectors** — the dropdowns were showing every
   contract type twice because the production master collection had been seeded
   twice. Two-part fix:
   - The UI now **defensively de-duplicates by code**, so duplicate rows never
     render twice anywhere (board + homepage + notice forms).
   - A new admin button **Admin → Masters → Contract types (or Sectors) →
     "Remove duplicates"** permanently deletes the duplicate rows from the
     database (keeps the earliest of each code; sectors, contract types and
     categories). Safe to run repeatedly — reports "No duplicates found" when clean.
   - **After deploying, open that tab once and click "Remove duplicates"** to
     clean your production data.

2. **Country filter on the tender board** — was a 2-letter text box that only
   matched exact ISO codes. It is now a proper **country dropdown** sourced from
   the full country master, on both the public board and the homepage search.

Preview-verified. Awaiting production deploy + your confirmation.
