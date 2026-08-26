#!/usr/bin/env bash
# Build backend-v7-hardened.zip for AWS Elastic Beanstalk.
# - Strips _temp_downloads (per ANCHOR.md rule #5)
# - Includes Dockerfile + Dockerrun.aws.json at zip root
# - Ships hardened config.py + startup diagnostics
set -euo pipefail

APP_ROOT="/app"
STAGE=$(mktemp -d)
OUT_ZIP="${APP_ROOT}/pmc-backend-v7-hardened.zip"

echo "==> Staging in ${STAGE}"
cp "${APP_ROOT}/Dockerfile" "${STAGE}/"
cp "${APP_ROOT}/Dockerrun.aws.json" "${STAGE}/"
cp -r "${APP_ROOT}/backend" "${STAGE}/backend"

echo "==> Stripping _temp_downloads from server.py"
python3 - <<'PY'
from pathlib import Path
p = Path("${STAGE}/backend/server.py".replace("${STAGE}", "$STAGE"))
PY
# Easier via sed
sed -i \
  -e 's/, _temp_downloads,/,/g' \
  -e 's/    _temp_downloads,//g' \
  -e '/app\.include_router(_temp_downloads\.router)/d' \
  "${STAGE}/backend/server.py"

echo "==> Removing _temp_downloads.py file"
rm -f "${STAGE}/backend/routers/_temp_downloads.py"

echo "==> Sanity check: grep should return nothing"
if grep -R "_temp_downloads" "${STAGE}/backend/" ; then
  echo "!! _temp_downloads still referenced — aborting" >&2
  exit 2
fi

echo "==> Removing __pycache__ / .pyc"
find "${STAGE}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${STAGE}" -type f -name "*.pyc" -delete 2>/dev/null || true

echo "==> Removing dev-only files"
rm -rf "${STAGE}/backend/tests" 2>/dev/null || true
rm -f "${STAGE}/backend/pytest.ini" 2>/dev/null || true

echo "==> Zipping"
rm -f "${OUT_ZIP}"
cd "${STAGE}" && zip -qr "${OUT_ZIP}" .
ls -lh "${OUT_ZIP}"

echo "==> Zip contents (top-level):"
unzip -l "${OUT_ZIP}" | head -10
echo "..."
unzip -l "${OUT_ZIP}" | tail -5

echo "==> Cleanup"
rm -rf "${STAGE}"
echo "DONE: ${OUT_ZIP}"
