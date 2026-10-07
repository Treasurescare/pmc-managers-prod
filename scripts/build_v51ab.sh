#!/usr/bin/env bash
# PMC v51ab — Money & compliance filter bar + reverse-auction edit + bundle refresh.
set -eu
VER="v51ab"
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
# PMC Managers — Release v51ab (cumulative, supersedes v51aa)

## What's new in v51ab
1. **Reverse auctions** — new per-row **Edit** button on every draft auction
   that opens an inline form to change title, start/floor/decrement prices,
   duration, currency, anti-snipe seconds (backend PATCH /reverse-auctions/{aid}
   with validations).
2. **Working Money & compliance search bar on every panel**:
   - Reverse auctions, Bidding ops, Awards, Billing, Escrow / EMD,
     Evaluation, L1 comparison, DocuSign.
   - Shared `MoneyFilterBar` component: search tender/title, created-by,
     created from→to date, expires from→to date, status dropdown, Clear.
   - Reverse auctions filters its React state array (true client-side filter);
     Bidding ops and legacy panels filter their rendered rows via a
     MutationObserver so even DOM-rendered tables respond.
3. All v51aa fixes carried forward: Money crash fix, auction invites + Resend
   auto-send + readiness badge, Notices filter URL memory, blank Contact Email
   422 coercion, bulk-invite Sections A–E CSV, 409 "already active" structured
   detail, full vendor-profile editor at /admin/vendors/:ref/edit.

## Deploy
Upload pmc-frontend-v51ab-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51ab.zip to Elastic Beanstalk. No new secrets.

## Up next (post-v51ab, from the user's roadmap)
Corrigenda module (edit live tenders with amendment trail + vendor re-ack).
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
