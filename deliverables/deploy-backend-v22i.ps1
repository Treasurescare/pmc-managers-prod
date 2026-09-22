$ErrorActionPreference = 'Stop'
$AWS_REGION            = 'eu-west-2'
$AWS_PROFILE           = 'pmc-admin'
$EB_APP                = 'pmc-backend-prod'
$EB_ENV                = 'pmc-backend-prod'
$S3_ARTIFACTS_BUCKET   = 'elasticbeanstalk-eu-west-2-637423434072'
$Zip                   = '.\pmc-backend-v22i.zip'
$VERSION_LABEL         = "v22i-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

Write-Host "=========================================================="
Write-Host "  PMC Backend v22i deploy (v45 Tender Pro)"
Write-Host "  EB app / env  : $EB_APP  /  $EB_ENV"
Write-Host "  Version label : $VERSION_LABEL"
Write-Host "  Zip           : $Zip"
Write-Host "=========================================================="
if (-not (Test-Path $Zip)) { throw "ERROR: $Zip not found in $(Get-Location)" }

$S3_KEY = "artifacts/pmc-backend/$VERSION_LABEL.zip"
aws s3 cp $Zip "s3://$S3_ARTIFACTS_BUCKET/$S3_KEY" `
  --profile $AWS_PROFILE --region $AWS_REGION --no-progress
Write-Host "[1/3] Uploaded to s3://$S3_ARTIFACTS_BUCKET/$S3_KEY"

aws elasticbeanstalk create-application-version `
  --profile $AWS_PROFILE --region $AWS_REGION `
  --application-name $EB_APP `
  --version-label $VERSION_LABEL `
  --description "v22i — Tender Pro: DPR AI generation, EMD masters, rating criteria, per-section save (v45)" `
  --source-bundle "S3Bucket=$S3_ARTIFACTS_BUCKET,S3Key=$S3_KEY" `
  --auto-create-application | Out-Null
Write-Host "[2/3] EB application version $VERSION_LABEL registered"

aws elasticbeanstalk update-environment `
  --profile $AWS_PROFILE --region $AWS_REGION `
  --environment-name $EB_ENV `
  --version-label $VERSION_LABEL | Out-Null
Write-Host "[3/3] EB environment $EB_ENV updating to $VERSION_LABEL"
Write-Host ""
Write-Host "Backend v22i deploy triggered. Watch with:"
Write-Host "  aws --profile $AWS_PROFILE --region $AWS_REGION elasticbeanstalk describe-environments ``"
Write-Host "    --environment-names $EB_ENV ``"
Write-Host "    --query 'Environments[0].[Status,Health,VersionLabel]' --output table"
