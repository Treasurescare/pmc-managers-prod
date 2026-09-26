# v47b — Admin "Send EMD link" + vendor transition emails

## Was it in the previous build? — No. Now it is.

Before v47b:
- Transition emails went only to **staff** (next role in pipeline). The bidder got nothing.
- EMD payment was only reachable from the vendor dashboard — no admin-triggered email link.

## What's new

### 1 · "Send EMD link" button on the admin bids table
- New endpoint `POST /api/v1/bids/{bid_id}/emd/send-link` (roles: admin, reviewer).
- Guards: bid must have `emd_due_amount > 0`, status must be `emd_pending`/`submitted`, and EMD must not already be paid (400 otherwise).
- Sends a branded email to the bidder: subject `[PMC] EMD payment link — {bid_ref}`, with a **Pay EMD securely** CTA button.
- Audit-logged as `bid.emd_link_sent`.

### 2 · Deep-link payment page (vendor)
- New route `/vendor/bids/:bidId/pay` (`BidPayRedirect.jsx`): verifies the vendor session → creates the Stripe checkout → hard-redirects to Stripe → returns to `/vendor/payment/success`.
- If not signed in: bounces to `/vendor/login` with a `next` state, and VendorLogin honours it after sign-in.
- The in-dashboard **Pay EMD** button stays — both paths are live, so a vendor can never miss the step.

### 3 · Vendor (bidder) transition emails
`notify_bid_transition` now also emails the **bidder** on every vendor-visible stage:
| New status | Email to bidder |
|---|---|
| `emd_pending` | EMD payment pending — with Pay EMD button |
| `admin_flagged` | Passed PMC admin review |
| `certifier_cleared` | Certification cleared |
| `legal_cleared` | Legal cleared |
| `accounting_cleared` | Accounting cleared — with committee |
| `on_hold` | Placed on hold (includes hold reason) |
| `awarded` | Congratulations + open portal to sign PO |
| `rejected` | Not selected + EMD refund note |

Staff notifications to the next pipeline role are unchanged.

## Verified on preview
- `send-link` on an emd_pending bid → HTTP 200, email fired to vendor, link = `/vendor/bids/{id}/pay` ✅
- `send-link` on a zero-EMD bid → HTTP 400 "No EMD due on this bid" ✅
- Frontend prod build clean, zero preview-URL references ✅

## ⚠️ Production config check (one time)
Email links are built from the `FRONTEND_URL` env var. On EB it **must** be:
```
FRONTEND_URL=https://www.pmcmanagers.com
```
If it's unset, links will point to localhost and the CTA button won't work. Check EB → Configuration → Software → Environment properties. (The same var already powers vendor verify/invite links.)

## Deploy
- `pmc-backend-v47b.zip` → EB
- `pmc-frontend-v47b-prod-build.zip` → S3 sync + CloudFront invalidate (same commands as v47a)

## Carries forward
v47a (Approve / Hold / Resume), v46z (EMD fallback + View/Print), v46y (Rate-a-Peer gates) — all included in this one backend zip.
