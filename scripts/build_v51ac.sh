#!/usr/bin/env bash
# PMC v51ac — Expires-fields hidden on panels without an expiry concept +
# per-row Edit sections link on every non-approved registration.
set -eu
VER="v51ac"
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
# PMC Managers — Release v51ac (cumulative, supersedes v51ab)

## What's new in v51ac
1. **Edit sections for every non-approved registration.** In Admin →
   Market → Registrations each row for a Draft / Submitted / Needs
   clarification registration now shows an "Edit sections" link that
   opens the vendor's own 5-section flow in a new tab (admin can save
   on behalf of the vendor). Approved rows link to the full vendor
   profile editor at /admin/vendors/{ref}/edit (added in v51aa).
2. **Expires from / Expires to filters removed from panels that don't
   have an expiry concept** (Awards, Billing, Escrow/EMD, Evaluation,
   L1 comparison, DocuSign). Reverse auctions still exposes Expires
   from / to because reverse-auction rows carry an `end_at`.
3. All v51ab features retained: shared Money filter bar, reverse
   auction Edit per row, bulk Section A–E CSV template, 409 structured
   detail, Section A–E vendor-profile editor, auction readiness badge
   + Resend auto-send, notice filter URL memory, Money-pages crash fix.

Backend: new `GET /api/v1/registrations/admin/{rid}/resume-link` for
admins to open any non-approved registration in the vendor-facing
5-section flow (audit logged).

## Deploy
Upload pmc-frontend-v51ac-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51ac.zip to Elastic Beanstalk.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
