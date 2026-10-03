#!/usr/bin/env bash
# PMC v50u — Vendor portal navigation consistency fixes
# (a) View/Continue buttons on My Bids now route to the live Bid Workspace
#     (was /vendor/bids/:id — a non-existent route that fell through to the
#     notices catch-all page)
# (b) Static vendor pages (EMD / Reviews / Alerts / Bid Workspace) no longer
#     render mockup sidebar badges (29/1/1) that conflicted with live counts
# (c) Bid Workspace sidebar href="#" links replaced with real /vendor/* routes
set -eu
VER="v50u"
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
# PMC Managers — Release v50u (cumulative: v50m → v50u)

## Fixes in this build (vendor portal navigation consistency)

### (a) My Bids "View" / "Continue" buttons — fixed routing
Both buttons pointed to `/vendor/bids/:id`, which has no route and fell
through to the public notices catch-all (the bug where clicking View on an
active bid landed on the tender/notices page). They now open the live
Bid Workspace at `/vendor/workspace/:bidId`. Pay EMD and Sign LOA actions
unchanged.

### (b) Sidebar count consistency (29 vs 33 flip) — fixed
The static vendor pages (EMD & payments, Reviews, Alerts, Bid Workspace)
rendered their own mockup sidebar with hard-coded badges (Find tenders 29,
My bids 1, Signatures 1). Live pages use real counts from the API, so the
number flipped as you navigated. Mockup badges removed — static pages now
show no stale numbers, live pages show real ones.

### (c) Bid Workspace sidebar links fixed
Every sidebar entry on the Bid Workspace was `href="#"`; now real
`/vendor/*` routes (Home / Find tenders / My bids / EMD / Signatures /
Company & KYC / Reviews / Account).

## Carried from v50t (critical)
- Runtime domain guard in api.js — production domains always use
  same-origin /api (fixes preview-URL bake-in that broke prod login/reset)
- Built with REACT_APP_BACKEND_URL=""

## Carried from v50s
- Upload tiles visible (amber dashed) + re-upload after delete
- My Bids fully live via /api/v1/bids/mine (+ notice title/deadline join)
- Live sidebar counts via VendorPortalChrome
- /vendor/auth/me returns business_categories (KYC header shows approvals)
- Back button on Categories page

## Deploy
- Frontend: `pmc-frontend-v50u-prod-build.zip` → S3 + CF invalidate `/*`
- Backend: `pmc-backend-v50u.zip` → EB (identical API to v50t; frontend-only changes)
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
