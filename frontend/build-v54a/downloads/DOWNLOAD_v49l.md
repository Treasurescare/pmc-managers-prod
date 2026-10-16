# PMC Managers Limited — Release v49l

## What's new in v49l

### 1 · EMD Statement PDF endpoint
`GET /api/v1/payments/emd/statement.pdf` (auth: vendor cookie).
Reads every `payment_transactions` row where `purpose=emd` for the current
vendor, joins to the bid for `bid_ref`/`notice_ref`, and renders an A4
WeasyPrint statement with:
- Header: vendor name + ref, generation timestamp.
- 3 KPI blocks: Total paid, Refunded, Row count.
- Table: date, bid ref, notice ref, amount + currency, status pill,
  reference ID.
- Green "chained to the audit ledger" footer.
Streamed with `Content-Disposition: attachment; filename="PMC-EMD-
Statement-<vendor_ref>-<yyyymmdd>.pdf"`. Verified: **HTTP 200,
application/pdf, 21,200 bytes**, starts with `%PDF-`.

`handleStatementPdf` in `PmcLinkPatcher` now fetches with
`credentials: include`, blob-downloads the file, and toasts on error
(no more "on its way to your inbox" placeholder).

### 2 · Real per-session revocation
- Added `token_generation` (int) on the vendor document.
- JWT payload carries the `gen` claim.
- `current_vendor` rejects any token whose `gen < vendor.token_generation`.
- `POST /api/v1/vendor/auth/sessions/revoke-others` (`require_csrf`)
  `$inc`'s the generation, mints a fresh JWT + CSRF for the CURRENT
  device, kills every other one on next request.
- `POST /api/v1/vendor/auth/change-password` now bumps the gen too so
  a password change kicks other devices.
- Patcher: `Sign out everywhere else` calls the new endpoint. Per-row
  Sign-out on the "Where you're signed in" table also hits the endpoint,
  fades the row and toasts what happened. The header Sign out button
  still just clears the current cookie.

Verified live: old cookie post-revoke → **HTTP 401 "Session revoked"**.

### 3 · Vendor route guard
- New `RequireVendor.jsx` component.
- Wraps `/vendor`, `/vendor/mybids`, `/vendor/tenders`, `/vendor/emd`,
  `/vendor/signatures`, `/vendor/alerts`, `/vendor/reviews`,
  `/vendor/company`, `/vendor/account`, `/vendor/workspace/:bidId`,
  `/vendor/change-password`, `/vendor/bid/new/:noticeRef`,
  `/vendor/bids/:bidId/pay`.
- Calls `vendorApi.me()` on mount. On 401 it `<Navigate>`s to
  `/login?next=<original path>`. In flight it shows a small "Signing you
  in…" placeholder so the static mockup never flashes.

Verified live: guest visit to `/vendor` lands at
`/login?next=%2Fvendor`; the Option-E sign-in form is visible.

## Everything else unchanged from v49k
- Negative-amount server-side guard.
- Vendor `.pmc-who` menu with Account / Photo / Sign out.
- Delegation-based `PmcLinkPatcher`, in-app change-password modal.

## Bundles
- **Frontend:** `pmc-frontend-v49l-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49l.zip` (419 KB — includes the new
  statement endpoint + session revocation, **redeploy this**)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- Backend: upload to Elastic Beanstalk.
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49k` if needed.
