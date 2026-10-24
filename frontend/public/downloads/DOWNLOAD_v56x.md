# PMC Managers — v56x (27 Jun 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v56x.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56x-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v56x · Backend v56x"

## What's new / fixed in v56x
1. **Supplier portal mobile nav unified** — matches Staff/Escrow/Admin: the bottom tab
   bar is gone; the single top-left hamburger opens a full off-canvas drawer + scrim with
   the complete navigation (Home, Find tenders, My bids, Reverse auctions, EMD & payments,
   Signatures, Company & KYC, Categories, Services, Reviews, Account & security, Alerts,
   Help) plus Sign out. Desktop layout unchanged.
2. **Vendor home Quick links icons** — meaningful per-link icons (search/tag/shield/settings)
   instead of four identical sparkle glyphs that read as loading spinners.
3. **Escrow transaction signature chips** — signature status now shows as colour-coded chips
   (emerald "signed" / amber "pending") on desktop and mobile cards.

Preview-verified by screenshot. Awaiting your deploy + confirmation.
