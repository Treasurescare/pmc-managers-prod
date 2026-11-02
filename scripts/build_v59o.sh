#!/usr/bin/env bash
# PMC v59o — fix supplier registration 422 (UNSPSC fields).
set -eu
VER="v59o"; ROOT="/app"; DL="$ROOT/frontend/public/downloads"; mkdir -p "$DL"
cd "$ROOT/backend"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" . \
    -x '__pycache__/*' -x '**/__pycache__/*' -x '*.pyc' -x '**/*.pyc' \
    -x '.env' -x 'venv/*' -x '.pytest_cache/*' -x '.ruff_cache/*' -x 'keys/*' -x 'tests/*'
echo "BACKEND ZIP:"; ls -lh "$DL/pmc-backend-${VER}.zip"
cd "$ROOT/frontend"
STASH=/tmp/pmc_dl_stash_${VER}; rm -rf "$STASH"
if [ -d public/downloads ]; then mv public/downloads "$STASH"; fi
restore() { if [ -d "$STASH" ]; then rm -rf public/downloads; mv "$STASH" public/downloads; fi; }
trap restore EXIT
REACT_APP_BACKEND_URL="" REACT_APP_PUBLIC_SITE_URL="https://www.pmcmanagers.com" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
rm -rf public/downloads; mv "$STASH" public/downloads; trap - EXIT
OUT="$DL/pmc-frontend-${VER}-prod-build.zip"; rm -f "$OUT"
( cd build && zip -rq "$OUT" . -x 'downloads/*' -x 'downloads' ); rm -rf /tmp/mz; mkdir -p /tmp/mz/downloads/manual; cp public/downloads/manual/PMC_v4_Master_Training_Manual.pdf public/downloads/manual/sections.json /tmp/mz/downloads/manual/; ( cd /tmp/mz && zip -rq "$OUT" downloads )
echo "FRONTEND ZIP:"; ls -lh "$OUT"; echo "ALL DONE ${VER}"

echo "Running secret scan on bundles..."
if ! python3 "$ROOT/scripts/secret_scan.py" "$DL/pmc-backend-${VER}.zip" "$DL/pmc-frontend-${VER}-prod-build.zip"; then
  rm -f "$DL/pmc-backend-${VER}.zip" "$DL/pmc-frontend-${VER}-prod-build.zip"
  echo "BUNDLES DELETED: secret found"; exit 1
fi
