#!/usr/bin/env bash
# PMC v56m — wire up the public marketing site: hero search + country + Find
# tenders, Popular chips, clickable platform stats, programme category cards,
# Trust "Verify"/"Report a concern", Contact form, and all top-nav/footer links
# across every public page (Home, Tenders, Trust, Contact, About, Vision,
# For suppliers, For buyers, Privacy, Completed/Awards).
set -eu
VER="v56m"; ROOT="/app"; DL="$ROOT/frontend/public/downloads"; mkdir -p "$DL"
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
