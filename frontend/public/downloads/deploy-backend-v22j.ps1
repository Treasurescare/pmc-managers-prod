# PMC Backend v22j deploy (PowerShell) - v45c hardened
$ErrorActionPreference = 'Stop'
$AWS_REGION          = 'eu-west-2'
$EB_APP              = 'pmc-backend-prod'
$EB_ENV              = 'pmc-backend-prod'
$S3_ARTIFACTS_BUCKET = 'elasticbeanstalk-eu-west-2-637423434072'
$Zip                 = '.\pmc-backend-v22j.zip'
$VERSION_LABEL       = "v22j-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

$profiles = (aws configure list-profiles 2>$null) -split "`r?`n" | Where-Object { $_ }
if ($profiles -contains 'pmc-admin') { $AWS_PROFILE = 'pmc-admin' }
elseif ($profiles -contains 'default') { $AWS_PROFILE = 'default' }
elseif ($profiles.Count -ge 1) { $AWS_PROFILE = $profiles[0] }
else { throw "No AWS profiles. Run: aws configure --profile pmc-admin" }
Write-Host "Using AWS profile: $AWS_PROFILE" -ForegroundColor Cyan

aws sts get-caller-identity --profile $AWS_PROFILE --region $AWS_REGION | Out-Null
if ($LASTEXITCODE -ne 0) { throw "AWS credentials invalid for '$AWS_PROFILE'. Run: aws configure --profile pmc-admin" }
if (-not (Test-Path $Zip)) { throw "ERROR: $Zip not found in $(Get-Location)" }

Write-Host "== Backend v22j deploy =="
$S3_KEY = "artifacts/pmc-backend/$VERSION_LABEL.zip"
aws s3 cp $Zip "s3://$S3_ARTIFACTS_BUCKET/$S3_KEY" --profile $AWS_PROFILE --region $AWS_REGION --no-progress
if ($LASTEXITCODE -ne 0) { throw "S3 upload failed" }
Write-Host "[1/3] Uploaded"

aws elasticbeanstalk create-application-version --profile $AWS_PROFILE --region $AWS_REGION --application-name $EB_APP --version-label $VERSION_LABEL --description "v22i - WAF-safe DPR analyze-json, pypdf, EMD masters, rating criteria" --source-bundle "S3Bucket=$S3_ARTIFACTS_BUCKET,S3Key=$S3_KEY" --auto-create-application | Out-Null
if ($LASTEXITCODE -ne 0) { throw "create-application-version failed" }
Write-Host "[2/3] Version $VERSION_LABEL registered"

aws elasticbeanstalk update-environment --profile $AWS_PROFILE --region $AWS_REGION --environment-name $EB_ENV --version-label $VERSION_LABEL | Out-Null
if ($LASTEXITCODE -ne 0) { throw "update-environment failed" }
Write-Host "[3/3] EB updating to $VERSION_LABEL - rollout takes 4-6 min"
