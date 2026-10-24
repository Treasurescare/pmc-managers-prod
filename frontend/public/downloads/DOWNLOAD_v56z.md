# PMC Managers — v56z (27 Jun 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v56z.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56z-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v56z · Backend v56z"

## What's in v56z
1. **Vendor "Find tenders" — delivery country now shows** (was "—"); resolves ISO code to
   full country name.
2. **Vendor "Find tenders" — EMD amount now shows** (e.g. ₹50,000 or "2% of bid"); falls back
   to "See notice" only when no EMD is configured on the notice.
3. **Vendor "Find tenders" — sort/filter toolbar**: sort by Closing soonest/latest, Budget
   high→low / low→high; filter by Country, Sector, Contract type, Category; Clear button.
4. Rolled up since v56y deploy: dark Supplier sidebar, unified Supplier mobile nav (single
   hamburger drawer), vendor-home quick-link icons, escrow signature chips.

Preview-verified by screenshot. Awaiting your deploy + confirmation.
