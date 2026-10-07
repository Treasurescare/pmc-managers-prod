#!/usr/bin/env bash
# PMC v51af — Registrations "Edit sections" fix.
# Backend: admin_resume_link mints a magic_token for legacy registrations that
# never had one; new admin-only PATCH /api/v1/registrations/admin/{rid} saves
# edits on submitted/under_review registrations.
# Frontend: RegistrationResume renders the editable 5-section stepper when
# opened with ?from=admin and saves via the admin endpoint.
set -eu
VER="v51af"
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
# PMC Managers — Release v51af (frontend + backend)

## What's fixed
**Registrations → "Edit sections" did nothing / bounced to /register.**
Three gates were stacked against the admin:

1. **Missing magic tokens** — 11 legacy registrations (created before magic
   links existed) had no `magic_token`, so the resume URL was built with
   `token=` empty and the resume page silently redirected to `/register`.
   → `GET /api/v1/registrations/admin/{rid}/resume-link` now mints and
   persists a token on demand. Heals lazily per click; no migration needed.
2. **Read-only status screen** — the resume page rendered a static
   "Submitted — under review" card for any non-draft registration.
   → When opened with `?from=admin` it now renders the full editable
   5-section stepper for any non-approved / non-rejected registration.
3. **Save blocked for submitted rows** — the public token PATCH only allows
   `draft` / `needs_clarification`.
   → New admin-only `PATCH /api/v1/registrations/admin/{rid}` (admin or
   reviewer role, CSRF-protected, audit-logged) saves section edits on
   submitted / under_review registrations. Protected fields
   (status, vendor_ref, magic_token, ids, timestamps) are stripped
   server-side.

## Verified
- Preview E2E: Edit sections on a `submitted` registration opens the editable
  form, Save draft returns success, no error toasts.
- API: resume-link returns a real token; admin PATCH preserves status and
  updates fields.

## Deploy
Upload pmc-frontend-v51af-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51af.zip to Elastic Beanstalk.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
