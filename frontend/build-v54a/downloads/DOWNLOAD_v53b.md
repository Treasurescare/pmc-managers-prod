# PMC Managers — Release v53b (frontend + backend)

## What changed since v53a

### Reverse-auction award hand-off — closes the "auction closed, now what?" gap

**Before:** closing a reverse auction only flipped a status. No emails, no
bid record, no award pipeline — admins saw "CLOSED", the winning vendor
couldn't even tell they won, and the public spectator page was a dead-end.

**Now:**

1. **Close fan-out (automatic, on Close):**
   - **Admin** → in-app + email: winner company, winning price vs start,
     and the next step ("click Award winner").
   - **Winner** → "You won" email with the pipeline that follows (EMD →
     escrow → legal → accounting → PO for e-signature).
   - **Losers** → polite not-selected email. Winner identity stays masked
     to losers everywhere.
2. **"Award winner" button** (admin Reverse auctions list, on closed rows
   with a winner): creates a real bid — `BID-AUC-XXXXXX`, `emd_paid`,
   `source=reverse_auction`, winning price/currency, linked to the parent
   notice — and fires the standard pipeline notification to the escrow
   agent. **Per your governance decision, the full pipeline applies**:
   escrow acceptance → certifier → legal → accounting → award documents →
   DocuSign. Idempotent: a second click returns the same bid, and the row
   then shows an "Awarded · in pipeline" badge.
3. **Vendor Reverse auctions tab:** closed auctions now show the outcome —
   green "You won this auction at USD …" card (with a link to My bids once
   awarded) or a "not the lowest this round" note.
4. **Public spectator page:** "← Back to notices" link (was a dead-end).

**E2E verified in preview:** create → register → start → bid (90,000) →
close (winner captured) → award → bid `BID-AUC-…` in DB at `emd_paid` with
correct price/vendor → re-award idempotent (`already_awarded: true`) →
vendor `/mine` shows `outcome: "won"` + `awarded_bid_id`. Email fan-out
fires through Resend (same path verified 200 earlier). Test data cleaned.

## Deploy

1. **Backend** — upload `pmc-backend-v53b.zip` to Elastic Beanstalk.
2. **Frontend** — unzip `pmc-frontend-v53b-prod-build.zip` to S3 bucket
   root, CloudFront invalidate `/*`.
3. Close any completed auction → check the admin email → click
   **Award winner** → confirm the bid appears in Bidding Ops at
   `emd_paid` and the winner's vendor portal shows "You won".
