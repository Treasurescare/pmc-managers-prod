#!/usr/bin/env bash
# ============================================================================
# PMC Managers v2 — Frontend v40 deploy to AWS S3 + CloudFront
# ----------------------------------------------------------------------------
# Ships:  Batches #9 (11 tracker items) + #9b (committee CSRF) + #9c (escrow
#         governance) + #9d (loud error toasts). New bundle: main.727b5a39.js
# Target: s3://pmc-managers-frontend-prod  +  CloudFront E2WZT1TMQ0EK9W
# Live:   https://www.pmcmanagers.com  (also https://d2h9tkca2zjofy.cloudfront.net)
#
# Run this from any machine with AWS CLI configured (profile `pmc-admin`).
# All variables can be overridden via env vars if your account uses different
# names.
# ============================================================================
set -euo pipefail

# ---- Config (override with env vars if needed) -----------------------------
: "${AWS_REGION:=eu-west-2}"
: "${AWS_PROFILE:=pmc-admin}"
: "${S3_BUCKET:=pmc-managers-frontend-prod}"
: "${CLOUDFRONT_ID:=E2WZT1TMQ0EK9W}"
: "${ZIP:=./pmc-frontend-v40-build.zip}"
: "${STAGE_DIR:=./.deploy-v40}"

echo "=========================================================="
echo "  PMC Frontend v40 deploy"
echo "  S3 bucket        : $S3_BUCKET"
echo "  CloudFront dist  : $CLOUDFRONT_ID"
echo "  Zip              : $ZIP"
echo "=========================================================="

[[ -f "$ZIP" ]] || { echo "ERROR: $ZIP not found in $(pwd)"; exit 1; }

# ---- 1. Unzip ---------------------------------------------------------------
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
unzip -q "$ZIP" -d "$STAGE_DIR"
echo "[1/4] Unzipped $(du -sh "$STAGE_DIR" | cut -f1) into $STAGE_DIR"

# Sanity-check the new bundle hash is present
MAIN=$(ls "$STAGE_DIR"/static/js/main.*.js | head -1 | xargs basename)
echo "     Bundled main.js : $MAIN   (expected main.727b5a39.js)"

# ---- 2. Sync hashed static assets (long cache) ------------------------------
aws s3 sync "$STAGE_DIR/static/" "s3://$S3_BUCKET/static/" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --no-progress
echo "[2/4] Static assets synced (long cache)"

# ---- 3. Sync everything else with no-cache (index.html, manifest, etc.) -----
aws s3 sync "$STAGE_DIR/" "s3://$S3_BUCKET/" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --exclude "static/*" \
  --cache-control "public, max-age=0, must-revalidate" \
  --no-progress
echo "[3/4] index.html + manifest synced (no-cache)"

# ---- 4. Invalidate CloudFront for html + manifest ---------------------------
INV_ID=$(aws cloudfront create-invalidation \
  --profile "$AWS_PROFILE" \
  --distribution-id "$CLOUDFRONT_ID" \
  --paths "/" "/index.html" "/asset-manifest.json" "/manifest.json" \
  --query 'Invalidation.Id' --output text)
echo "[4/4] CloudFront invalidation created: $INV_ID"
echo
echo "✅ Deploy complete."
echo "   Verify: https://www.pmcmanagers.com/static/js/$MAIN"
echo "   Wait  : the invalidation takes ~1-3 min to propagate."
echo "   Clean : rm -rf $STAGE_DIR"
