# PMC Managers Limited — Release v49m

## What's new in v49m — Pay EMD really opens Stripe now

`Pay EMD` in the Option E templates was a plain `href="#"` inside static
markup. v49h routed it to `/vendor/emd` (the deposits list); users saw
the list and thought the gateway was broken.

`PmcLinkPatcher.jsx` now owns the click with `handlePayEmd`:

1. Extract a `PMC-BID-YYYY-#####` ref from the row / card / `<tr>`
   containing the clicked element (via `.pmc-ref` or a regex over the
   row's text). If found → target that specific bid.
2. Otherwise (e.g. the top task banner "Pay EMD" button on the vendor
   home), call `GET /api/v1/bids/mine`, filter to `emd_pending`, and
   pick the first one so the user always lands on a live checkout.
3. If no pending bids → toast "No EMD payments are pending" and stay.
4. Call `POST /api/v1/payments/emd/checkout` via `paymentApi.checkout`,
   then `window.location.href = checkout_url` — a hard redirect so the
   Stripe Checkout page fully replaces the tab.
5. On 401 → `/login`; on API error → detail toast + drop on `/vendor/emd`.

### Verified live
- Signed in as `manualvendor@pmcmanagers.com` (3 `emd_pending` bids).
- Clicked "Pay EMD" from the vendor home task banner.
- Final URL:
  `https://checkout.stripe.com/c/pay/cs_test_a1gwr7mjjNeJ3kmZPsceiweDX59dyzjdC6nN9MTAQGkTdCPi5VNRUREpVy`
- Stripe Checkout renders the correct line item
  `EMD — bid PMC-BID-2026-00022 · KZT 1,000.00`, Sandbox badge,
  Apple Pay / Link / Card form.

### Also removed
- The catch-all `pay → /vendor/emd` static label mapping from
  `VENDOR_CTA_MATCHERS` so it can no longer short-circuit the real
  Stripe flow.

## Everything from v49l still applies
- EMD statement PDF endpoint (`GET /api/v1/payments/emd/statement.pdf`).
- Real per-session revocation with `token_generation`.
- `RequireVendor` route guard on every `/vendor/*` route.

## Bundles
- **Frontend:** `pmc-frontend-v49m-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49m.zip` (419 KB — no backend change vs
  v49l; re-packaged as a matched pair)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- Backend: skip if v49l is already deployed.
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49l` if needed.
