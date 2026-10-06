#!/usr/bin/env bash
# PMC v51aa — three vendor-flow enhancements on top of v51z:
#  1. Bulk-invite CSV template that covers every Section A–E field, with the
#     invite-bulk parser coercing lists / booleans / numbers correctly.
#  2. 409 "already active" invite returns a structured detail with vendor_ref;
#     the admin UI turns that into an "Edit full profile" toast action.
#  3. New /admin/vendors/:ref/edit screen so admins can edit the ENTIRE
#     Sections A–E profile of any created-but-unpublished vendor (and active
#     ones too).
set -eu
VER="v51aa"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
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
# PMC Managers — Release v51aa (cumulative, supersedes v51z)

## What is new in v51aa

### 1. Bulk-invite CSV template with the complete Sections A–E field set
Admin → Vendors → Bulk invite now has two template helpers:
  * Download full Sections A–E template — pulls a CSV with ~45 columns
    (identity, contact, banking, business profile, declarations) and one
    pre-filled sample row. Served by GET /api/v1/vendors/invite-bulk/template.
  * Minimal 4-column sample — the old quick-start template.

The invite-bulk parser coerces every cell correctly:
  * lists like operating_regions use | or ; as separators,
  * decl_* columns accept true/false/yes/no/1/0,
  * numeric columns are typed to int / float.
Every imported field is stored on the vendor's profile sub-dict so the
vendor sees their draft pre-filled on first login.

### 2. Clearer "already active" invite error
Previously admins got a dead-end HTTP 409 "Vendor with this email already
active." Now the 409 returns the matching vendor_ref and company_name,
and the admin UI shows a toast with an "Edit full profile" action that
jumps straight to the vendor record. No more guessing which vendor it was.

### 3. Edit entire vendor profile from the admin console
Every vendor row now has an Edit full profile link that opens
/admin/vendors/{ref}/edit — the same Sections A–E stepper used for
creation, but pre-filled from the vendor record. Admins can save per
section or save-and-close. Works for pending-verify, inactive, and
active vendors; the email field is intentionally read-only (change by
re-inviting).

## Deploy
Upload pmc-frontend-v51aa-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51aa.zip to Elastic Beanstalk. No new secrets.

Hotfixes from the v51z line (Money crash, auction invites, notice
filters with URL memory, blank Contact Email 422) remain in this build.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
