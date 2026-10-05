#!/usr/bin/env bash
# PMC v51v — hotfix over v51u: light-shell vendor pages (bid submit /
# payment result / sandbox checkout / verify) repainted dark by the global
# .bg-slate-50 remap — headings were invisible (dark-on-dark). Those pages
# are now pinned back to light slate-50. Frontend-only change.
set -eu
VER="v51v"
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
# PMC Managers — Release v51v (cumulative, supersedes v51o–v51u)

## Hotfix in this build

### Vendor "Submit a bid" / payment / sandbox / verify pages — dark-on-dark heading
The global theme remap `[data-ui="e"] .bg-slate-50 → deep green` (meant for
dark pages) also repainted the LIGHT bid-submit shell, so after v51r's text
restore the page heading rendered dark-on-dark and was invisible. These four
light pages (bid submit, payment result, sandbox checkout, vendor verify)
are now explicitly pinned back to light slate-50 with dark ink.

## Also included (v51o–v51u)
- Company & KYC Cancel crash fix (scrim scrub guard)
- Admin Registrations inline detail on mobile
- Vendor Change Password mobile overflow fix
- Admin avatar dropdown via React Portal + icon-only topbar buttons on mobile
- Company-name change: incorporation evidence upload required + help text
- Phone-change confirmation gate (click-link to current email, admin 412)
- Bidding Ops mobile: tabs wrap, counts match rows, checkbox alignment
- Admin drawer iOS scroll fix, Vendors toolbar wrap, inline KPI detail,
  Masters chip grid, Start-bid bottom clearance + readable upload chips,
  5-icon mobile tab bar, Account rows wrap

## Deploy
- Frontend: `pmc-frontend-v51v-prod-build.zip` → S3, CloudFront invalidate `/*`.
- Backend: unchanged since v51t (`pmc-backend-v51v.zip` identical; if you
  already deployed v51t/v51u backend you can skip it).
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
