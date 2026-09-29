#!/usr/bin/env bash
# PMC v49q — Bidding Ops redesign adoption + equal-height tender cards.
# Ships a new AdminBiddingOpsE screen wired to real /api/v1/bids data,
# and card layout fix for "Open for bids this week" grid.
set -eu

VER="v49q"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"

echo ">>> Building frontend ($VER) with same-origin backend URL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build

echo ">>> Zipping frontend build (excluding downloads/)"
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
echo "     -> $DL/pmc-frontend-${VER}-prod-build.zip"

echo ">>> Zipping backend (Dockerfile + Dockerrun.aws.json + .platform at zip root)"
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' \
    -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' \
    -x 'backend/**/*.pyc' \
    -x 'backend/.env' \
    -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' \
    -x 'backend/tests/*' \
    -x 'backend/keys/*'
echo "     -> $DL/pmc-backend-${VER}.zip"

cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers Limited — Release v49q

## What's new
### 1. Bidding Ops — redesign adopted
Admin `/admin/e/bidding` now uses the supplied Bidding-Ops redesign:
* 7-stage clearance pipeline strip (EMD → Escrow → Admin → Certifier →
  Legal → Accounts → Awarded) with live counts and hot glow on stages
  that have load.
* 4 tabs (Needs PMC / Waiting on supplier / Awarded / All) with dynamic
  counts, sticky search, and a "Hide test data" toggle.
* New table with stage-dot indicators, next-step + owner + waiting-age
  per row, price-anomaly flag (>1.5× estimate), EMD status inline
  (paid / link sent / not paid) and per-row primary action (Confirm /
  Clear KYC / Review / Send link / Resend link / View).
* Bulk-select bar for sending EMD reminders across ticked rows.
* Right side panel: bid detail with clearance timeline, active
  committee (live from `/api/v1/committees`).
* Fully responsive: 3-col collapses to 1-col below 1180 px; table becomes
  stacked cards below 760 px.
* All data comes from `/api/v1/bids` and `/api/v1/committees`; no mock.

### 2. Equal-height tender cards
"Open for bids this week" grid on the homepage and the tenders list now
render every card at identical height with aligned budget / delivery /
category rows. Long titles clamp to 2 lines, top row (tag · ref ·
countdown) stays on one line with ellipsis on the reference number.

### 3. Homepage/tender-list pagination (already in v49p)
`/tenders/live` pagination is fully functional (10 per page, dynamic
label, windowed numbered buttons, filter reset). Tested end-to-end.

## Bundles
* Frontend: `pmc-frontend-v49q-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront)
* Backend: `pmc-backend-v49q.zip` (unchanged since v49p; ship only if
  you need to reset the EB image)

## Deploy — Frontend (S3 + CloudFront)
1. `aws s3 sync --delete` the unzipped `pmc-frontend-v49q-prod-build.zip`
   into your S3 bucket root.
2. Invalidate CloudFront: paths `/*`.
3. CloudFront SPA rule (once): `403` and `404` → `/index.html` with `200`.
4. Verify: open `/admin/e/bidding` as admin — you should see the new
   pipeline strip, tabs and stage-dot table populated with real bids.

## Deploy — Backend (Elastic Beanstalk)
Backend has no code changes vs v49p. If the previous EB deploy is
healthy, skip. Otherwise upload `pmc-backend-v49q.zip` after rebuilding
the EB environment (aborted-deploy state from earlier requires an env
rebuild, not a redeploy of the same version).

## Rollback
Roll back to `v49p` if needed. Nothing in v49q changes routes, APIs or
the database schema.
EOF
echo "     -> $DL/DOWNLOAD_${VER}.md"

echo ">>> Bundle sizes"
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
echo ">>> Done: $VER"
