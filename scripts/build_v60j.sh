#!/usr/bin/env bash
# PMC v60j — iPhone app is purchase-free (App Store 3.1.3(f)). Frontend only; backend stays v60i2.
set -eu
VER="v60j"; ROOT="/app"; DL="$ROOT/frontend/public/downloads"
rm -f "$DL"/pmc-frontend-v60h*.zip
cd "$ROOT/frontend"
STASH=/tmp/pmc_dl_stash_${VER}; rm -rf "$STASH"
if [ -d public/downloads ]; then mv public/downloads "$STASH"; fi
restore() { if [ -d "$STASH" ]; then rm -rf public/downloads; mv "$STASH" public/downloads; fi; }
trap restore EXIT
REACT_APP_BACKEND_URL="" REACT_APP_PUBLIC_SITE_URL="https://www.pmcmanagers.com" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
python3 "$ROOT/scripts/prerender.py" "$ROOT/frontend/build" "https://www.pmcmanagers.com"
rm -rf public/downloads; mv "$STASH" public/downloads; trap - EXIT
OUT="$DL/pmc-frontend-${VER}-prod-build.zip"; rm -f "$OUT"
( cd build && zip -rq "$OUT" . -x 'downloads/*' -x 'downloads' )
rm -rf /tmp/mz; mkdir -p /tmp/mz/downloads/manual
cp public/downloads/manual/PMC_v4_Master_Training_Manual.pdf public/downloads/manual/PMC_Master_Training_Manual_*.pdf public/downloads/manual/sections*.json /tmp/mz/downloads/manual/
( cd /tmp/mz && zip -rq "$OUT" downloads ); rm -rf /tmp/mz
echo "FRONTEND ZIP:"; ls -lh "$OUT"
if ! python3 "$ROOT/scripts/secret_scan.py" "$OUT"; then rm -f "$OUT"; echo "BUNDLE DELETED: secret found"; exit 1; fi
echo "ALL DONE ${VER}"
