#!/usr/bin/env bash
# PMC v51ai — Vendor workspace: envelope file upload/remove after submission
# (backend PATCH /api/v1/bids/{id}) + on-hold callout + clickable stepper.
# Backend + frontend release.
set -eu
VER="v51ai"
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
# PMC Managers — Release v51ai (frontend + backend)

## What's fixed — "Unable to proceed" on the vendor bid workspace

The production screenshot (PMC-BID-2026-00026) had THREE separate blockers,
all addressed:

1. **Bid is ON HOLD** — an admin paused it in Bidding Ops. The workspace now
   shows a prominent amber "This bid is on hold by PMC" callout telling the
   vendor exactly why nothing can change and who to contact. (Admin action
   required: Bidding ops → ⋯ → Resume.)

2. **Envelopes showed "No files sealed yet" with no way back** — steps 2/3 in
   the stepper were display-only and there was NO post-submission upload UI
   anywhere. Now:
   - Steps 2 and 3 in the stepper are clickable and scroll to the envelope panel.
   - Each envelope gets a "+ Add technical file" / "+ Add commercial file"
     upload button while the bid is editable (draft / submitted / emd_pending,
     before the deadline).
   - Every uploaded file lists with View (in-page preview), Download and
     Remove actions.
   - Backend: new `PATCH /api/v1/bids/{bid_id}` (vendor-owner scoped, status +
     deadline gated, audit-logged as `bid.documents_update`).

3. **EMD panel confusion on settled/$0 bids** — already fixed in v51ah (the
   $0-EMD compact card + "Not required" checklist). This screenshot was the
   old build; deploying v51ah+v51ai together resolves it.

## Verified (preview)
- API: PATCH adds and removes documents on a submitted bid (status preserved).
- E2E: workspace renders Add/Remove buttons on an editable bid; on-hold bids
  show the callout and no edit controls.

## Deploy
Frontend → S3 + CloudFront invalidate `/*`. Backend → Elastic Beanstalk
(pmc-backend-v51ai.zip). Google site-verification meta tag carried forward.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
