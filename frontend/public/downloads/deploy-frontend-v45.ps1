$ErrorActionPreference = 'Stop'
$AWS_REGION     = 'eu-west-2'
$AWS_PROFILE    = 'pmc-admin'
$S3_BUCKET      = 'pmc-managers-frontend-prod'
$CLOUDFRONT_ID  = 'E2WZT1TMQ0EK9W'
$Zip            = '.\pmc-frontend-v45-build.zip'
$StageDir       = '.\.deploy-v45'

Write-Host "=========================================================="
Write-Host "  PMC Frontend v45 deploy (Tender Pro UI)"
Write-Host "  S3 bucket       : $S3_BUCKET"
Write-Host "  CloudFront dist : $CLOUDFRONT_ID"
Write-Host "  Zip             : $Zip"
Write-Host "=========================================================="
if (-not (Test-Path $Zip)) { throw "ERROR: $Zip not found in $(Get-Location)" }

if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Path $StageDir | Out-Null
Expand-Archive -LiteralPath $Zip -DestinationPath $StageDir -Force
$size = (Get-ChildItem $StageDir -Recurse | Measure-Object -Property Length -Sum).Sum
Write-Host ("[1/4] Unzipped {0:N1} MB into {1}" -f ($size/1MB), $StageDir)
$Main = (Get-ChildItem "$StageDir\static\js\main.*.js" | Select-Object -First 1).Name
Write-Host "     Bundled main.js : $Main"

aws s3 sync "$StageDir\static\" "s3://$S3_BUCKET/static/" `
  --profile $AWS_PROFILE --region $AWS_REGION `
  --delete `
  --cache-control "public, max-age=31536000, immutable" `
  --no-progress
Write-Host "[2/4] Static assets synced (long cache)"

aws s3 sync "$StageDir\" "s3://$S3_BUCKET/" `
  --profile $AWS_PROFILE --region $AWS_REGION `
  --exclude "static/*" `
  --cache-control "public, max-age=0, must-revalidate" `
  --no-progress
Write-Host "[3/4] index.html + manifest + downloads/ synced (no-cache)"

$InvId = aws cloudfront create-invalidation `
  --profile $AWS_PROFILE `
  --distribution-id $CLOUDFRONT_ID `
  --paths "/" "/index.html" "/asset-manifest.json" "/manifest.json" "/downloads/*" `
  --query 'Invalidation.Id' --output text
Write-Host "[4/4] CloudFront invalidation created: $InvId"
Write-Host ""
Write-Host "Frontend v45 deploy complete."
Write-Host "   Verify: https://www.pmcmanagers.com/static/js/$Main"
