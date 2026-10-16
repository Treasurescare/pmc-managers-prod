# PMC Frontend v45 deploy (PowerShell) - v45c hardened
$ErrorActionPreference = 'Stop'
$AWS_REGION    = 'eu-west-2'
$S3_BUCKET     = 'pmc-managers-frontend-prod'
$CLOUDFRONT_ID = 'E2WZT1TMQ0EK9W'
$Zip           = '.\pmc-frontend-v45-build.zip'
$StageDir      = '.\.deploy-v45'

$profiles = (aws configure list-profiles 2>$null) -split "`r?`n" | Where-Object { $_ }
if ($profiles -contains 'pmc-admin') { $AWS_PROFILE = 'pmc-admin' }
elseif ($profiles -contains 'default') { $AWS_PROFILE = 'default' }
elseif ($profiles.Count -ge 1) { $AWS_PROFILE = $profiles[0] }
else { throw "No AWS profiles. Run: aws configure --profile pmc-admin" }
Write-Host "Using AWS profile: $AWS_PROFILE" -ForegroundColor Cyan

aws sts get-caller-identity --profile $AWS_PROFILE --region $AWS_REGION | Out-Null
if ($LASTEXITCODE -ne 0) { throw "AWS credentials invalid for '$AWS_PROFILE'. Run: aws configure --profile pmc-admin" }
if (-not (Test-Path $Zip)) { throw "ERROR: $Zip not found in $(Get-Location)" }

Write-Host "== Frontend v45 deploy =="
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Path $StageDir | Out-Null
Expand-Archive -LiteralPath $Zip -DestinationPath $StageDir -Force
$Main = (Get-ChildItem "$StageDir\static\js\main.*.js" | Select-Object -First 1).Name
Write-Host "[1/4] Unzipped - bundle $Main"

aws s3 sync "$StageDir\static\" "s3://$S3_BUCKET/static/" --profile $AWS_PROFILE --region $AWS_REGION --delete --cache-control "public, max-age=31536000, immutable" --no-progress
if ($LASTEXITCODE -ne 0) { throw "S3 static sync failed" }
Write-Host "[2/4] Static synced"

aws s3 sync "$StageDir\" "s3://$S3_BUCKET/" --profile $AWS_PROFILE --region $AWS_REGION --exclude "static/*" --cache-control "public, max-age=0, must-revalidate" --no-progress
if ($LASTEXITCODE -ne 0) { throw "S3 root sync failed" }
Write-Host "[3/4] Root synced"

$InvId = aws cloudfront create-invalidation --profile $AWS_PROFILE --distribution-id $CLOUDFRONT_ID --paths "/" "/index.html" "/asset-manifest.json" "/manifest.json" "/downloads/*" --query "Invalidation.Id" --output text
if ($LASTEXITCODE -ne 0) { throw "Invalidation failed" }
Write-Host "[4/4] Invalidation $InvId - hard-refresh site in 1-3 min"
