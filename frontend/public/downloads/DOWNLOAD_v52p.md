# PMC Managers — Release v52p

## Addendum (same bundle) — v52q corrigendum sync fix
- `backend/routers/corrigenda.py` — field amendments (budget, EMD amounts,
  deadlines, pre-bid meeting, etc.) now apply onto the parent notice when a
  corrigendum is published, and roll back correctly when withdrawn
  (latest active corrigendum wins per field; stashed base values restored).
- Notice view now always shows amended values, matching the corrigendum diff.
- Verified end-to-end on a test notice (publish → values changed on notice;
  withdraw → values restored).
- Existing corrigenda published before this fix did NOT sync. To fix a live
  tender (e.g. Biogas): withdraw the old corrigendum and re-publish it with
  the same edits.

## What's in this release

### 1. Vendor Submit-Bid lockout once bidding closes (P0)
- `frontend/src/apps/vendor-portal/BidSubmit.jsx`
- When the current time is outside the admin-configured submission window
  (`submission_start → submission_deadline`), the submit form is replaced by a
  **view-only "Bidding is closed"** state. The tender detail stays visible for
  reference. If an admin later extends the deadline and the current time is
  back inside the window, the submission form re-enables automatically on next
  load — no code change needed.
- Backend already rejects late submits (`routers/bids.py:create_bid` 400 on
  `deadline < now()`), so the frontend lockout is a UX-level reinforcement.

### 2. Admin "Resync pending payments" (P2 → done)
- `backend/routers/billing.py` — new admin endpoint
  `POST /api/v1/billing/resync-pending?limit=200`.
  * Polls Stripe for every `payment_transactions` row still in
    `pending`/`initiated` state.
  * Uses the same idempotent `_mark_paid` helper the webhook uses, so bids
    advance to `emd_paid` + escrow auto-ledger fires exactly once.
  * Writes an audit event `billing.resync_pending` with the summary.
- `frontend/src/apps/admin-console/BillingTransactionsPanel.jsx` — new green
  "**Resync pending**" button (admin confirmation prompt + inline report).
- Use this to clean up historical rows left behind while the production
  Stripe webhook secret was missing (unblocked once `STRIPE_WEBHOOK_SECRET`
  is set — see §5 below).

### 3. Tender Maker — categories chip picker + AI extraction visibility (P1)
- `frontend/src/apps/admin-console/tender/CategoryMultiPicker.jsx` — new chip
  component for the tender header's **Product Category**.
  * Loads live from the Categories master (`/api/v1/masters/categories/public`).
  * Multi-select with "primary" badge on the first chip (writes back to the
    existing `product_category` string, plus a new `product_categories` list).
  * Supports **free-text add** (press Enter or Add).
  * Each chip is removable; "★" promotes any chip to primary.
- `frontend/src/apps/admin-console/tender/TenderHeaderForm.jsx` — the plain
  text input is replaced by the chip picker.
- `frontend/src/apps/admin-console/tender/DprGenerateModal.jsx` — after an AI
  DPR analysis finishes, the **extracted categories are now surfaced as chips**
  in the preview card (or an amber hint when the AI couldn't extract one).
  The chips flow into the draft on Create and remain editable from the chip
  picker above.

### 4. Hover readability fixes — Masters/Clone, Escrow EMD/Sign, Bidding Ops (P1)
- `frontend/src/index.css` — Option E palette overrides were defeating
  Tailwind's `hover:text-white` because `.text-brand-navy` was pinned to
  `--e-ink !important`. Added matching-weight hover rules so
  `hover:text-white`, `hover:bg-brand-navy`, `hover:bg-brand-navy-deep`,
  `hover:bg-brand-navy-soft` take effect on dark-fill-on-hover buttons.
- Visible repair across:
  * Masters → Staff Master → row **Clone** button.
  * Masters → Escrow EMD → **Sign · release to vendor / contractor /
    forfeit** and the **Release** button.
  * Admin → Billing → **Refresh / Resync pending**.
  * Any other `hover:bg-brand-navy hover:text-white` outline-button
    anywhere in the Option E admin.

### 5. Production Stripe webhook — operational fix (no code change needed)
- `backend/routers/payments.py` already enforces `STRIPE_WEBHOOK_SECRET` and
  returns **503** when it is missing, so unverified webhook calls can't
  advance a bid to paid. Preview env already has the secret set.
- **Production remediation steps:**
  1. Stripe Dashboard → **Developers → Webhooks** → open the production
     endpoint (`https://<your-domain>/api/webhook/stripe`).
  2. Confirm these events are enabled:
     * `checkout.session.completed`
     * `checkout.session.async_payment_succeeded`
     * `checkout.session.async_payment_failed`
     * `checkout.session.expired`
     * `charge.refunded`
  3. Click **Reveal signing secret** → copy the `whsec_…` value.
  4. Set `STRIPE_WEBHOOK_SECRET` in the production backend environment and
     **redeploy** the backend.
  5. Stripe Dashboard → endpoint → **Recent deliveries** should now show
     `200 OK` instead of `503`.
  6. Open **Admin → Billing**, click **Resync pending** to reconcile the
     backlog that was stuck during the outage.

## Testing status
- Preview backend restart clean; new endpoint returns 401 for anon and the
  expected JSON summary for authenticated admin.
- Hover-text contrast visually verified on Staff Master (Clone row) and
  Escrow / EMD (Sign · release buttons).
- Bid lockout UI inspected by hitting a notice whose deadline has passed —
  form is replaced by the view-only closed screen with a working **View my
  bids** link.
