#!/usr/bin/env bash
# PMC v50i — Notice Edit modal + Notice View modal + document delete.
set -eu
VER="v50i"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"

echo ">>> Zipping frontend"
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'

echo ">>> Zipping backend"
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' -x 'backend/**/*.pyc' \
    -x 'backend/.env' -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' -x 'backend/tests/*' -x 'backend/keys/*' 2>/dev/null || true

cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers Limited — Release v50i

## Notices · View + Edit + Document management

### Frontend
* Every row in Admin → Notices now has **View** and **Edit** buttons.
* **View modal** (`NoticeViewModal`) — complete read-only notice:
  * All fields (status, ref, type, category, country, budget, EMD,
    deadline, licences, matrix, template, contact, created/updated).
  * Full description.
  * **Every uploaded document** (primary + all attachments) listed with
    inline **View ↗**, **Download**, and **Delete** actions.
  * Confirmation dialog before any delete.
  * "Open public page ↗" button jumps to the bidder view.
* **Edit modal** (`NoticeEditModal`) — full editable form:
  * Same field set as Create (title, description, category dropdown,
    country dropdown, deadline, budget, EMD picker, approval matrix,
    tender template, publish checkbox).
  * Documents are managed via dedicated upload paths — a plain Save
    never drops existing files. Use View → Delete to remove docs.
  * Add-more inputs for appending primary or attachment uploads
    without replacing anything.

### Backend
* `PATCH /api/v1/notices/{notice_ref}` — update any editable field.
  Guards: primary_document / attachments / tenant_id never overwritten.
  Draft → Live transition still requires the publish permission.
  Writes a `notice.update` audit event with the list of changed fields.
* `DELETE /api/v1/notices/{notice_ref}/document?kind=primary` or
  `?kind=attachment&file_name=…` — detach a single document and log
  the event. (Underlying bytes stay in `uploads` for audit.)
* Startup seeder hardened against the EB rolling-deploy double-insert
  race that produced duplicate categories after the v50h deploy.

## Deploy
* Backend: upload `pmc-backend-v50i.zip` to Elastic Beanstalk.
* Frontend: `aws s3 sync --delete build/` → CloudFront invalidate `/*`.
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
echo ">>> Done: $VER"
