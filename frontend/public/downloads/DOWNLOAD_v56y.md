# PMC Managers — v56y (27 Jun 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v56y.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56y-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v56y · Backend v56y"

## What's in v56y (cumulative UI-consistency batch)
1. **Supplier portal sidebar unified (dark)** — the vendor left-nav is now the same dark
   forest-green panel as Admin/Staff/Escrow (light text, brass active stripe, dark
   "Your PMC desk" card). All four portals now match.
2. **Supplier portal mobile nav unified** — bottom tab bar removed; single top-left
   hamburger opens a full off-canvas drawer + scrim with the complete navigation + Sign out.
3. **Vendor home Quick-link icons** — meaningful icons (search/tag/shield/settings) instead
   of four identical sparkle glyphs.
4. **Escrow transaction signature chips** — colour-coded chips (emerald "signed" / amber
   "pending") on desktop and mobile cards.

Preview-verified by screenshot. Awaiting your deploy + confirmation.
