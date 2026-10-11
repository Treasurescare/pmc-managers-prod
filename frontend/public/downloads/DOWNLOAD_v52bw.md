# PMC Managers · Release v52bw

**Date:** 11 Oct 2026 · **Supersedes:** v52bv

## What's in v52bw

### 1. DocuSign vendor status sync — both gates removed
Previously the vendor stayed on **submitted / pending** after admin signed because of two gates:
1. A DocuSign Connect webhook had to fire **or** the polling job had to run.
2. The envelope row had to carry `bid_id`.

Fixes:
- `_apply_live_status` now resolves `bid_id` via `award_ref → awards.bid_id` and `bid_ref → bids._id` fallbacks before mirroring the status. Older envelopes that only stored `award_ref` or `bid_ref` now sync too.
- New endpoint `POST /api/v1/docusign/envelopes/{envelope_id}/refresh` lets the admin console force a status pull right after signing/dispatching — vendors see the new status without waiting for the 5-minute poll.

### 2. DocuSign resend — UNKNOWN_ENVELOPE_RECIPIENT handled gracefully
`routers/docusign.py :resend_envelope` now also detects `UNKNOWN_ENVELOPE_RECIPIENT` (400) and the matching message string, flagging the local row `status: "orphaned"` and returning **HTTP 410** with a friendly recipient-missing message — not a raw stack trace.

### 3. Edit Signers CSS overlap
The Admin → Escrow / EMD row now carries `min-w-0 break-all` on the signer cells so long emails wrap inside their column instead of overlapping the next one.

### 4. BOQ View scroll-into-view + Close
Clicking **View** on a BOQ template now smoothly scrolls the viewer into view (ref + `scrollIntoView`), and the viewer has a **Close** button so admins don't scroll past the list wondering if the click worked.

### 5. BOQ Contract — reveal after create
`ContractsTab.createContract` now awaits the create response, shows the generated `contract_ref` in the toast (`"Contract created · PMC-CON-2026-NNNN"`), awaits the reload, and scrolls the new row into view. Admins no longer wonder where the contract went.

### 6. Tender Builder search results promoted
A second **"Matching drafts"** panel (`data-testid="tb-search-results-main"`) is now rendered at the top of the main content area whenever a search/filter is active, so admins see the results without scrolling past Kind + Master Library.

## Deployment
- Backend EB: upload `pmc-backend-v52bw.zip`.
- Frontend S3 + CloudFront: unzip `pmc-frontend-v52bw-prod-build.zip`, sync, invalidate `/*`.

## Verify after deploy
1. DocuSign admin → sign/dispatch any envelope → the admin UI calls `/refresh` → vendor /vendor/mybids and /vendor/signatures reflect the new status without a manual refresh.
2. DocuSign admin → Resend on an older-sandbox envelope → friendly "Use Reassign" message, no stack trace.
3. Admin → Escrow / EMD → each row's PMC / Escrow officer emails wrap inside their column.
4. Admin → BOQ → click View → viewer scrolls into view and shows a Close button.
5. Admin → BOQ → Contracts → create a contract → toast shows the generated ref, new row visible in the list.
6. Admin → Tender builder → search for anything → results banner appears at the top of the main pane.
