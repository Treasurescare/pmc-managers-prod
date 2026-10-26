#!/usr/bin/env bash
# PMC v57f — Auction engagement polish. (1) Public /auctions pages use the shared
# public site chrome (PublicChrome header + footer) instead of the generic TopBar.
# (2) Homepage live-auctions band hides when empty and shows a hero "N live now"
# ticker. (3) Public spectator room has a copy-watch-link button. (4) Closed
# auction cards show a recap panel (final price, saving %, SHA-256 ledger ref).
# (5) Duplicate-price bid notification is now fire-and-forget so the 409 is instant.
# Service-worker shell cache bumped to pmc-shell-v57f to push the new bundle.
set -eu
VER="v57f"; ROOT="/app"; DL="$ROOT/frontend/public/downloads"; mkdir -p "$DL"
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
