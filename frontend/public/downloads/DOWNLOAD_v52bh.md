# PMC Managers — Release v52bh (10 Oct 2026)

Fixes the "Something went wrong · HTTP 412 / [object Object]" deadlock seen
on production bid submission when a tender has a published corrigendum.

## Downloads
- Frontend: `/downloads/pmc-frontend-v52bh-prod-build.zip`
- Backend : `/downloads/pmc-backend-v52bh.zip` (EB root layout — REQUIRED,
  contains the corrigenda acknowledgement fix)

## Root cause
The backend blocks bid creation (HTTP 412) until every active corrigendum
on the notice is acknowledged, but the vendor-facing acknowledge endpoint
required an **active bid first** — so a first-time bidder could neither
acknowledge (no bid) nor create the bid (unacknowledged). Deadlock. On top
of that, the 412 response carried a structured detail object
(`{code, message, corrigenda: [...]}`) which the frontend rendered as
"[object Object]", hiding the real reason.

## What changed

### Backend (`routers/corrigenda.py`)
- `POST /api/v1/corrigenda/{cid}/acknowledge` no longer requires an active
  bid. Acknowledging a corrigendum before submitting is legitimate — the
  vendor is bidding on the amended terms.

### Frontend
- `lib/api.js` — `formatApiError` now renders structured details
  (`{message}`, `{code}`, `{corrigenda: [...]}`) as readable text instead
  of "[object Object]". The vendor now sees e.g.
  "1 active corrigendum on this notice need your acknowledgement before you
  can act. (Deadline clarified — no material change.)"
- `apps/vendor-portal/BidSubmit.jsx` — new **corrigenda acknowledgement
  panel**: every active corrigendum on the notice is listed with title,
  summary, new deadline (if any) and an "I acknowledge this corrigendum"
  button. Submit stays disabled with the hint
  "Acknowledge N corrigenda to submit" until every one is acknowledged;
  acknowledged items show "Acknowledged ✓".

## Verification (preview)
- Published a test corrigendum on an open notice, acknowledged it as a
  vendor **without** an active bid → `{ok:true}` (previously HTTP 400).
- Corrigendum withdrawn after the test; no residue.
- Submit button gating verified in code + build (`yarn build` clean).

## Deploy order
1. **Backend v52bh** to EB first (acknowledge-without-bid fix).
2. **Frontend v52bh** to S3 + CloudFront `/*` invalidation.
