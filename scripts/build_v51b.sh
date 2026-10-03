#!/usr/bin/env bash
# PMC v51b — Language switcher in footer + Tender country mode toggle +
# DocuSign reassign/archive tools
# (a) Footer bottom bar now carries the EN/RU/KZ language switcher on every
#     public page (top-right header already had it).
# (b) Tender Builder: when a country is selected, admin picks between
#     "This country only" (default) and "All templates".
# (c) DocuSign admin console: Reassign and Archive (soft-hide) actions on
#     every envelope. /mine excludes archived envelopes so vendors never
#     see orphans. Audit-ledgered.
set -eu
VER="v51b"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -3
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' -x 'backend/**/*.pyc' \
    -x 'backend/.env' -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' -x 'backend/tests/*' -x 'backend/keys/*' 2>/dev/null || true
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51b (cumulative v50m → v51b)

## Features in this build
- **Footer language switcher** (#123): EN/RU/KZ dropdown now sits at the
  bottom-right of every page, mirroring the one in the top header.
- **Tender Builder country mode** (#99): when a country is selected the
  admin picks between "This country only" (default) and "All templates".
- **DocuSign Reassign + Archive**: every envelope row gets ↪ Reassign
  (new signer email/name + audit reason) and ⌧ Archive / ⟲ Restore. A
  reassigned envelope resurfaces for the new vendor on their next
  Signatures page load. Archived envelopes are hidden from
  /api/v1/docusign/mine so vendors never see orphaned items.

## Deploy
- Backend: `pmc-backend-v51b.zip` → EB (new reassign/archive endpoints)
- Frontend: `pmc-frontend-v51b-prod-build.zip` → S3 + CloudFront `/*`
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
