#!/usr/bin/env bash
# PMC v51r — vendor "Start bid" mobile fixes (over v51q)
#
# User report (iPhone, vendor portal → Start bid):
#   1. "Submit & pay EMD" button was hidden UNDER the fixed bottom tab
#      bar — the legacy BidSubmit page had no bottom clearance (the 88px
#      rule only covers Option-E page roots). Page now has pb-40 on
#      mobile so the button always scrolls fully above the tab bar.
#   2. Uploaded-file rows were INVISIBLE: a global Option-E remap in
#      index.css forces .text-slate-900/800 → cream and .bg-white →
#      light surface (meant for dark pages). On the light BidSubmit page
#      this made filenames cream-on-cream, and there was no way to view
#      the uploaded file. Fix: page-scoped slate-ink restore for
#      [data-testid="bid-submit-page"] + each uploaded doc now renders as
#      a white bordered chip with kind · filename · size and a working
#      "View" link (opens /api/v1/uploads/files/<key> in a new tab).
#   3. Upload slots + payment-gateway selector now stack 1-column on
#      phones (were 3 squeezed columns at 390px).
#   4. Submit button gets py-4 + font-semibold (bigger tap target).
set -eu
VER="v51r"
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
# PMC Managers — Release v51r (cumulative, supersedes v51o–v51q)

## Fixes in this build (vendor portal → Start bid, mobile)

1. **"Submit & pay EMD" button no longer hidden under the bottom menu.**
   The Start-bid page had no bottom clearance, so the fixed mobile tab
   bar covered the pay button at the end of the form. The page now pads
   160px at the bottom on phones — the button always scrolls fully into
   view above the menu.
2. **Uploaded files are visible and viewable.** A global theme remap
   (meant for dark pages) was forcing the uploaded-file text to cream on
   a near-white background — invisible. The Start-bid page now keeps
   dark slate text, and every uploaded document renders as a clear white
   chip showing `TECHNICAL · filename.pdf (size)` with a working
   **View** link (opens the file in a new tab) and Remove.
3. **Upload slots and payment-gateway options stack vertically** on
   phones instead of 3 squeezed columns.
4. Submit button tap target enlarged.

### Also included (v51o–v51q)
- Bidding Ops mobile: tabs wrap, counts match visible rows, row-card
  checkbox alignment.
- Admin drawer scrolls to Masters / Events on iOS (100dvh fix).
- Admin Vendors: toolbar wraps 2-up; giant-button padding bug fixed.
- Admin Vendors: tapping a row expands the KPI/KYC detail inline below
  the row on mobile; desktop keeps the right column.
- Masters: all 13 tabs visible as wrapping chips; active chip solid navy.

## Deploy
- Frontend: `pmc-frontend-v51r-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. Deploy this one only.
- Backend: unchanged since v51n (`pmc-backend-v51r.zip` identical,
  included for convenience).
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
