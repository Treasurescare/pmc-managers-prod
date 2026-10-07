#!/usr/bin/env bash
# PMC v51aj — Hold/Resume clarity + post-payment envelope edits.
# Backend: PATCH /api/v1/bids/{id} now also allows emd_paid + escrow_accepted.
# Frontend: Bidding ops detail panel swaps Hold… → Resume bid (with hold
# reason) for on_hold bids; vendor workspace envEditable widened to match.
set -eu
VER="v51aj"
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
# PMC Managers — Release v51aj (frontend + backend)

## What this answers — the "hold changed from greyed to normal" scenario

**What you saw was correct behaviour plus one UI gap:**

1. Vendor bid on tender 48 without the commercial PDF — allowed at
   submission; the envelope shows "Not submitted" until they add it.
2. Vendor paid EMD → the bid does NOT jump straight to admin. It goes to
   **Step 2/6 — Escrow agent "Confirm receipt"** first (by design):
   Supplier pays → Escrow confirms → Admin tender desk → Certifier → Legal →
   Accounts → Committee.
3. You held the bid (commercial PDF missing). While the Hold request was in
   flight the button greys out; after the panel re-rendered, the Hold button
   looked active again because the detail panel never reflected the on_hold
   state. The hold DID apply — the vendor workspace showed ON_HOLD with the
   "on hold by PMC" callout.

**The UI gap is now fixed:** an on_hold bid's detail panel shows a prominent
**"On hold — Reason … Held by …"** note plus a **Resume bid** button (Hold… is
hidden). Resuming returns the bid to the exact step it was paused from
(`held_from_status`).

**And the follow-on gap:** after resuming, a bid at emd_paid /
escrow_accepted previously still blocked the vendor from adding the missing
commercial PDF. `PATCH /api/v1/bids/{id}` and the workspace "+ Add file"
buttons now allow envelope edits in every pre-evaluation state
(draft / submitted / emd_pending / emd_paid / escrow_accepted) while the
tender deadline is still open. on_hold remains locked by design.

## Verified (preview)
- API: PATCH succeeds on submitted bid (future deadline); emd_paid bid with a
  PASSED deadline correctly 400s ("envelopes are sealed"); held bid 400s;
  resume restores prior status.
- E2E: detail panel Hold → on_hold note + Resume → back to Hold cycle.

## Deploy
Frontend → S3 + CloudFront invalidate `/*`. Backend → Elastic Beanstalk
(pmc-backend-v51aj.zip). Supersedes/includes v51af–v51ai.
EOF
echo "built $VER"
ls -la "$DL"/pmc-{frontend,backend}-${VER}* "$DL/DOWNLOAD_${VER}.md"
