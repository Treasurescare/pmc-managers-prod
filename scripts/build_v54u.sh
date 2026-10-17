#!/usr/bin/env bash
# PMC v54u — Safari staff-login fix (first-party SameSite=Lax cookies).
set -eu
VER="v54u"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"

# ---------- Backend EB zip (contents of /app/backend at zip root) ----------
cd "$ROOT/backend"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" . \
    -x '__pycache__/*' -x '**/__pycache__/*' \
    -x '*.pyc' -x '**/*.pyc' \
    -x '.env' -x 'venv/*' \
    -x '.pytest_cache/*' -x '.ruff_cache/*' \
    -x 'keys/*' -x 'tests/*'
echo "BACKEND ZIP built:"
ls -lh "$DL/pmc-backend-${VER}.zip"

# ---------- Frontend prod build (downloads stashed so CRA skips them) ------
cd "$ROOT/frontend"
STASH=/tmp/pmc_dl_stash_v54u
rm -rf "$STASH"
if [ -d public/downloads ]; then mv public/downloads "$STASH"; fi
restore() { if [ -d "$STASH" ]; then rm -rf public/downloads; mv "$STASH" public/downloads; fi; }
trap restore EXIT

REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true

rm -rf public/downloads
mv "$STASH" public/downloads
trap - EXIT

OUT="$DL/pmc-frontend-${VER}-prod-build.zip"
rm -f "$OUT"
( cd build && zip -rq "$OUT" . -x 'downloads/*' -x 'downloads' )
echo "FRONTEND ZIP built:"
ls -lh "$OUT"
echo "ALL DONE v54u"
