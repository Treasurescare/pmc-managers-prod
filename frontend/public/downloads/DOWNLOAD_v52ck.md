# PMC Managers — v52ck — Stripe webhook health indicator (12 Oct 2026)

SEC-001 follow-up. A missing or rotated `STRIPE_WEBHOOK_SECRET` used to be
invisible — webhooks would 503 and Stripe would retry for days. Now the
**Billing** page shows a health card at the top:

- 🔴 **Red**: "Signing secret missing — webhook returns 503…" (set the env var)
- 🟡 **Amber**: "Signing secret configured · awaiting first event"
- 🟢 **Green**: "Signing secret configured · last event <timestamp> UTC (<status>) · N event(s) in 24h"

### Backend (`billing.py`, `payments.py`)
- New admin endpoint `GET /api/v1/billing/webhook-health` →
  `{secret_configured, last_event_at, last_session_id, last_payment_status, events_24h}`.
  Auth: `current_admin` (401 for anonymous — verified).
- Both Stripe webhook handlers now record every **signature-verified** event
  into a `webhook_events` collection (`provider, session_id, payment_status,
  received_at`) — no schema migration needed.

### Frontend
- `api.js`: `feeBillingApi.webhookHealth()`.
- `BillingTransactionsPanel.jsx`: health card rendered above the transactions
  table; refreshes with the Refresh button. Testids: `webhook-health-card`,
  `webhook-health-missing`, `webhook-health-ok`.

Verified live on preview: card renders red "Signing secret missing" variant
(`STRIPE_WEBHOOK_SECRET` intentionally unset on preview); endpoint returns
401 unauthenticated.

## Deploy
- Backend: `pmc-backend-v52ck.zip` (includes v52cj — deploy this one).
- Frontend: `pmc-frontend-v52ck-prod-build.zip` (includes v52ci — deploy this one).

Files:
- `pmc-backend-v52ck.zip`
- `pmc-frontend-v52ck-prod-build.zip`
