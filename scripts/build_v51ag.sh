#!/usr/bin/env bash
# PMC v51ag — Vendor requests, Profile changes, BOQ, Work packages, Bidding
# ops, Escrow filters & governance UX fixes. Frontend-only release.
set -eu
VER="v51ag"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51ag (frontend only)

## What's fixed
1. **Vendor requests** (`/admin/e/vendor-requests`) — added search bar + requested-date range filter.
2. **Profile changes** (`/admin/e/profile-changes`) — added search bar + field dropdown + requested-date range filter.
3. **BOQ & Contracts** (`/admin/e/boq`) — single filter bar now searches template/contract fields + status + created-date range; identical fields on both tabs.
4. **Work packages Kanban** — switched from a 6-column flex grid (which produced cramped, broken titles) to a horizontal-scroll row with fixed 280 px cards so every title and metadata line is readable.
5. **Work packages publish view** — `View` modal now lists `attached_documents` with inline **View** and **Download** links per document.
6. **Bidding ops** — tagged `.bo-r` rows with `data-row`, `data-status`, `data-created-at`, `data-creator` so the MoneyFilterBar's Created-from / Created-to and Status filters actually hide non-matching rows.
7. **Escrow / EMD** — tagged transaction rows with `data-row` + `data-status` + `data-created-at` + `data-tender-ref` so the Search tender field and Created-date filters work. Each pending transaction now also shows a per-row **"You are signed in as X · will sign as PMC/Escrow officer"** banner. If the signed-in admin is neither officer the Sign call is blocked client-side with a clear remediation message.
8. **MoneyFilterBar global rule** — every "Created from / to" and "Expires from / to" input pair now enforces that the end date cannot be earlier than the start date (HTML `min`/`max` plus a toast on invalid change).

## Deploy
Upload `pmc-frontend-v51ag-prod-build.zip` to S3, invalidate CloudFront `/*`.
No backend change in this release.
EOF
echo "built $VER"
ls -la "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/DOWNLOAD_${VER}.md"
