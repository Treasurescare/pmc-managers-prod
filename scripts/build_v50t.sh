#!/usr/bin/env bash
# PMC v50t — Production API Origin Fix + Vendor UX Hotfixes
# (a) Runtime + build-time production API routing fix (ensures CloudFront routes /api to EB, never preview)
# (b) Supporting-document upload tiles visibility + re-upload after delete
# (c) My Bids rewritten to use live /bids/mine + live sidebar counts
# (d) Approved categories reflected in Company & KYC header
# (e) Back button on Categories page
set -eu
VER="v50t"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -5
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
# PMC Managers — Release v50t (critical production fix + cumulative v50s)

## 🚨 Critical Fix in this build: Production API Routing
Previous frontend builds baked in `REACT_APP_BACKEND_URL=https://pmc-forest-green...`
which caused browsers visiting `www.pmcmanagers.com` to send login, password reset,
and portal API calls to the preview container instead of your production Elastic Beanstalk
backend.

**Fixed at two levels:**
1. **Runtime Domain Guard in `api.js`:** Whenever hostname is `pmcmanagers.com`
   (or any custom domain), API calls strictly use relative `/api/...` (proxied by
   CloudFront to EB).
2. **Build-time:** Built cleanly with `REACT_APP_BACKEND_URL=""`.

## Vendor UX fixes included (v50s):
- **Upload buttons clearly visible:** Technical / Commercial / Other doc upload tiles are now amber dashed boxes with "+ Click to upload" prompts.
- **Re-upload after delete:** File input resets so re-selecting the same file works.
- **My Bids live:** `/vendor/mybids` rewritten to live API (`/api/v1/bids/mine`).
- **Sidebar badges match live data:** Dynamic counts for Find tenders / My bids / Signatures.
- **Approved categories on Company & KYC:** `/vendor/auth/me` returns `business_categories`.
- **Back button on Categories page:** `← Back` link returns to `/vendor/company`.

## Deploy Instructions
1. Frontend: Extract `pmc-frontend-v50t-prod-build.zip` → Upload to S3 bucket → CloudFront invalidate `/*`
2. Backend: `pmc-backend-v50t.zip` → Deploy to Elastic Beanstalk
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
