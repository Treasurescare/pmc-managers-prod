# PMC Managers — Release v50v (cumulative v50m → v50v)

## What this fixes (vendor-reported Oct 3)
- **Bid Workspace completely static (a, b, c)** — Drop zone, Save-and-finish,
  Submit for escrow check and Bank-guarantee radio did nothing because
  the page was a static HTML mockup. Fully rewritten:
  - Real bid pulled from `/api/v1/bids/{id}`
  - Transfer-to-escrow ↔ Bank-guarantee radios toggle controlled state
    and swap the right-hand instructions.
  - Upload proof: presign + direct upload to our storage, with success/
    failure toasts.
  - "Save and finish later" takes you back to My bids (progress is saved
    by the usual bid autosave).
  - "Pay EMD now" opens the live Stripe EMD checkout; BG mode uploads
    the guarantee for the escrow team to verify.
  - EMD outstanding, deadline, envelopes, bid ref — all live from the bid.
- **Signatures heading (d)** — now reads "N signed documents" when every
  envelope is complete (previously said "0 documents to sign" which was
  confusing). Download has a fallback that tries the document.pdf
  endpoint when combined-pdf returns 502/412 (envelope archived or
  DocuSign document unavailable).
- **Company & KYC → Bidding categories (e)** — new tab fed by
  `/api/v1/vendor/categories/mine` with Approved / Pending / Recent
  decisions. The header counter now prefers this live source so an
  admin-approved category appears without a re-login.
- **Reviews Reply (f)** — `href="#"` Reply links no longer hijacked by
  the legacy PmcLinkPatcher; clicking Reply opens a reply dialog and
  drafts an email to tenders@pmcmanagers.com with the review context
  pre-filled.

## Deploy
- Frontend: `pmc-frontend-v50v-prod-build.zip` → S3 + CloudFront `/*`
- Backend: `pmc-backend-v50v.zip` → EB (identical to v50t/v50u)
