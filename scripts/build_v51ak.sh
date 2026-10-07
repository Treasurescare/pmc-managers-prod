#!/usr/bin/env bash
# PMC v51ak — Escrow "Record inbound EMD" bid picker.
# The Bid ref field was a free-text input so admins had to memorise refs and
# paid bids never appeared anywhere. Now a dropdown lists live bids (paid-EMD
# first) and auto-fills notice ref, vendor ref, amount and currency.
# Frontend-only release.
set -eu
VER="v51ak"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51ak (frontend only)

## What's fixed
**Escrow / EMD → "Record inbound EMD" — the Bid ref field was a free-text
box, so paid bids (e.g. PMC-BID-2026-00048) never appeared anywhere and
admins had to type refs from memory.**

- Bid ref is now a **dropdown of live bids** (withdrawn/rejected excluded),
  with **EMD-paid bids floated to the top** and annotated
  ("PMC-BID-2026-00048 — PMC-NOT-2026-0076 · PMC-SUP-000017 · EMD paid 100,000 INR").
- Picking a bid **auto-fills Notice ref, Vendor ref, Amount (EMD paid/due)
  and Currency** — every field stays editable afterwards.
- A **"— Manual entry —"** option reveals the old free-text box for
  exceptional/legacy refs.

## Deploy
Upload `pmc-frontend-v51ak-prod-build.zip` to S3, invalidate CloudFront `/*`.
No backend change in this release. Google site-verification meta tag carried
forward.
EOF
echo "built $VER"
ls -la "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/DOWNLOAD_${VER}.md"
