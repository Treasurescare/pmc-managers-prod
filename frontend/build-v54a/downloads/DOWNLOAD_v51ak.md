# PMC Managers — Release v51ak (frontend only)

## What's fixed
**Escrow / EMD → "Record inbound EMD" — the Bid ref field was a free-text
box, so paid bids (e.g. PMC-BID-2026-00048) never appeared anywhere and
admins had to type refs from memory.**

- Bid ref is now a **dropdown of live bids** (withdrawn/rejected excluded),
  with **EMD-paid bids floated to the top** and annotated
  ("PMC-BID-2026-00048 — PMC-NOT-2026-0076 · PMC-SUP-000017 · EMD paid 100,000 INR").
- Picking a bid **auto-fills Notice ref, Vendor ref, Amount (EMD paid/due)
  and Currency** — every field stays editable afterwards.
- A **"— Manual entry —"** option reveals the old free-text box for
  exceptional/legacy refs.

## Deploy
Upload `pmc-frontend-v51ak-prod-build.zip` to S3, invalidate CloudFront `/*`.
No backend change in this release. Google site-verification meta tag carried
forward.
