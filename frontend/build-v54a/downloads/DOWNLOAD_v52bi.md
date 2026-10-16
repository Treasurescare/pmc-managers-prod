# PMC Managers — Release v52bi (10 Oct 2026)

HOTFIX — vendor "My bids" page showed `Something went wrong · HTTP 500`
and an empty list after bidding / paying EMD.

## Downloads
- Backend : `/downloads/pmc-backend-v52bi.zip` (EB root layout) — REQUIRED
- Frontend: unchanged — stay on v52bh.

## Root cause
During the v51bd draft-sync change, the `@router.get("/mine")` decorator
in `routers/bids.py` was accidentally consumed by an edit, orphaning
`list_my_bids`. With no `/mine` route registered, `GET /api/v1/bids/mine`
fell through to `GET /api/v1/bids/{bid_id}` with `bid_id="mine"` →
`ObjectId("mine")` raised `InvalidId` → unhandled 500 for every vendor.

## What changed
- `routers/bids.py`
    * Restored `@router.get("/mine")` above `list_my_bids` — the vendor's
      bid list endpoint works again.
    * `get_bid` now returns a clean `400 Malformed bid id` for non-ObjectId
      inputs instead of an unhandled 500 (defence-in-depth).

## Verification (preview)
- `GET /api/v1/bids/mine` as the test vendor → HTTP 200, 8 bids returned,
  newest `PMC-BID-2026-00022 · emd_pending` with notice title joined.
- `GET /api/v1/bids/zzz` → HTTP 400 (was 500).

## Deploy order
1. **Backend v52bi** to EB (this hotfix).
2. Frontend — no change; v52bh stays.
