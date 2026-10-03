#!/usr/bin/env bash
# PMC v50y — Masters: Legal Entity Types + Registration doc view/download
# (a) New Masters tab "Legal entity types" (CRUD) — admin edits the list,
#     Section A dropdown fetches from the public endpoint.
# (b) & (c) Section A, B, C uploads now use a dedicated token-authed
#     endpoint /api/v1/registrations/{id}/documents/{slot}/file — the old
#     /uploads/files URL required a signed-in session so vendors mid-
#     registration couldn't view their own uploads.
# (c) Section D "Business categories" is now a real multi-select from the
#     Categories master (UNSPSC-backed) — no more free-text.
# (d) Admin RegDocCard uses the new /admin-file variant so reviewers can
#     view/download all registration documents before approving.
set -eu
VER="v50y"
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
# PMC Managers — Release v50y (cumulative v50m → v50y)

## Fixes in this build
- **Masters → Legal entity types (new tab)**: full CRUD for the Legal
  entity type dropdown. Pre-seeded with LLC / JSC / Sole Proprietorship /
  Partnership / Branch / Other. Supports EN/RU/KZ names + country scope.
- **Section A dropdown now reads from the master**: vendor registration
  Section A pulls `/api/v1/masters/legal-entity-types/public`; falls
  back to the hard-coded list only if the API is unreachable.
- **Section A/B/C View & Download now work**: added
  `GET /api/v1/registrations/{id}/documents/{slot}/file?token=xxx` with
  magic-token auth. The old `/uploads/files/{key}` route required a
  signed-in session, so vendors mid-registration always hit 401 and
  View/Download appeared broken.
- **Section D "Business verticals" → multi-select from UNSPSC Categories
  master**: searchable list fed by `/api/v1/masters/categories/public`,
  chips for selected items, UNSPSC codes visible. Replaces the earlier
  free-text comma-separated input.
- **Admin: view/download registration documents before approving**:
  `RegDocCard` now hits a new `/admin-file` variant that fetches by
  registration id + slot — no more key-path CDN quirks.

## Deploy
- Backend: `pmc-backend-v50y.zip` → EB (new /legal-entity-types router +
  registration doc endpoints; backend MUST be deployed for this release)
- Frontend: `pmc-frontend-v50y-prod-build.zip` → S3 + CloudFront `/*`
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
