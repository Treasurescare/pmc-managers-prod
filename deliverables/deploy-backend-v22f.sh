#!/usr/bin/env bash
# ============================================================================
# PMC Managers v2 — Backend v22f deploy to Elastic Beanstalk
# ----------------------------------------------------------------------------
# Ships:  Batches #9 (evaluation validators + score-lock guard + /me
#         Cache-Control no-store) + #9c (escrow same-email governance guard)
# Target: EB application `pmc-backend-prod` in eu-west-2
# ============================================================================
set -euo pipefail

: "${AWS_REGION:=eu-west-2}"
: "${AWS_PROFILE:=pmc-admin}"
: "${EB_APP:=pmc-backend-prod}"
: "${EB_ENV:=pmc-backend-prod}"          # override if your env name differs
: "${S3_ARTIFACTS_BUCKET:=elasticbeanstalk-eu-west-2-637423434072}"
: "${ZIP:=./pmc-backend-v22f.zip}"
: "${VERSION_LABEL:=v22f-$(date -u +%Y%m%d-%H%M%S)}"

echo "=========================================================="
echo "  PMC Backend v22f deploy"
echo "  EB app / env    : $EB_APP  /  $EB_ENV"
echo "  Version label   : $VERSION_LABEL"
echo "  Zip             : $ZIP"
echo "=========================================================="

[[ -f "$ZIP" ]] || { echo "ERROR: $ZIP not found in $(pwd)"; exit 1; }

# ---- 1. Upload the artifact to the EB pipeline bucket -----------------------
S3_KEY="artifacts/pmc-backend/${VERSION_LABEL}.zip"
aws s3 cp "$ZIP" "s3://${S3_ARTIFACTS_BUCKET}/${S3_KEY}" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" --no-progress
echo "[1/3] Uploaded to s3://${S3_ARTIFACTS_BUCKET}/${S3_KEY}"

# ---- 2. Register a new EB application version -------------------------------
aws elasticbeanstalk create-application-version \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --application-name "$EB_APP" \
  --version-label "$VERSION_LABEL" \
  --description "Batch #9 (evaluations + /me no-store) + #9c (escrow same-email guard)" \
  --source-bundle "S3Bucket=${S3_ARTIFACTS_BUCKET},S3Key=${S3_KEY}" \
  --auto-create-application \
  >/dev/null
echo "[2/3] EB application version $VERSION_LABEL registered"

# ---- 3. Point the environment at the new version ---------------------------
aws elasticbeanstalk update-environment \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --environment-name "$EB_ENV" \
  --version-label "$VERSION_LABEL" \
  >/dev/null
echo "[3/3] EB environment $EB_ENV updating to $VERSION_LABEL"
echo
echo "✅ Deploy triggered. Watch progress with:"
echo "   aws --profile $AWS_PROFILE --region $AWS_REGION elasticbeanstalk describe-environments \\"
echo "     --environment-names $EB_ENV \\"
echo "     --query 'Environments[0].[Status,Health,VersionLabel]' --output table"
echo
echo "   Full rollout usually takes 3-6 minutes."
