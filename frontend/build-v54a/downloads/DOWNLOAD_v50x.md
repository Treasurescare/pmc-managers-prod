# PMC Managers — Release v50x (cumulative v50m → v50x)

## Fixes in this build
- **Zero-EMD tenders**: when the tender has `emd_due_amount = 0`, the
  "Pay EMD now / Submit for review" button is hidden entirely and the
  workspace shows "No EMD required for this bid".
- **In-page document preview**: clicking View on an uploaded EMD proof /
  bank guarantee now opens a modal inside the workspace (iframe for PDF,
  image render for PNG/JPG) with Close + optional "Open in new tab".
- **File URL encoding fix**: keys were encoded with %2F for "/", which
  CloudFront/nginx reject with 404 — this is why the old new-tab view
  showed a blank page. Keys are now appended raw.

## Carried from v50w
- EMD proof uploads list (Uploaded (N) panel, filename + size + View +
  Delete, multi-file)

## Carried from v50v
- Bid Workspace fully live (real bid data, Transfer/BG radios, Save /
  Pay EMD now → Stripe)
- Paid bids show "Settled" + disabled button; pay-redirect friendly
  "already settled" message
- Signatures heading context-aware + download fallback
- Company & KYC "Bidding categories" tab (approved/pending/recent)
- Reviews Reply dialog; PmcLinkPatcher React-owned bypass

## Deploy
- Frontend: `pmc-frontend-v50x-prod-build.zip` → S3 + CloudFront `/*`
- Backend: `pmc-backend-v50x.zip` → EB (identical to v50t)
