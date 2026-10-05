#!/usr/bin/env bash
# PMC v51q — mobile design polish over v51p
#
# 1. Admin → Vendors: tapping a vendor row on a phone/tablet now expands
#    the KPI + KYC detail INLINE, directly below the tapped row, instead of
#    rendering it at the bottom of the stacked page. Desktop (≥1024px)
#    keeps the right-hand detail column. Implemented via a matchMedia
#    (max-width:1023px) gate; the detail JSX is shared (no duplication).
# 2. Admin → Masters: the tab strip was a single horizontally-scrolling
#    row where only the active tab was clearly visible. It is now a
#    wrapping chip grid — every master visible at once; active chip is
#    solid navy with white text, inactive chips are outlined.
set -eu
VER="v51q"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
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
# PMC Managers — Release v51q (cumulative, supersedes v51o/v51p)

## Changes in this build

### Admin → Vendors: detail opens right where you tap (mobile)
Previously, tapping a vendor in the list on a phone rendered the KPI/KYC
detail panel at the very bottom of the page (the two-column desktop layout
simply stacked). Now the detail expands **inline, directly below the tapped
row** — accordion style. Desktop (≥1024px) is unchanged: the detail still
opens in the right-hand column.

### Admin → Masters: all tabs visible, active one highlighted
The Masters tab bar was a single horizontally-scrolling row — only the
active tab was obvious, the rest were hidden off-screen. The bar is now a
wrapping chip grid: all 13 masters visible at once. Active chip = solid
navy with white text; inactive chips = outlined navy on white.

### Also included (from v51o + v51p)
- Bidding Ops: mobile tabs wrap, tab counts always match visible rows,
  row-card checkbox alignment fixed.
- Admin drawer scrolls to Masters / Events on iOS (100dvh fix).
- Admin Vendors toolbar wraps 2-up; giant-button padding bug fixed
  (88px bottom-tab clearance rule scoped to vendor-portal page roots).

## Deploy
- Frontend: `pmc-frontend-v51q-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. Supersedes v51o/v51p — deploy this one only.
- Backend: unchanged since v51n (`pmc-backend-v51q.zip` identical,
  included for convenience).
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
