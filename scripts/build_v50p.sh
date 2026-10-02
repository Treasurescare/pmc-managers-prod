#!/usr/bin/env bash
# PMC v50p — PmcLinkPatcher guard for rewritten React vendor pages
# (fixes Signatures "Download" hijack). Includes everything from v50m→v50o.
set -eu
VER="v50p"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
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
# PMC Managers — Release v50p (cumulative: v50m → v50p)

## Fix in this build
- **Signatures "Download" hijack**: the global PmcLinkPatcher intercepted any
  button labelled "Download" (legacy label map → handleSigDoc) before the
  React onClick, surfacing "This document isn't linked to an envelope yet."
  The rewritten React vendor pages (Home / Find tenders / Signatures /
  Account / Company & KYC) are now exempt from the legacy label-click map —
  their buttons' own handlers always run.

## Carried from v50m–v50o
- Vendor portal rewritten with live APIs; sidebar is real React Router links
  (Home stays inside /vendor).
- Vendor Profile Edit with Admin approval; email changes also need the
  verification link on the new address; address dialog is structured
  (street/city/state/country/zip); company name editable; phone fields get
  a 30-country dropdown + per-country digit validation.
- Company & KYC page fully wired (tabs + licences CRUD with status).
- Vendor avatar dropdown: Change profile / photo / password / sign out.
- DocuSign `mine` returns `has_document`; Download hidden when no PDF.
- Find Tenders uses the shared admin pager (Show 10/20/30/All).
- SEC-001 fail-fast seed credentials; SEC-003 DocuSign HMAC fail-closed
  in production.
- Admin: Masters → Profile changes tab; Reverse auctions page;
  Stakeholder reports page; L1 dropdown shows all notices; escrow
  joint-account validation; AI-bid-anomaly dropdown contrast.

## Deploy
- Backend: `pmc-backend-v50p.zip` → EB.
- Frontend: `pmc-frontend-v50p-prod-build.zip` → S3 + CF invalidate.
- No new env vars required.
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
