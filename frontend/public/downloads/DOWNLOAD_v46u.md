# v46u — Production bundles: dashboard drill-through, universal search/filters, KYC admin controls, bid-submit UX, SW crash fix

## What's new in v46u

### 1 · Reverse Auctions crash fix (P0)
- `LiveAuctionsPanel.jsx` used `publicApi.listNotices` without importing `publicApi` → "This panel hit an error". Fixed.

### 2 · Universal filters + search across admin console
- **Live Auctions** — status filter (All/Draft/Live/Closed) + search (`ra-search`).
- **Engagements** — search by product / buyer (`engagement-search`).
- **Billing** — status filter (All/Paid/Unpaid/Refunded) + search (`btp-search`).
- **Awards** — awarded-bid search (`awards-bid-search`).
- **DocuSign** — envelope filter **All / Sent / Waiting / Signed / Rejected / Voided** + search (`ds-search`).
- **Masters** — per-tab search on staff / companies / tenants / hierarchy.
- **Vendors / Registrations / Vendor Intel** — search added in previous pass (`vendor-search`, `reg-search`, `vintel-search`).
- **Procurement group** — Corrigenda (`corr-notice-search` + `corr-search`), Work Packages kanban (`pkg-search`), BOQ & Contracts (`boq-search`), Catalog (`catalog-search`). Notices and Tender Builder already had search.

### 3 · Dashboard drill-through
- Every KPI tile is clickable → jumps to its owning tab (Notices / Vendors / Bidding / Awards / Escrow / Billing / BOQ).
- Pipeline funnel stages + Top-priced-bids rows click through to the bid pipeline.

### 4 · Help improvements
- Help panel search is sticky at the top (no scrolling to search).
- New **Help pill** in the admin top bar on every tab — jumps to Help pre-filtered to the current tab.

### 5 · KYC admin controls
- New backend endpoint `POST /api/v1/kyc/manual` (admin / legal_counsel) — set vendor KYC to `verified` / `pending` / `rejected` with audit row.
- Vendors panel → select a vendor → "KYC verification" block: **Run KYC provider**, **Mark verified**, **Mark pending**, **Mark rejected** (with reason).

### 6 · Bid-submit UX hardening
- Deadline-passed notices show a persistent red banner and disable the submit button.
- API errors render inline under the form (no more silent failures).
- Partial document uploads are stripped from the payload (fixes 422 "Field required ×6").

### 7 · Service worker crash fix
- All fetch branches now always return a real `Response` (503/504 fallbacks). Cache version bumped to `pmc-shell-v46u` — browsers auto-pick the new SW within one page load.

---

## Deploy steps

### Backend (Elastic Beanstalk)
1. Upload **`pmc-backend-v46u.zip`** to the EB environment (contains `Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf` with the 200 MB body-size config, and the full `backend/` tree).
2. EB env properties must carry: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, Stripe keys, and (for push) `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` / `VAPID_CLAIM_EMAIL`.
3. Health check: `GET https://pmcmanagers.com/api/v1/push/config` → `{"public_key":"...","enabled":true}` once VAPID vars are set.

### Frontend (S3 + CloudFront)
1. Unzip **`pmc-frontend-v46u-prod-build.zip`** → `aws s3 sync <unzipped> s3://<bucket>` **without `--delete`** (protects `/downloads/`).
2. This build is **same-origin** — no backend URL is baked in; all API calls go to `/api/*` on the same domain.
3. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.
4. The new service worker (`pmc-shell-v46u`) self-updates within one page load; no manual cache-clear needed.

### Post-deploy smoke test
- Admin login → Dashboard → click a KPI tile (should navigate).
- Vendors → select a vendor → KYC block visible → Mark verified.
- Vendor login → Open tenders → bid on a future-deadline notice → Stripe EMD checkout opens in a new tab.
- Reverse Auctions tab renders without the error boundary.

---

## Downloads

- **[pmc-backend-v46u.zip](./pmc-backend-v46u.zip)** — EB Docker archive (kyc/manual endpoint + push router, 288 KB)
- **[pmc-frontend-v46u-prod-build.zip](./pmc-frontend-v46u-prod-build.zip)** — same-origin production build (2.3 MB, excludes `/downloads/` — sync those separately)
- **[DOWNLOAD_v46u.md](./DOWNLOAD_v46u.md)** — this file
