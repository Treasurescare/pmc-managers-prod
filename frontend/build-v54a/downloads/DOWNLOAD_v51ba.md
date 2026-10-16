# PMC Managers — Release v51ba (10 Oct 2026)

## Downloads
- Frontend (production build): `/downloads/pmc-frontend-v51ba-prod-build.zip`
- Backend (source archive):    `/downloads/pmc-backend-v51ba.zip`

## What changed

### Admin bid detail — readability
- Fixed cream-on-cream unreadable text inside the admin bid detail cards.
  CSS carve-out added for `[data-testid="admin-bid-page"]` so slate ink
  stays dark on the light cards. (`frontend/src/index.css`)

### Admin bid detail — Award Record panel
- New lifecycle panel appears for awarded bids with:
  - Award ref, PO no., awarded by / at
  - Tender ref, title, delivery country, published date, submission deadline
  - Bid submission, technical cleared, financial opened timestamps
  - Winning vendor + awarded price
  - Lifecycle sign-offs (Escrow, PMC admin, Certifier, Legal, Accounts, Committee)
  - Escrow dual-signature ledger entries with PMC & institution officer stamps
  - DocuSign envelope status + completion timestamps
  - Buttons: Print Award Letter · Download PDF · Print Contract · Download PDF
- `frontend/src/apps/admin-console/bidding/AdminBidDetailPage.jsx`

### Backend endpoints (admin-only)
- `GET /api/v1/awards/bid/{bid_id}/summary` — lifecycle + sign-off summary.
- `GET /api/v1/awards/bid/{bid_id}/award-letter.html` — printable HTML view.
- `GET /api/v1/awards/bid/{bid_id}/contract.html`     — printable HTML view.
- `GET /api/v1/awards/bid/{bid_id}/award-letter.pdf`  — PDF export (WeasyPrint).
- `GET /api/v1/awards/bid/{bid_id}/contract.pdf`      — PDF export (WeasyPrint).
- `backend/routers/awards.py`

## Verification (preview)
- Logged in as `adminsupport@pmcmanagers.com` and opened an awarded bid
  (`PMC-BID-2026-00005`). All values are now clearly readable.
- Award Record shows:
  - Escrow sign-off: `escrow@pmcmanagers.com` · 2026-08-02 06:10:19
  - PMC admin sign-off: `adminsupport@pmcmanagers.com` · 2026-08-03 03:41:10
  - Certifier / Legal / Accounts / Committee: pending
  - DocuSign envelopes list with completed / sent states.
- Print view renders a clean letter with the Close + Print toolbar.
- PDF download returns a 20 KB PDF (`PDF document, version 1.7`).

## Deploy notes
- No new secrets, no new migrations.
- Hot reload picks up backend changes automatically in the preview env.
- To ship: upload the prod frontend zip to the S3/CloudFront origin and the
  backend zip to Elastic Beanstalk (same procedure as prior v51a* releases).
- v51ba backend zip was repackaged (10 Oct, second build) with the required
  EB root structure — `Dockerfile`, `Dockerrun.aws.json`, `.platform/` at the
  archive root and code under `backend/` — matching the working v51ax layout.
  The first v51ba zip (backend folder contents at root) fails on EB with
  "Engine execution has encountered an error"; discard it.
