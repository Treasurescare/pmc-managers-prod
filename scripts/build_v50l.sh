#!/usr/bin/env bash
# PMC v50l — Vendor category interest flow + admin approval queue.
set -eu
VER="v50l"
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
# PMC Managers — Release v50l

## Vendor Category Interest flow

### Supplier side (vendor login required)
- `/vendor/categories` — new page listing:
    - Approved categories (green pills) that drive tender matching.
    - Pending requests the admin hasn't decided yet.
    - Last 10 approve/reject decisions with admin notes.
- "Request additional category" picker fed from the Category master
  (105 categories, UNSPSC-coded). Searchable, radio-select, with an
  optional rationale textarea for the admin.

### Admin side
- `Admin → Masters → Vendor requests` — new tab listing all pending
  category requests. Each row shows vendor name/ref/email, requested
  category, rationale, timestamp. One-click **Approve** (optionally
  with notes) or **Reject** (notes required).
- Approving adds the category to `vendors.business_categories` via
  `$addToSet` so tender matching picks it up immediately.
- Both actions write a `vendor.category_approve|reject` audit event.

### Backend (routers/vendor_categories.py)
- `GET  /api/v1/vendor/categories/mine`           — vendor
- `POST /api/v1/vendor/categories/request`        — vendor
- `GET  /api/v1/vendors/category-requests`        — admin
- `POST /api/v1/vendors/category-requests/{id}/approve` — admin
- `POST /api/v1/vendors/category-requests/{id}/reject`  — admin
- Dedupe on (vendor_ref, category_code) across pending/approved.

## Deploy
- Backend: `pmc-backend-v50l.zip` → EB.
- Frontend: `pmc-frontend-v50l-prod-build.zip` → S3 + CF invalidate.
- SW banner from v50j auto-prompts Refresh after rollout.
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
