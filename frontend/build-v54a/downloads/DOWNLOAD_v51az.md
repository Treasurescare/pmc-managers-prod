# PMC Managers — v51az (Bidding Ops — video-verified fixes)

**Build date:** 2026-10-10
**Frontend bundle:** `pmc-frontend-v51az-prod-build.zip`
**Backend:** no changes — keep `pmc-backend-v51ax.zip`

## 🐞 Fixed (from the 05:24 screen recording)

- **Pipeline step numbers did nothing**: the EMD / Escrow / Admin /
  Certifier / Legal / Accounts / Awarded tiles had counters but were
  never wired to a click handler. Clicking a step now filters the bid
  list to that stage and highlights the active tile (inset brand ring +
  pale background). Click the same step again to clear the filter.
  Status mapping: EMD = emd_pending/submitted · Escrow = emd_paid ·
  Admin = escrow_accepted · Certifier = admin_flagged · Legal =
  certifier_cleared · Accounts = legal_cleared/accounting_cleared ·
  Awarded = awarded/closed.
- **Review / Open bid doesn't open anything**: reverted the v51as
  inline-panel behavior. Review and Open bid now navigate to the full
  bid detail page (`/admin/bids/{id}`) with documents, timeline and
  actions. The right-side tracker still opens on a plain row click.

## Deploy

Frontend only: unzip into S3 (overwrite v51ay), CloudFront `/*`
invalidation. Backend unchanged.
