# PMC Managers — Release v53h (frontend + backend)

## What changed since v53g

### "Track every step under My bids" — fixed the misleading link
Your report: the vendor won, clicked the My bids link from the auction
room, and saw only an old bid. Root cause was twofold:

1. **The auction you viewed was never awarded.** There are two auctions on
   PMC-NOT-2026-0020: "OT Auction Wave40 Test" (won by TEST_Dec — this is
   the one that was awarded, bid `BID-AUC-A03BF7`) and "Modular OT Reverse
   Round 1" (won by Managers PMC — `awarded_bid_id` empty, never awarded).
   Until the admin clicks **Award winner** on the Modular OT row, no bid
   exists, so My bids correctly shows nothing new. To complete it: Admin →
   Reverse auctions → "Modular OT Reverse Round 1" row → Award winner →
   the bid then appears in the winner's My bids and in Bidding Ops.

2. **The room copy implied the bid already existed.** The "What happens
   next" list always said "Track every step under My bids". Now:
   - Before award: "Once PMC confirms the award, the new bid will appear
     under My bids."
   - After award: "Your bid **BID-AUC-…** is now in the approval pipeline —
     track every step under My bids."
   The backend `state-mine` payload now exposes `awarded_bid_ref` to the
   winning vendor only (losers and spectators never see it).

### Backfill: winner email missing on pre-v53b closes
Auctions closed before v53b stored no `winner.vendor_email` (e.g. the
Wave40 bid has `vendor_email: null`). The award endpoint now backfills the
email from the participant record, so pipeline notifications for those
bids have a real address.

**E2E verified in preview:** seeded a pre-v53b-style closed auction
(winner without email) → Award → bid created with backfilled
`vendor_email` at `escrow_accepted` (zero-EMD auto-clear from v53g) →
winner's `state-mine` returns `awarded_bid_ref`. Test data cleaned.

## Deploy

1. **Backend** — `pmc-backend-v53h.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53h-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. Then award "Modular OT Reverse Round 1" to complete your vendor's flow.
