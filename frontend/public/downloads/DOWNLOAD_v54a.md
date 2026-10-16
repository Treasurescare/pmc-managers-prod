# PMC Managers v54a — Escrow EMD operational pack

Release target: 16 Feb 2026

## What this release fixes & adds

### 1. Escrow institution dashboard — real transaction detail, DocuSign & payment entries

Previously the **Pending signatures** / **All transactions** tables on the
institution portal were read-only lines with no way to open a row, no
visible signatories, no document to sign, and no place to record money
received or paid. All of that is live now.

Click any row in the institution dashboard and you get:

* Signature cards for **both** officers (PMC and your institution), with
  live signature status and timestamps.
* The **DocuSign envelope** panel: if PMC admin has issued an envelope for
  this transaction, you see its status + an **Open in DocuSign to sign**
  button that opens the hosted DocuSign signing session (DocuSign also
  sends you the hosted-signing email the moment admin dispatches it).
* **Payment entries** ledger — your institution records every real money
  movement on this bid with proof upload:
  * Payment-in (EMD received from bidder)
  * Payment-out (release to vendor / contractor)
  * Refund (back to bidder)
  * Fee / charge (debit)
* Each payment entry requires **dual signature** (PMC officer + Institution
  officer) before it is treated as posted. Approve / Reject buttons on
  every entry; proof files viewable inline.
* Full audit trail with timestamps, actor and action.

### 2. Admin console — Send DocuSign envelope on an escrow transaction

In Admin → Escrow → EMD transactions ledger, every open row now shows a
**Send DocuSign envelope** button. One click:

1. Builds a 2-signer envelope PDF summarising the escrow receipt &
   release mandate, with signature anchors for each officer.
2. Dispatches it to PMC officer **and** Institution officer. DocuSign emails
   both their hosted-signing link.
3. Mirrors the envelope status onto the transaction (shown as
   `DocuSign · sent` pill); institution portal picks it up and surfaces
   the **Open in DocuSign to sign** button automatically.

### 3. Admin Joint Escrow Accounts — rebind to approved institution

The **Edit signers** panel on each joint account now has a dedicated
**Escrow institution** picker. Pick any approved escrow institution master
and the Escrow-institution-officer dropdown repopulates with that
institution's registered signatories (plus its primary contact as a
fallback). This unblocks the "institution signatory dropdown is empty
forever" bug where a legacy free-text institution name did not match any
approved master.

The signatory pool API also now surfaces the institution's **primary
contact** as a fallback signatory option so correctly approved
institutions never show an empty officer list.

### 4. Backend bug fix — signatory_pool missing return

`GET /api/v1/escrow/signatory-pool` was previously falling through to the
duplicate-scan handler because the function had no `return` statement.
Fixed; it now returns `{pmc_officers: [...], institutions: [...]}` as
documented.

### 5. New backend router — `escrow_payment_entries`

Clean, test-friendly separation. Endpoints:

* `GET  /api/v1/escrow/transactions/{tid}/payment-entries` — admin list
* `POST /api/v1/escrow/payment-entries` — admin create
* `POST /api/v1/escrow/payment-entries/{peid}/sign` — admin sign
* `POST /api/v1/escrow/payment-entries/{peid}/void` — admin void
* `POST /api/v1/escrow/transactions/{tid}/docusign` — admin issue envelope
* `GET  /api/v1/escrow/transactions/{tid}/docusign-url?side=` — admin console view

Institution-portal mirrors (CSRF-protected, scoped to the current escrow
account):

* `GET  /api/v1/escrow-accounts/me/transactions/{tid}`
* `POST /api/v1/escrow-accounts/me/transactions/{tid}/payment-entries`
* `POST /api/v1/escrow-accounts/me/payment-entries/{peid}/sign`
* `GET  /api/v1/escrow-accounts/me/transactions/{tid}/docusign-url`

## What you still need to do once (per institution)

* **Register signatories inside each approved institution.** Status
  `approved` alone is not enough — the institution dashboard must list at
  least one signatory under *Invite a teammate as signatory*. The
  signatory then claims their password and shows up in the admin
  dropdowns.
* Keep at least one active staff flagged **Escrow signatory** in Masters →
  Staff — this is the PMC side of every joint account.

## Artifacts

* Backend: `pmc-backend-v54a.zip`
* Frontend: `pmc-frontend-v54a-prod-build.zip`

Deploy as usual (EB upload for backend, S3 upload + CloudFront
invalidation for frontend). No DB migrations required; new collections
(`escrow_payment_entries`, additional fields on `escrow_accounts` and
`escrow_transactions`) are created lazily.
