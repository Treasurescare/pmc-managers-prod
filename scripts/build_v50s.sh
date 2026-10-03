#!/usr/bin/env bash
# PMC v50s — Vendor UX hotfixes:
# (a) Supporting-document upload tiles visibility + re-upload after delete
# (b) My Bids rewritten to use live /bids/mine + live sidebar counts
# (c) Approved categories reflected in Company & KYC header
# (d) Back button on Categories page
set -eu
VER="v50s"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
yarn build 2>&1 | tail -3
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
# PMC Managers — Release v50s (cumulative: v50m → v50s)

## Fixes in this build (vendor UX hotfixes)

### (a) Supporting-document upload tiles — now clearly visible
On Submit-a-bid the three upload slots (Technical PDF / Commercial PDF /
Other doc) used ghost text on cream which was effectively invisible. The
tiles are now amber dashed boxes with a bold label and a yellow "+ Click
to upload" prompt. Hovering darkens the background for feedback.

### (b) Re-upload after delete — fixed
After uploading a document and then removing it, picking the SAME file
again did nothing (browsers suppress onChange when the picked path hasn't
changed). The upload handler now resets the <input type="file"> value on
both successful upload and on remove, so the same filename can be
reselected immediately.

### (c) My Bids — now live and complete
`/vendor/mybids` was a static mockup with only 4 hard-coded rows. It is
now a fully live React page that reads `GET /api/v1/bids/mine` (enriched
with notice title & deadline), tabs across Active / Drafts / Closed /
Withdrawn, computes KPIs (Active, Win rate, Value in play, EMD paid) and
renders every bid the vendor has submitted — including the one you just
placed.

### (d) Live sidebar counts across the supplier portal
VendorPortalChrome now fetches Find tenders / My bids / Signatures counts
on every page load, so the sidebar badges always match the lists below
them (previously the mockup showed a fixed "29/1/1").

### (e) Approved categories now reflect on Company & KYC
`GET /api/v1/vendor/auth/me` now returns `business_categories`, `country`
and `kyc_status` so the header on Company & KYC renders the category
chips the admin just approved (previously an approved category was
invisible until a full re-login).

### (f) Back button on Categories page
`/vendor/categories` now shows a `← Back` link at the top that returns
to the previous page (falls back to `/vendor/company`).

## Carried from v50m–v50r
- v50r: vendor Home routing on static pages, admin Vendor-requests
  crash fix, Market sidebar reorg, Help page back button.
- Vendor Portal rewritten (Home/Tenders/Signatures/Account/KYC on live
  APIs, structured address, phone validation, avatar dropdown)
- Vendor profile change approval queue (email verify + admin approve)
- SEC-001 fail-fast seeds, SEC-003 DocuSign HMAC fail-closed
- #6 Vendor activation verified end-to-end, #60 blank form regenerated
- DocuSign admin Archive-PDF repair tool
- EMD Master Editor UI (Masters → EMD rules + calculator)
- Reverse auctions page, Stakeholder reports page
- Admin Masters: Category Master, L1 all-notices, escrow validation,
  anomaly contrast

## Deploy
- Backend: `pmc-backend-v50s.zip` → EB
- Frontend: `pmc-frontend-v50s-prod-build.zip` → S3 + CF invalidate `/*`
- No new env vars required
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
