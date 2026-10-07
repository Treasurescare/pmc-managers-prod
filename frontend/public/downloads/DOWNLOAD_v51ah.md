# PMC Managers — Release v51ah (frontend only)

## What's fixed

### 1. Bidding ops — layout order swapped
The pipeline step tiles (EMD → Escrow → Admin → Certifier → Legal → Accounts →
Awarded) now render FIRST; the search/created-date/status filter bar sits
directly below them.

### 2. Vendor bid workspace — EMD = 0 bids no longer dead-end
Previously a bid with `emd_due_amount = 0` still landed the vendor on the
"Pay the Earnest Money Deposit" panel (Step 4) with the stepper flagging EMD
as "Your action", and the seal checklist demanded "EMD confirmed by escrow"
forever. Now:
- Step 4 in the stepper shows ✓ **"Not required"**.
- The main panel collapses to a compact **"No EMD required for this tender"**
  card with only a Save-and-finish-later action (payment form, drop zone and
  beneficiary copy blocks are hidden).
- The "Before you can seal" checklist shows ✓ **"EMD not required for this tender"**.
- The "Your action" marker now points at the first genuinely incomplete step
  (Technical envelope → Commercial envelope → EMD → Review & seal).

### 3. Vendor can see their own envelope files (test-team clarification)
The "Sealed envelopes" panel previously read `bid.envelopes.*.files` — a field
the backend never populates — so every bid showed "No files sealed yet" even
when the vendor had uploaded documents at bid-creation time. The panel now
reads the real source (`bid.documents`, kind = technical / commercial) and
lists **every file with filename, size, an in-page View preview, and a
Download link**. The vendor can always inspect their own submissions; PMC
staff still cannot open them before the deadline.
- Envelope rows say "Submitted with bid" once files exist (seal timestamps
  still display when present).
- Checklist wording updated: "Technical/Commercial envelope submitted".

## Deploy
Upload `pmc-frontend-v51ah-prod-build.zip` to S3, invalidate CloudFront `/*`.
No backend change in this release. Google site-verification meta tag carried
forward.
