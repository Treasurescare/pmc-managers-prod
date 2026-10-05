#!/usr/bin/env bash
# PMC v51p — hotfix over v51o: admin Vendors page giant buttons on iPhone
#
# Root cause: mobile-fix.css had
#   [data-testid^="vendor-"] { padding-bottom: 88px !important; }
# intended to clear the fixed bottom tab bar on VENDOR PORTAL page roots.
# The attribute-prefix selector also matched every admin Vendors-panel
# control (vendor-search, vendor-invite-toggle, vendor-bulk-invite-open,
# vendor-status-filter-*, …), inflating each button by 88px on phones
# (measured: padding-bottom 88px, buttons 120–145px tall on iPhone).
# Fix: scope the rule to [data-pmc-e-page^="vendor-"] page roots only
# (+ the standalone verify-email-change page). Verified: admin Vendors
# buttons back to 26–62px, vendor portal pages keep the 88px clearance.
set -eu
VER="v51p"
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
# PMC Managers — Release v51p (hotfix over v51o)

## Fix in this build

**Admin → Vendors page on iPhone (giant stretched buttons).**
v51o fixed the toolbar wrapping, but the buttons/search/status filters were
still rendered 120–145px tall. Root cause: a mobile rule meant to add 88px
bottom clearance on vendor-portal pages used the selector
`[data-testid^="vendor-"]`, which also matched every control inside the
admin Vendors panel (`vendor-search`, `vendor-invite-toggle`,
`vendor-bulk-invite-open`, `vendor-status-filter-*`…). Each of those got
88px of forced bottom padding.

The rule is now scoped to actual page roots (`[data-pmc-e-page^="vendor-"]`)
only, so:
- admin Vendors controls are back to normal height (26–62px measured),
- vendor-portal pages still keep the 88px bottom clearance so the fixed
  bottom tab bar never covers content.

Includes everything from v51o (Bidding Ops tabs/counts, row-card layout,
drawer scroll to Masters, toolbar wrap).

## Deploy
- Frontend: `pmc-frontend-v51p-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. **This supersedes v51o** — skip v51o if not deployed yet.
- Backend: unchanged since v51n (`pmc-backend-v51p.zip` identical, included
  for convenience).
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
