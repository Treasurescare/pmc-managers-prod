#!/usr/bin/env bash
# Run this after CloudFront `/api/*` behavior + v22 frontend deploy + invalidation.
# Expected: every line prints HTTP 200 (or valid JSON body).

FE="https://www.pmcmanagers.com"

echo "1) Frontend HTML served"
curl -s --max-time 10 -o /dev/null -w "   HTTP=%{http_code} time=%{time_total}s\n" "$FE/"

echo "2) Backend health via CloudFront (was the missing link)"
curl -s --max-time 15 -w "\n   HTTP=%{http_code} time=%{time_total}s\n" "$FE/api/v1/meta/health"

echo "3) Admin login via CloudFront (real API call)"
curl -s --max-time 15 -w "\n   HTTP=%{http_code}\n" -X POST \
  "$FE/api/v1/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"adminsupport@pmcmanagers.com","password":"Admin@12345"}' | head -c 400
echo

echo "4) JS bundle no longer references EB URL"
JS=$(curl -s "$FE/" | grep -oE 'main\.[a-f0-9]+\.js' | head -1)
if curl -s "$FE/static/js/$JS" | grep -qE 'elasticbeanstalk\.com'; then
  echo "   ⚠ EB URL still present — CloudFront may be serving cached JS. Re-invalidate /*."
else
  echo "   ✓ clean — API calls will be same-origin"
fi

echo "5) Public notices endpoint (real DB read)"
curl -s --max-time 15 -w "\n   HTTP=%{http_code}\n" "$FE/api/v1/notices?public=1&limit=1" | head -c 300
echo
