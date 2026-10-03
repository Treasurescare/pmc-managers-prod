#!/usr/bin/env bash
# PMC v50x — EMD workspace UX fixes
# (a) Hide the EMD submit action entirely when the tender needs no EMD
#     (emd_due_amount = 0): shows "No EMD required for this bid" instead.
# (b) View on uploaded proofs now opens an in-page preview modal
#     (iframe for PDFs, img for images) instead of navigating to a new tab.
# (c) File URLs no longer encode "/" as %2F — that broke through
#     CloudFront/nginx with a 404 ("new page shows nothing").
set -eu
VER="v50x"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -3
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' -x 'backend/**/*.pyc' \
    -x 'backend/.env' -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' -x 'backend/tests/*' -x 'backend/keys/*' 2>/dev/null || true
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
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
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
