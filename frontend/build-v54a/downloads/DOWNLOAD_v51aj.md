# PMC Managers — Release v51aj (frontend + backend)

## What this answers — the "hold changed from greyed to normal" scenario

**What you saw was correct behaviour plus one UI gap:**

1. Vendor bid on tender 48 without the commercial PDF — allowed at
   submission; the envelope shows "Not submitted" until they add it.
2. Vendor paid EMD → the bid does NOT jump straight to admin. It goes to
   **Step 2/6 — Escrow agent "Confirm receipt"** first (by design):
   Supplier pays → Escrow confirms → Admin tender desk → Certifier → Legal →
   Accounts → Committee.
3. You held the bid (commercial PDF missing). While the Hold request was in
   flight the button greys out; after the panel re-rendered, the Hold button
   looked active again because the detail panel never reflected the on_hold
   state. The hold DID apply — the vendor workspace showed ON_HOLD with the
   "on hold by PMC" callout.

**The UI gap is now fixed:** an on_hold bid's detail panel shows a prominent
**"On hold — Reason … Held by …"** note plus a **Resume bid** button (Hold… is
hidden). Resuming returns the bid to the exact step it was paused from
(`held_from_status`).

**And the follow-on gap:** after resuming, a bid at emd_paid /
escrow_accepted previously still blocked the vendor from adding the missing
commercial PDF. `PATCH /api/v1/bids/{id}` and the workspace "+ Add file"
buttons now allow envelope edits in every pre-evaluation state
(draft / submitted / emd_pending / emd_paid / escrow_accepted) while the
tender deadline is still open. on_hold remains locked by design.

## Verified (preview)
- API: PATCH succeeds on submitted bid (future deadline); emd_paid bid with a
  PASSED deadline correctly 400s ("envelopes are sealed"); held bid 400s;
  resume restores prior status.
- E2E: detail panel Hold → on_hold note + Resume → back to Hold cycle.

## Deploy
Frontend → S3 + CloudFront invalidate `/*`. Backend → Elastic Beanstalk
(pmc-backend-v51aj.zip). Supersedes/includes v51af–v51ai.
