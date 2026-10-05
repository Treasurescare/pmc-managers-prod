#!/usr/bin/env bash
# PMC v51s — admin avatar dropdown, vendor account overlap, 5th tab icon
set -eu
VER="v51s"
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
# PMC Managers — Release v51s (cumulative, supersedes v51o–v51r)

## Fixes in this build

### 1. Admin avatar dropdown no longer clipped on the right (mobile)
The topbar (Create / Help / Bell / Avatar) overflows the right edge on
narrow screens, which pushed the avatar close to the viewport edge; its
absolutely-positioned dropdown (260px wide, anchored right:0) was then
cut off by the sticky header's ancestor overflow. On ≤767px the avatar
menu is now `position: fixed` anchored to the viewport (top:60, right:8,
width 280 or viewport-16), so the full dropdown — profile email, Change
photo, Change password, Sign out — is always inside the screen and above
the topbar.

### 2. Vendor Account → "Sign out everywhere else" button no longer overlaps the description
The Password and Other devices rows used `flex` with no wrap, so when the
button sat beside the "Sign out of every other browser and mobile
session." text on a phone, it overlapped the wrapped second line. Rows
are now `flex-wrap: wrap` with gap:12 and shrink-safe column widths —
the button drops to its own line cleanly on narrow screens.

### 3. Mobile bottom tab bar: 5 icons including My Bids + Signatures
The vendor mobile tab bar used to show 4 icons: Home / Tenders / Bids /
Account. "Bids" is renamed to the clearer **My Bids**, and **Sign**
(Signatures) is added so the five mobile tabs are now:
`Home · Tenders · My Bids · Sign · Account`.

### Also included (v51o–v51r)
- Bidding Ops mobile: tabs wrap, counts match visible rows, row-card
  checkbox alignment.
- Admin drawer scrolls to Masters on iOS (100dvh fix).
- Admin Vendors: toolbar wraps 2-up; giant-button padding bug fixed;
  tapping a row expands KPI/KYC detail inline below the row (mobile);
  desktop keeps the right column.
- Masters: all 13 tabs visible as wrapping chips.
- Start-bid: Submit button no longer hidden under the tab bar;
  uploaded files visible as readable chips with working View link;
  upload slots and gateways stack 1-col on phones.

## Deploy
- Frontend: `pmc-frontend-v51s-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. Supersedes v51o–v51r — deploy this one only.
- Backend: unchanged since v51n (`pmc-backend-v51s.zip` identical,
  included for convenience).
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
