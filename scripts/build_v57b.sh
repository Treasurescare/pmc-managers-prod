#!/usr/bin/env bash
# PMC v57b — Clean-slate hardening. Startup demo seeders (notices, KZ work
# packages, product catalog, tender-template masters) now run ONLY when
# SEED_DEMO_DATA=true, so a production restart on an empty DB no longer
# re-creates demo content. Public homepage is fully real-data driven with
# polished empty states (live board + "open this week" grid + audit panel).
set -eu
VER="v57b"; ROOT="/app"; DL="$ROOT/frontend/public/downloads"; mkdir -p "$DL"
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
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
rm -rf public/downloads; mv "$STASH" public/downloads; trap - EXIT
OUT="$DL/pmc-frontend-${VER}-prod-build.zip"; rm -f "$OUT"
( cd build && zip -rq "$OUT" . -x 'downloads/*' -x 'downloads' )
echo "FRONTEND ZIP:"; ls -lh "$OUT"; echo "ALL DONE ${VER}"
