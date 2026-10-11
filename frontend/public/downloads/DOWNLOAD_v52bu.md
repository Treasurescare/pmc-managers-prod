# PMC Managers · Release v52bu

**Date:** 11 Oct 2026 · **Supersedes:** v52bt

## New in v52bu

### 1. Vendor Signatures Sync — "Admin signed · your turn"
- `VendorSignaturesE.jsx` now maps DocuSign status `signed` (partial — admin signed, vendor pending) to a bright yellow pill **"Admin signed · your turn"** with a working **Review & sign** CTA (previously fell through to the raw literal and had no action button).
- The page now **polls every 20 s** and on window-focus, so the badge appears live after admin dispatch without the vendor manually refreshing.

### 2. EMD Payment History — per-bid printable receipt
- New authenticated endpoint `GET /api/v1/payments/emd/bid/{bid_id}/receipt.pdf` renders a one-page A4 PDF (Weasyprint) with vendor, bid, notice, amount, payment reference and date.
- `useVendorEmdLive` now rewrites the right-most cell of every **paid** row into a **"Receipt (PDF)"** button (`data-testid=vemd-receipt-<bid_ref>`) that triggers an authenticated blob download — no more "Details" dead-link.

### 3. Vendor sidebar — Categories & Services icons restored
- `VendorEmdE.jsx` and `VendorAlertsE.jsx` had hard-coded `<nav class="pmc-lnav">` menus missing both **Categories** (`i-tag`) and **Services** (`i-briefcase`). Those links are now inserted right after Company & KYC, matching the shared `VendorPortalChrome` layout — so the sidebar is identical on every vendor page.

## Deployment
- Backend EB: upload `pmc-backend-v52bu.zip` as a new application version.
- Frontend S3 + CloudFront: unzip `pmc-frontend-v52bu-prod-build.zip`, sync to the bucket, invalidate `/*`.

## Verify after deploy
1. Vendor /vendor/emd → every paid deposit row has a **Receipt (PDF)** button; clicking downloads a receipt PDF named `PMC-EMD-Receipt-<BID>.pdf`.
2. Vendor /vendor/emd and /vendor/alerts → the left nav now shows both **Categories** and **Services** below Company & KYC.
3. Vendor /vendor/signatures → an envelope whose DocuSign state is `signed` (admin signed, vendor pending) renders "Admin signed · your turn" with the Review & sign button; the page refreshes automatically every 20 s and on window focus.
