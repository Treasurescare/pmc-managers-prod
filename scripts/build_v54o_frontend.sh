#!/bin/bash
# Build the v54o production frontend archive.
# CRITICAL: public/downloads/ is stashed during the build so CRA does not copy
# the (huge) release archives into build/. It is restored afterwards.
set -e
VER=v54s
cd /app/frontend

STASH=/tmp/pmc_dl_stash
rm -rf "$STASH"
if [ -d public/downloads ]; then mv public/downloads "$STASH"; fi

# Always restore downloads, even if the build fails.
restore() { if [ -d "$STASH" ]; then rm -rf public/downloads; mv "$STASH" public/downloads; fi; }
trap restore EXIT

yarn build

# downloads restored by trap only on EXIT; restore now so we can zip into it
rm -rf public/downloads
mv "$STASH" public/downloads
trap - EXIT

OUT="/app/frontend/public/downloads/pmc-frontend-${VER}-prod-build.zip"
rm -f "$OUT"
( cd build && zip -rq "$OUT" . )
echo "FRONTEND ZIP:"
ls -la "$OUT"
