#!/usr/bin/env bash
# PMC v50w — EMD proof upload: visible multi-document list
# Every uploaded EMD proof / bank-guarantee file now appears in an
# "Uploaded (N)" list under the drop zone with filename, size, View
# (opens inline in a new tab) and Delete. Multiple files supported.
set -eu
VER="v50w"
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
# PMC Managers — Release v50w (cumulative v50m → v50w)

## Fix in this build
**Bid Workspace — EMD proof uploads now show a live document list.**
Previously an upload showed only a toast and vanished; vendors could not
see, open or remove what they had uploaded. Now every upload lands in an
"Uploaded (N)" panel under the drop zone:
- filename + human-readable size (KB/MB)
- View — opens the file inline in a new tab (gated, signed-in only)
- Delete — removes it from the list before you submit for escrow check
- Multiple documents accumulate (bank confirmation + BG + annexes all show)

Verified on preview: two PDFs uploaded → both rows listed, View returns
HTTP 200, Delete removes the row.

## Carried from v50v
- Bid Workspace fully live (real bid data, Transfer/BG radios, Save /
  Pay EMD now → Stripe)
- Paid bids show "Settled" + disabled button; pay-redirect shows a
  friendly "already settled" message
- Signatures heading context-aware + download fallback
- Company & KYC "Bidding categories" tab (approved/pending/recent)
- Reviews Reply dialog; PmcLinkPatcher React-owned bypass

## Deploy
- Frontend: `pmc-frontend-v50w-prod-build.zip` → S3 + CloudFront `/*`
- Backend: `pmc-backend-v50w.zip` → EB (identical to v50t)
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
