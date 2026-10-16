#!/usr/bin/env bash
# ============================================================================
# PMC Managers v2 — Frontend v45 Deploy (macOS / Linux)
# Target: s3://pmc-managers-frontend-prod + CloudFront E2WZT1TMQ0EK9W
# ============================================================================
set -euo pipefail

: "${AWS_REGION:=eu-west-2}"
: "${AWS_PROFILE:=pmc-admin}"
: "${S3_BUCKET:=pmc-managers-frontend-prod}"
: "${CLOUDFRONT_ID:=E2WZT1TMQ0EK9W}"
: "${ZIP:=./pmc-frontend-v45-build.zip}"
: "${STAGE_DIR:=./.deploy-v45}"

echo "=========================================================="
echo "  PMC Frontend v45 deploy (macOS)"
echo "  S3 bucket        : $S3_BUCKET"
echo "  CloudFront dist  : $CLOUDFRONT_ID"
echo "  Zip              : $ZIP"
echo "  Profile          : $AWS_PROFILE"
echo "=========================================================="

[[ -f "$ZIP" ]] || { echo "ERROR: $ZIP not found in $(pwd)"; exit 1; }

# Preflight: test AWS credentials
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null

# 1. Unzip
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
unzip -q "$ZIP" -d "$STAGE_DIR"
echo "[1/4] Unzipped $(du -sh "$STAGE_DIR" | cut -f1) into $STAGE_DIR"

MAIN=$(ls "$STAGE_DIR"/static/js/main.*.js | head -1 | xargs basename)
echo "     Bundled main.js : $MAIN"

# 2. Sync hashed static assets (long cache)
aws s3 sync "$STAGE_DIR/static/" "s3://$S3_BUCKET/static/" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --no-progress
echo "[2/4] Static assets synced (long cache)"

# 3. Sync root assets with no-cache
aws s3 sync "$STAGE_DIR/" "s3://$S3_BUCKET/" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --exclude "static/*" \
  --cache-control "public, max-age=0, must-revalidate" \
  --no-progress
echo "[3/4] index.html + manifest + downloads/ synced (no-cache)"

# 4. Invalidate CloudFront
INV_ID=$(aws cloudfront create-invalidation \
  --profile "$AWS_PROFILE" \
  --distribution-id "$CLOUDFRONT_ID" \
  --paths "/" "/index.html" "/asset-manifest.json" "/manifest.json" "/downloads/*" \
  --query 'Invalidation.Id' --output text)
echo "[4/4] CloudFront invalidation created: $INV_ID"
echo
echo "Frontend v45 deploy complete."
echo "   Verify: https://www.pmcmanagers.com/static/js/$MAIN"
echo "   Wait  : invalidation takes ~1-3 min to propagate."
echo "   Clean : rm -rf $STAGE_DIR"
