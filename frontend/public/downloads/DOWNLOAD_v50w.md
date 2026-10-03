# PMC Managers — Release v50w (cumulative v50m → v50w)

## Fix in this build
**Bid Workspace — EMD proof uploads now show a live document list.**
Previously an upload showed only a toast and vanished; vendors could not
see, open or remove what they had uploaded. Now every upload lands in an
"Uploaded (N)" panel under the drop zone:
- filename + human-readable size (KB/MB)
- View — opens the file inline in a new tab (gated, signed-in only)
- Delete — removes it from the list before you submit for escrow check
- Multiple documents accumulate (bank confirmation + BG + annexes all show)

Verified on preview: two PDFs uploaded → both rows listed, View returns
HTTP 200, Delete removes the row.

## Carried from v50v
- Bid Workspace fully live (real bid data, Transfer/BG radios, Save /
  Pay EMD now → Stripe)
- Paid bids show "Settled" + disabled button; pay-redirect shows a
  friendly "already settled" message
- Signatures heading context-aware + download fallback
- Company & KYC "Bidding categories" tab (approved/pending/recent)
- Reviews Reply dialog; PmcLinkPatcher React-owned bypass

## Deploy
- Frontend: `pmc-frontend-v50w-prod-build.zip` → S3 + CloudFront `/*`
- Backend: `pmc-backend-v50w.zip` → EB (identical to v50t)
