# PMC Managers — Release v53c (frontend only)

## What changed since v53b

### Vendor reverse-auction UX (your 3 requests from the screenshot review)

1. **Won/awarded badge on the auctions LIST** (`VendorAuctionsE.jsx`) — a
   trophy pill now shows on the row itself, before clicking View details:
   - "You won" (green) once the auction closes with you as leader.
   - "Contract awarded" once the admin has clicked Award winner.
   (Data comes from the v53b `/mine` outcome fields — needs the v53b
   backend deployed to light up.)
2. **Back button in the auction room** (`AuctionRoom.jsx`) —
   "← Back to reverse auctions" above the title.
3. **"What happens next" process flow in the room** once closed:
   - Winner sees the 4-step chain: award confirmation email → EMD/escrow/
     legal/accounting pipeline → PO/contract via DocuSign (Signatures tab)
     → track under My bids.
   - Non-winners see a "not the lowest this round, no action needed, EMD
     follows standard release" note.

### About the missing phone-change email — status
Prod backend version-marker probes show the current backend IS deployed
(v52w filters respond correctly), and the Resend config is verified working
(admin test-send returned ok:true). Prod audit shows only address-change
requests on record — no mobile request has ever reached the DB, so the
submission never completed client/server-side. Code path is verified
working in preview (mobile change → 2× Resend 200). If you click Submit
and see an error toast, send me the exact message — that's the failure
point. If you see "Request sent", the row will appear under Profile changes
and the email goes to managerspmc@gmail.com (check spam).

## Deploy

1. **Backend** — `pmc-backend-v53b.zip` → EB (this is the one that fixes
   the missing emails; v53c is frontend-only).
2. **Frontend** — `pmc-frontend-v53c-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.

Verified in preview: auctions list renders rows + lost-outcome note, room
shows back link, no console errors. (Trophy/won-states need a real won
auction — preview test data was cleaned after the v53b E2E.)
