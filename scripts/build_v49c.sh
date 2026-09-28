#!/usr/bin/env bash
# PMC v49c — build & package production frontend + backend bundles for AWS.
set -eu

VER="v49c"
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

echo ">>> Zipping backend (includes Dockerfile, Dockerrun.aws.json, .platform at zip root)"
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

echo ">>> Writing release notes"
cat > "$DL/DOWNLOAD_${VER}.md" << EOF
# PMC Managers Limited — Release ${VER}

## What's in this release
* **Option E v2 — 55-template design overhaul** wired behind \`?ui=e\`
  (legacy Navy UI remains the default).
* **Live-data v49c**: homepage stats bar (17/41/48/911), tenders list rows &
  filters, notice detail per-ref fetch, vendor home KPIs (Active/Closing/
  Matched/KYC now driven by \`/api/v1/vendor/auth/me\` + \`/vendor/bids\`),
  **admin dashboard EMD KPI now shows real USD-equivalent from
  \`/api/v1/meta/public/escrow-summary\`** (per-currency totals plus paid/pending counts),
  admin pipeline, KPIs and sidebar counts all real.
* **Option E email templates** in \`/app/backend/emails_option_e.py\` (6 typed
  builders, plugs into existing Resend integration).
* **Design references**: \`/design/dialogs\`, \`/states\`, \`/emails\`,
  \`/printables\` are showcase surfaces; safe to link from admin docs.

## Bundles
* Frontend: \`pmc-frontend-${VER}-prod-build.zip\`
  (built with \`REACT_APP_BACKEND_URL=""\` → same-origin S3/CloudFront)
* Backend:  \`pmc-backend-${VER}.zip\` (excludes \`.env\`, \`__pycache__\`)

## Deploy
* Frontend: unzip into your S3 bucket; invalidate CloudFront cache.
* Backend: unzip into your Elastic Beanstalk root. No new env vars needed.

## New/changed endpoints
* \`GET /api/v1/meta/public/stats\` — now includes \`ledger_events\`.
* \`GET /api/v1/meta/public/escrow-summary\` — new; per-currency EMD totals +
  USD-equivalent estimate + paid/pending counts. No PII.

## Rollback
* Roll back to \`v48c\` if needed, or disable Option E at runtime with
  \`?ui=default\` on any URL.
EOF
echo "     -> $DL/DOWNLOAD_${VER}.md"

echo ">>> Sizes"
ls -lh "$DL"/pmc-*"${VER}"*.zip "$DL/DOWNLOAD_${VER}.md"

echo ">>> Done."
