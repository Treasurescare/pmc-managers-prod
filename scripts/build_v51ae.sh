#!/usr/bin/env bash
# PMC v51ae — Google Search Console verification meta tag in index.html
# so the Google Play Console "Verify your organization's website" step passes
# on https://pmcmanagers.com.
set -eu
VER="v51ae"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51ae (frontend only)

## What's new in v51ae
- Added the Google Search Console verification meta tag to `index.html`:
  `<meta name="google-site-verification" content="t7scPgT9ZxpjYxkyRAyB8cCvfrCh04IAO6XcvAvS4r0" />`
- Purpose: prove ownership of https://pmcmanagers.com so the Google Play
  Console "Verify your organization's website" requirement resolves.

## Deploy (frontend only — no backend change)
1. Upload `pmc-frontend-v51ae-prod-build.zip` contents to the production S3 bucket.
2. Invalidate CloudFront — **/index.html is the critical path** (or `/*` to be safe).
3. Confirm live: `curl -s https://pmcmanagers.com | grep google-site-verification`
   should print the meta tag.
4. Back in Google Search Console click **Verify**, then in Play Console click
   **Verify website** — it will resolve immediately.
EOF
echo "built $VER"
ls -la "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/DOWNLOAD_${VER}.md"
