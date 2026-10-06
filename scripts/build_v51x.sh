#!/usr/bin/env bash
# PMC v51x — notice filter upgrades (created-by + date range) + money-pages
# clarification note. The L1-award crash on www.pmcmanagers.com in the user
# screenshot was an older bundle in production — v51u/v51v/v51w fixes the
# ErrorBoundary and are already in the preview. Nothing new to fix in the
# money pages; this release just bundles the new notice filters.
set -eu
VER="v51x"
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
cp scripts/backfill_notice_creator.py "$DL/backfill_notice_creator.py"
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51x (cumulative, supersedes v51o–v51w)

## New in this build

### Notices panel — richer filter bar
Added date-range and creator filters to the Admin → Notices filter bar.
You can now filter by any combination of:
- **Search by title or tender ref** (existing)
- **Created by (email)** — substring match on created_by_email
- **Created from / to** — inclusive date range on created_at
- **Status** — Published / Draft (awaiting approval) / Closing this week / Deadline past
- **Template-linked only** (existing)
- **Clear** resets all six.

### Reverse auction "Start" HTTP 400
This is a correct guardrail, not a bug: an auction can't start with
<2 registered participants. If you see "need at least 2 registered
participants, currently 0", invite the vendors first via the public
invitation link, let them register their interest, then click Start.

### Admin money-section panels crashing (your screenshot)
The screenshot URL was `www.pmcmanagers.com/admin/e/l1-award` — the
production build. The preview build (v51u onwards) no longer crashes
on any of the money pages (verified across l1-award, awards, escrow,
billing, evaluation). The crash will clear once you deploy v51u/v/w/x
to production.

## Also included (v51o–v51w)
- Notice creator attribution ("Posted by <email>")
- Light-shell vendor pages pinned light; Company & KYC Cancel crash fix
- Admin Registrations inline detail on mobile
- Vendor Change Password mobile overflow fix
- Admin avatar dropdown via React Portal + icon-only topbar on mobile
- Company-name change: evidence upload required
- Phone-change confirmation gate
- Bidding Ops mobile tabs/counts/checkbox; admin drawer iOS scroll fix
- Vendors toolbar + inline KPI; Masters chip grid
- Start-bid clearance + readable upload chips
- 5-icon mobile tab bar; Account rows wrap

## Deploy
- Frontend: `pmc-frontend-v51x-prod-build.zip` → S3, CloudFront invalidate `/*`
- Backend: unchanged since v51w — `pmc-backend-v51x.zip` identical; if you
  already deployed v51w backend you can skip it. If you haven't, deploy
  this zip and then run `backfill_notice_creator.py` once.
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
