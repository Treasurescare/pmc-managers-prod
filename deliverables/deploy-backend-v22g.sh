#!/usr/bin/env bash
# ============================================================================
# PMC Managers v2 — Backend v22g deploy to Elastic Beanstalk
# ----------------------------------------------------------------------------
# Ships:  Help metadata endpoints (/api/v1/meta/help) that power the in-app
#         Help tab. No breaking changes — safe to redeploy on top of v22f.
# Target: EB application `pmc-backend-prod` in eu-west-2
# ============================================================================
set -euo pipefail

: "${AWS_REGION:=eu-west-2}"
: "${AWS_PROFILE:=pmc-admin}"
: "${EB_APP:=pmc-backend-prod}"
: "${EB_ENV:=pmc-backend-prod}"
: "${S3_ARTIFACTS_BUCKET:=elasticbeanstalk-eu-west-2-637423434072}"
: "${ZIP:=./pmc-backend-v22g.zip}"
: "${VERSION_LABEL:=v22g-$(date -u +%Y%m%d-%H%M%S)}"

echo "=========================================================="
echo "  PMC Backend v22g deploy"
echo "  EB app / env    : $EB_APP  /  $EB_ENV"
echo "  Version label   : $VERSION_LABEL"
echo "  Zip             : $ZIP"
echo "=========================================================="

[[ -f "$ZIP" ]] || { echo "ERROR: $ZIP not found in $(pwd)"; exit 1; }

# ---- 1. Upload to EB pipeline bucket -------------------------------------
S3_KEY="artifacts/pmc-backend/${VERSION_LABEL}.zip"
aws s3 cp "$ZIP" "s3://${S3_ARTIFACTS_BUCKET}/${S3_KEY}" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" --no-progress
echo "[1/3] Uploaded to s3://${S3_ARTIFACTS_BUCKET}/${S3_KEY}"

# ---- 2. Register new EB application version -----------------------------
aws elasticbeanstalk create-application-version \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --application-name "$EB_APP" \
  --version-label "$VERSION_LABEL" \
  --description "v22g — Help metadata endpoints for in-app Help tab (v43)" \
  --source-bundle "S3Bucket=${S3_ARTIFACTS_BUCKET},S3Key=${S3_KEY}" \
  --auto-create-application \
  >/dev/null
echo "[2/3] EB application version $VERSION_LABEL registered"

# ---- 3. Point env at the new version ------------------------------------
aws elasticbeanstalk update-environment \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --environment-name "$EB_ENV" \
  --version-label "$VERSION_LABEL" \
  >/dev/null
echo "[3/3] EB environment $EB_ENV updating to $VERSION_LABEL"
echo
echo "✅ Backend v22g deploy triggered. Watch with:"
echo "   aws --profile $AWS_PROFILE --region $AWS_REGION elasticbeanstalk describe-environments \\"
echo "     --environment-names $EB_ENV \\"
echo "     --query 'Environments[0].[Status,Health,VersionLabel]' --output table"
echo
echo "   Full rollout usually takes 3-6 minutes."
