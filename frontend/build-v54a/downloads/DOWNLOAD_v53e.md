# PMC Managers — Release v53e (frontend only)

## What changed since v53d

### 1. Vendor auction room — unmistakable Back button
The v53c back link was a small 11px text link that was easy to miss. It is
now a proper bordered button at the top of the room:
**"← Back to reverse auctions"** → returns to the vendor's auctions list.
(The public spectator page got its own "← Back to notices" in v53b.)

### 2. Awarded auction — where did it go? Now self-answering
Once an auction is awarded, the admin row's badge now reads
**"Awarded · in pipeline — Track in Bidding Ops →"** with a direct link to
`/admin/e/bidding`.

**Why it wasn't visible before:** the award creates a bid at
`status=emd_paid`, which lives in the **Bidding Ops** pipeline
(EMD paid → escrow acceptance → certifier → legal → accounting → awarded).
The **Awards** panel only lists bids that completed the whole chain
(`status=awarded`) — so a freshly-awarded auction bid correctly does NOT
appear there yet. Verified on prod: `BID-AUC-A03BF7` sits at `emd_paid`
under PMC-NOT-2026-0020 and is visible in Bidding Ops.

**Admin path after awarding an auction:**
Reverse auctions → Award winner → **Bidding Ops** (bid at "EMD paid —
Awaits Escrow") → escrow accepts → certifier → legal → accounting →
award documents auto-generate → vendor signs via DocuSign → bid flips to
`awarded` and appears in the **Awards** panel.

## Deploy

Frontend only: unzip `pmc-frontend-v53e-prod-build.zip` to S3 root,
CloudFront invalidate `/*`.
