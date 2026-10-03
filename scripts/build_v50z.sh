#!/usr/bin/env bash
# PMC v50z — Vendor login links + DocuSign envelope scoping
# (a) Vendor invite / activation / approval emails now link to the unified
#     /login page instead of the legacy /vendor/login.
# (b) /api/v1/docusign/mine scoped to envelopes belonging to the CURRENT
#     vendor record (bid ownership by vendor_id, signer_email only for
#     envelopes created after this registration) — a re-registered vendor
#     reusing an email no longer inherits stale envelopes.
set -eu
VER="v50z"
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
# PMC Managers — Release v50z (cumulative v50m → v50z)

## Fixes in this build
- **Vendor password/activation emails now open the new login page**:
  the "Sign in" button in invite, activation and registration-approved
  emails pointed to the legacy `/vendor/login` (old split-screen page).
  All three now link to the unified `/login`.
- **DocuSign envelope scoping fixed**: `/api/v1/docusign/mine` matched
  envelopes purely by email, so a re-registered vendor reusing an email
  address inherited every envelope from the previous registration
  (the "new vendor sees 3 documents to sign" bug). Now scoped by the
  current vendor record's bid ownership, and signer_email matches only
  count for envelopes created after this registration.

## Deploy (backend REQUIRED — both fixes are backend-side)
1. `pmc-backend-v50z.zip` → Elastic Beanstalk
2. `pmc-frontend-v50z-prod-build.zip` → S3 + CloudFront `/*`
   (identical to v50y frontend; safe to skip if v50y already deployed)
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
