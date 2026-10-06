#!/usr/bin/env bash
# PMC v51z — 3 enhancements on top of v51y:
#  1. Reverse-auction Invite panel now auto-emails vendors via Resend
#     (default-on checkbox, backend falls back to built-in template body).
#  2. Each Draft auction row shows a "0/2 participants" / "✓ ready" badge.
#  3. Admin Notices filter state is mirrored to the URL so operators can
#     bookmark / share the exact search they built.
set -eu
VER="v51z"
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
# PMC Managers — Release v51z (cumulative, supersedes v51o–v51y)

## What's new in v51z (built on top of v51y Money-pages crash fix)

### 1. Reverse auction — Email invites now via Resend
Invite panel on each auction row has a new "Email vendors now via Resend"
checkbox (default **on**). When checked, each pasted email is both given
a unique join link AND auto-emailed from the verified pmcmanagers.com
Resend domain, using the default auction-invite template (or a built-in
fallback body if no template is seeded). Un-check it if you want links
only, no email.

### 2. Auction readiness badge
Every Draft auction row now shows a small badge next to the status pill:
  * amber `0/2 participants` / `1/2 participants` while gated
  * emerald `✓ 2/2 ready` once two or more vendors have registered
Backed by a new `participant_count` field on the list endpoint — one
round-trip for the whole table.

### 3. Admin Notices — filter state in URL
Every filter in the Notices filter bar is now reflected in the query
string (`?status=`, `?q=`, `?creator=`, `?from=`, `?to=`, `?templates=`).
Operators can bookmark a search, share it with a colleague, or jump
straight to it from a dashboard pipeline link. Clear wipes all params.

## Deploy
Upload `pmc-frontend-v51z-prod-build.zip` to S3, invalidate CloudFront
`/*`, push `pmc-backend-v51z.zip` to Elastic Beanstalk. No new secrets —
the Resend key you already have is reused.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
