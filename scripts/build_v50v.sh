#!/usr/bin/env bash
# PMC v50v — Live Bid Workspace + Reviews + Signatures/KYC polish
# (a) VendorBidWorkspaceE: full live rewrite — real bid data, functional
#     Transfer/BG radios, working proof upload, Save/Submit actions
# (b) VendorReviewsE: fully React (no more href="#" Reply hijack); Reply
#     opens a dialog that drafts an email to tenders@pmcmanagers.com
# (c) VendorSignaturesE: heading now shows "N signed documents" when
#     nothing is pending; Download falls back to document.pdf when
#     combined-pdf fetch fails
# (d) VendorCompanyKycE: new "Bidding categories" tab backed by
#     /api/v1/vendor/categories/mine so approved categories appear even
#     if /auth/me didn't refresh; header counter also prefers live data
# (e) PmcLinkPatcher: vendor-reviews-e, vendor-bid-workspace-e,
#     vendor-mybids-e added to REACT_OWNED
set -eu
VER="v50v"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -3
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
# PMC Managers — Release v50v (cumulative v50m → v50v)

## What this fixes (vendor-reported Oct 3)
- **Bid Workspace completely static (a, b, c)** — Drop zone, Save-and-finish,
  Submit for escrow check and Bank-guarantee radio did nothing because
  the page was a static HTML mockup. Fully rewritten:
  - Real bid pulled from `/api/v1/bids/{id}`
  - Transfer-to-escrow ↔ Bank-guarantee radios toggle controlled state
    and swap the right-hand instructions.
  - Upload proof: presign + direct upload to our storage, with success/
    failure toasts.
  - "Save and finish later" takes you back to My bids (progress is saved
    by the usual bid autosave).
  - "Pay EMD now" opens the live Stripe EMD checkout; BG mode uploads
    the guarantee for the escrow team to verify.
  - EMD outstanding, deadline, envelopes, bid ref — all live from the bid.
- **Signatures heading (d)** — now reads "N signed documents" when every
  envelope is complete (previously said "0 documents to sign" which was
  confusing). Download has a fallback that tries the document.pdf
  endpoint when combined-pdf returns 502/412 (envelope archived or
  DocuSign document unavailable).
- **Company & KYC → Bidding categories (e)** — new tab fed by
  `/api/v1/vendor/categories/mine` with Approved / Pending / Recent
  decisions. The header counter now prefers this live source so an
  admin-approved category appears without a re-login.
- **Reviews Reply (f)** — `href="#"` Reply links no longer hijacked by
  the legacy PmcLinkPatcher; clicking Reply opens a reply dialog and
  drafts an email to tenders@pmcmanagers.com with the review context
  pre-filled.

## Deploy
- Frontend: `pmc-frontend-v50v-prod-build.zip` → S3 + CloudFront `/*`
- Backend: `pmc-backend-v50v.zip` → EB (identical to v50t/v50u)
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
