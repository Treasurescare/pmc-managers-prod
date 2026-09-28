#!/usr/bin/env bash
# PMC v49b — build & package production frontend + backend bundles for AWS.
#
# Usage:  bash /app/scripts/build_v49b.sh
#
# What it does:
#   * Frontend: yarn build with REACT_APP_BACKEND_URL="" (same-origin S3/CloudFront)
#   * Zips build/ into public/downloads/pmc-frontend-v49b-prod-build.zip
#   * Backend: zips /app/backend without __pycache__ / .pyc / .env into
#     public/downloads/pmc-backend-v49b.zip
#   * Emits DOWNLOAD_v49b.md release notes alongside the bundles
set -eu

VER="v49b"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"

echo ">>> Building frontend ($VER) with same-origin backend URL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build

echo ">>> Zipping frontend build"
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
echo "     -> $DL/pmc-frontend-${VER}-prod-build.zip"

echo ">>> Zipping backend"
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend \
    -x 'backend/__pycache__/*' \
    -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' \
    -x 'backend/**/*.pyc' \
    -x 'backend/.env' \
    -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*'
echo "     -> $DL/pmc-backend-${VER}.zip"

echo ">>> Writing release notes"
cat > "$DL/DOWNLOAD_${VER}.md" << EOF
# PMC Managers Limited — Release ${VER}

## What's in this release
* **Option E v2 — complete 55-template design overhaul** wired behind \`?ui=e\`
  (legacy Navy UI remains the default for existing users).
* **Real data**: Option E homepage, tenders list, and vendor home now pull live
  data from the same public/vendor APIs the legacy UI uses. See
  \`/app/frontend/src/lib/pmcELiveData.js\` for the runtime patching layer.
* **Option E email templates**: 6 branded templates in
  \`/app/backend/emails_option_e.py\` (new-tender match, corrigendum, deadline,
  EMD received, award issued, result published) sent via existing Resend
  integration in \`emails.py\`.
* **Design references** (\`/design/dialogs\`, \`/states\`, \`/emails\`,
  \`/printables\`) are showcase surfaces only — safe to link from admin docs.

## Bundles
* Frontend: \`pmc-frontend-${VER}-prod-build.zip\`
  (already built with \`REACT_APP_BACKEND_URL=""\` → same-origin S3/CloudFront)
* Backend:  \`pmc-backend-${VER}.zip\` (excludes \`.env\`, \`__pycache__\`)

## Deploy
* Frontend: unzip into your S3 bucket; invalidate CloudFront cache.
* Backend: unzip into your Elastic Beanstalk deployment root. No env-var changes
  from ${VER%b}a; existing keys (\`RESEND_API_KEY\`, \`STRIPE_*\`, \`DOCUSIGN_*\`,
  \`MONGO_URL\`, \`DB_NAME\`) apply unchanged.

## Rollback
* Roll back to \`v48c\` if needed — Option E can also be disabled at runtime by
  appending \`?ui=default\` to any URL.
EOF
echo "     -> $DL/DOWNLOAD_${VER}.md"

echo ">>> Sizes"
ls -lh "$DL"/pmc-*"${VER}"*.zip "$DL/DOWNLOAD_${VER}.md"

echo ">>> Done."
