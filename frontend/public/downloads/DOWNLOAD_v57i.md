# PMC Managers — v57i (29 Oct 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v57i.zip`             → Elastic Beanstalk
- Frontend → `pmc-frontend-v57i-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v57i · Backend v57i"

## What's in v57i (since v57h)
1. Tender Builder: AI Fill All runs in the background with a progress bar; reviewers preview tenders before publishing.
2. RFQ and RFP starter templates; AI writes each type in its own style.
3. Fee types + Fee rules: timing, fixed/%/range, category and country scope; rules auto-fill from the fee type,
   one rule can cover several countries, adding a new country/category in a rule also adds it to the fee type.
4. Vendor pays before using the AI Tender Builder; receipts emailed and shown under EMD & payments (real totals).
5. First category free, extra categories paid (Registration fee rule); admin "Payment pending — send back" with link.
6. EMD collector per notice, tender document download fee (once per tender), tender hosting fee (buyer link),
   Data intel requests, refund alerts on Billing, daily 3-day payment reminder.
7. Vendor Messages inbox with unread badge.

## Before / after deploy (AWS)
- Env vars on Elastic Beanstalk: keep EMERGENT_LLM_KEY, Stripe key, WEBHOOK_CRON_SECRET set.
- Daily reminder: create an EventBridge schedule (09:00 UTC) that POSTs to
  `/api/v1/cron/category-payment-reminders` with the cron secret header (same as your other cron jobs).
- No prices are charged until you add Fee rules in production (Masters → Fee rules).
