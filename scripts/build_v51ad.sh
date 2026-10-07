#!/usr/bin/env bash
# PMC v51ad — Corrigenda full workflow (acknowledge + extend_days + field_amendments)
# plus Saved views (Filter Presets) across every Money & compliance panel.
set -eu
VER="v51ad"
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
# PMC Managers — Release v51ad (cumulative, supersedes v51ac)

## What's new in v51ad

### 1. Corrigenda workflow — full scope (minimum viable through field-level diff)
Admin → Procurement → Corrigenda now supports the complete amendment flow:
- numbered addendum (auto-increment Corrigendum 01, 02, …) with note and attachments
- **Extend deadline by N days** shortcut (admin fills a number of days; backend adds it to the parent notice's current submission deadline)
- **Field amendments** — admin adds any number of {field, before, after} rows so vendors see a versioned diff of exactly what changed in the tender fields (BOQ item, eligibility clause, budget, …)
- **Vendor acknowledgement**: every active corrigendum on a notice must be acknowledged by any vendor who has an active bid on that notice before their next bid action. Backend `GET /api/v1/corrigenda/outstanding` powers a vendor banner; `POST /api/v1/corrigenda/{id}/acknowledge` records consent on the audit log.
- Admin `GET /api/v1/notices/{ref}/corrigenda/{cid}/acknowledgements` lists who has acknowledged.

### 2. Filter Presets — Saved views on every Money & compliance panel
MoneyFilterBar now shows a **Saved views** dropdown + **Save view** / **Delete view** buttons. Each preset is scoped per panel (auctions, awards, billing, escrow, evaluation, l1, docusign) and per admin user (not shared). Save Expiring this week on auctions, Draft by me on awards, etc. — one click reloads your filter. Backed by `/api/v1/filter-presets` CRUD.

### 3. Carried forward from earlier releases
- Vendor edit for every non-approved registration (/registrations) and full vendor-profile editor at /admin/vendors/:ref/edit
- Expires-from/to fields hidden on panels without an expiry concept
- Money-pages crash fix, reverse auction Edit + Invite + Resend + readiness badge
- Notices filter URL memory + blank Contact Email coercion
- Section A–E bulk invite CSV + 409 structured detail

## Deploy
Upload pmc-frontend-v51ad-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51ad.zip to Elastic Beanstalk.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
