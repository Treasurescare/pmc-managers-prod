#!/usr/bin/env bash
# Run this AFTER you've added the :443 HTTPS listener on the EB load balancer.
# Expected: every line prints HTTP 200 (or the JSON body).

BACKEND="https://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com"
FRONTEND="https://www.pmcmanagers.com"

echo "1) Backend HTTPS health"
curl -s --max-time 15 -w "\n   HTTP=%{http_code}\n" "$BACKEND/api/v1/meta/health"

echo "2) Backend admin login"
curl -s --max-time 15 -w "\n   HTTP=%{http_code}\n" -X POST \
  "$BACKEND/api/v1/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"adminsupport@pmcmanagers.com","password":"Admin@12345"}' | head -c 400
echo

echo "3) Frontend serves the new bundle"
curl -s --max-time 10 "$FRONTEND/" | grep -oE 'main\.[a-f0-9]+\.js' | head -1

echo "4) Frontend JS actually points at the EB backend"
JS=$(curl -s "$FRONTEND/" | grep -oE 'main\.[a-f0-9]+\.js' | head -1)
curl -s "$FRONTEND/static/js/$JS" | grep -oE "https://pmc-backend-prod[^\"']+elasticbeanstalk\.com" | sort -u | head -1
