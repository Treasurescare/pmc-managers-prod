# PMC Managers — Release v52bj (10 Oct 2026)

Fixes the "stuck duplicate bid" dead-end and lays the plumbing for the
losing-bidder EMD refund workflow.

## Downloads
- Frontend: `/downloads/pmc-frontend-v52bj-prod-build.zip`
- Backend : `/downloads/pmc-backend-v52bj.zip` (EB root layout) — REQUIRED

## EMD lifecycle — how it works end-to-end (reference)

1. **Submission window** — notice carries `submission_deadline`. Backend
   rejects `POST /api/v1/bids` after that date with HTTP 400
   "Submission deadline has passed". Vendor can still *view* the notice;
   bid buttons on the Find Tenders list show a **Closed** badge instead of
   "Start bid" so they don't walk into a dead end.
2. **EMD payment** — a bid can be created without immediate EMD payment
   (status `emd_pending`). The vendor finishes payment via Stripe / PayPal /
   Kaspi. On success the bid flips to `emd_paid` and the escrow ledger
   row is auto-created. EMD paid *after* the submission deadline is
   impossible because no bid can be created after the deadline — once a
   bid exists before the deadline, finishing payment afterwards is still
   accepted (vendor already committed; the submission act is the bid, not
   the EMD clearance). If you want to force EMD-before-deadline we can add
   that as a flag on the notice; call it out and I'll gate it.
3. **Opening + evaluation** — committee reviews. One bid moves to
   `awarded`, the rest to `non_winner`. On award (v52bj):
   - every other active bid on the same notice is set to `non_winner`
     with `prior_status` captured for the audit log
   - any bid with `emd_paid_amount > 0` is flagged
     `emd_refund_state = "pending_release"` and a target release date
     (`emd_refund_due_at = today + EMD_LOSER_RELEASE_DAYS`, default **14**)
   - each losing bidder is emailed: "You did not win — your EMD of X will
     be returned by DATE"
   - accounts role is notified: "N EMD refunds due on NOTICE_REF"
4. **Release** — `POST /api/v1/bids/{id}/emd/release-to-vendor` (admin or
   accounting). Marks `emd_refund_state="released"`, stores the external
   reference (bank wire / refund id), emails the vendor, writes an audit
   log entry.
5. **Forfeit** — admin can withdraw-with-forfeit via the existing escrow
   dual-signatory `release/forfeit` endpoints when the vendor violated
   terms (misrepresentation, late withdrawal, etc).

## New endpoints (v52bj)
- `GET  /api/v1/bids/emd/refunds?status=pending_release|released|all`
  — list every bid flagged for refund (admin / accounting / auditor).
- `POST /api/v1/bids/{bid_id}/emd/release-to-vendor` — mark a loser's
  EMD released (body: `{reason, external_ref}`).

## Bug fix — stuck duplicate bid

The user reported: "I bid and paid EMD; it accepted; dashboard errored;
after v52bi the dashboard works but I can't bid again — HTTP 409 says a
bid already exists, I can't see it."

v52bi fixed the My Bids 500. v52bj additionally:
- Backend `POST /api/v1/bids` now returns a **structured 409 body** when a
  duplicate exists:
    `{code, message, existing_bid_id, existing_bid_ref, existing_status}`
- The vendor BidSubmit page catches that 409 and renders two one-click
  recovery buttons under the error banner: **Open my bids** (jump to the
  stuck bid) and **Withdraw stuck bid** (confirms, calls the existing
  `POST /{bid_id}/withdraw`, then clears the error so the vendor can
  submit a fresh bid).

## Verification (preview)
- `POST /api/v1/bids` with a notice the test vendor already bid on →
  HTTP 409 with the structured body (`existing_bid_id` populated).
- `GET /api/v1/bids/admin/emd-refunds` → HTTP 200 (empty list — no awards
  decided on this DB yet).
- `POST /api/v1/bids/bad-id/emd/release-to-vendor` → HTTP 400 (malformed id).

## Deploy order
1. **Backend v52bj** to EB first (new endpoints + non_winner flagging).
2. **Frontend v52bj** to S3 + CloudFront `/*` invalidation.

## Environment knob
- `EMD_LOSER_RELEASE_DAYS` (default 14) — days from the award date to
  the target EMD release date communicated to losing bidders.
