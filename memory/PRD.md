# PMC Managers — PRD (reset: 16 Feb 2026)

> Oversized history relocated. This file now carries ONLY the live product
> requirements + current status. Changelog and backlog live in the sibling
> files.

## Product
PMC Managers is a React + FastAPI + MongoDB procurement/tender SaaS with
reverse auctions, bid governance, EMD escrow workflows, vendor/staff/
institution portals, AWS deployment bundles, and transactional notifications
(Stripe, Resend, DocuSign, Emergent crons).

## Current P0 — v54c FINAL all-in-one (17 Feb 2026)
v54c bundles = v54a (escrow EMD pack) + v54b (registration unblocked) +
v54c (signature whitelist + upload persistence). Deploy ONLY the v54c pair.

v54c root fixes on top of v54b:
- `REGISTRATION_UPDATE_FIELDS` whitelist (api.js) was missing
  `signature_name/title/date` and `directors` — the browser silently
  dropped the signature block on every save → Submit always 400'd with
  "Missing signature field: signature_name". Whitelist extended.
- `adminApi.registrationAdminUpdate` bypassed the whitelist → admin
  "Edit sections" 422'd on extras. Now routed through `_stripRegExtras`.
- `document_slots` deliberately excluded from save whitelist — upload
  state is owned exclusively by the slot endpoints; stale-tab PATCHes
  can no longer wipe uploaded files.
- Verified E2E against preview: create → upload → save → resume →
  view file 200 → submit 200.

## Current P0 — Escrow EMD operational pack (v54a, 16 Feb 2026)
Delivered in this release:
- Signatory-pool returns `{pmc_officers, institutions}` reliably; now also
  surfaces each approved institution's **primary contact** as a fallback
  signatory so the institution-officer dropdown is never empty for a
  correctly approved institution.
- Admin → Joint Escrow Accounts → Edit signers now includes an **Escrow
  institution** picker that rebinds the account to an approved master
  (fixes "institution signatory dropdown locked forever" when legacy
  free-text institution name doesn't match any master).
- Admin → EMD transactions ledger → **Send DocuSign envelope** per row.
  Builds a 2-signer PDF, emails both officers the DocuSign hosted link,
  mirrors status onto the transaction.
- Escrow institution dashboard transaction rows are now clickable and
  open a **Transaction Detail Modal** showing: both signatories with
  signature state, DocuSign envelope status + Open-in-DocuSign button,
  **payment entries ledger** (payment-in / release / refund / fees) with
  proof upload + dual-sign per entry, and the full audit trail.
- Payment entries sub-collection with per-entry dual-signature workflow.
- Resilient DocuSign fallbacks: auth/consent failures surface as 503;
  both admin-side and institution-side `docusign-url` degrade to
  `{mode: 'email_only'}` and the UI tells the signer to open the
  DocuSign email instead of showing a 502.
- `transactions/init` now enforces the same-email governance guard at
  init time, so broken legacy accounts can never accept inbound EMD.
- Legacy joint-account rows show "institution not set" instead of a
  blank "· ·" separator.

Testing status: backend pytest `test_v54a_escrow_payment_entries.py`
(15/15) + E2E review `test_v54a_e2e_review.py` (15/15, iteration_85:
signatory pool, account create/edit+rebind, ledger init + duplicate
guard, DocuSign graceful 503, magic-link issuance, institution-portal
dashboard + tx detail + payment-entry create/sign/void, 403 foreign-tx
authorisation). Verified live via curl: missing-officer 400 guard,
503 DocuSign fallback, cancel 200. Frontend smoke (Playwright): both
portals render without 500s. Production verification pending — user
must upload v54a bundles to EB + S3/CloudFront.

## Must-have invariants
- Escrow institution status `approved` is NOT enough — the institution
  must have `signatories[]` registered (or an opted-in primary contact)
  for admin dropdowns and dual-sign to work end-to-end.
- At least one active staff flagged `is_escrow_signatory=True` must exist
  for the PMC side of every joint account.
- EMD payments auto-create a ledger transaction via
  `routers.escrow.auto_init_from_emd_payment`. Zero-EMD bids skip the
  escrow-staff step but keep the audit trail.
- Both officers must sign the identical release action before Release
  fires. Same-email on both officer slots is rejected at create + patch.
- Payment entries also require dual-signature (admin PMC side + institution
  side) before they are considered posted.

## Known production operability gaps
- Production deployment bundles must be uploaded by the user — we cannot
  push directly to AWS from this environment. Latest bundle to upload is
  `pmc-backend-v54a.zip` + `pmc-frontend-v54a-prod-build.zip`.
- Institution portal signatory onboarding depends on the institution's
  primary-contact completing the "Invite a teammate as signatory" form.
  v54a backfills the primary contact as a signatory option so the
  institution is never un-pickable just because that form wasn't run.

## Live stack
- Backend: FastAPI (`/app/backend/server.py`) with motor/MongoDB, JWT +
  CSRF double-submit cookies. New escrow routers:
  `escrow`, `escrow_institutions`, `escrow_signatories`, `escrow_accounts`,
  `escrow_payment_entries` (v54a).
- Frontend: React/CRA. Escrow surfaces: `admin-console/escrow/*`,
  `escrow-portal/*`, admin institutions management under
  `admin-console-e/AdminEscrowInstitutionsE.jsx`.
- Integrations: Stripe (EMD payments + webhook), DocuSign (award + escrow
  envelopes), Resend (transactional emails), AWS EB/S3/CloudFront
  (manual deploys), Emergent crons (vendor digest, escrow jobs).

See `/app/memory/CHANGELOG.md` and `/app/memory/ROADMAP.md` for history
and backlog.
