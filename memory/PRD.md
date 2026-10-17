# PMC Managers — PRD (reset: 16 Feb 2026)

> Oversized history relocated. This file now carries ONLY the live product
> requirements + current status. Changelog and backlog live in the sibling
> files.

## Product
PMC Managers is a React + FastAPI + MongoDB procurement/tender SaaS with
reverse auctions, bid governance, EMD escrow workflows, vendor/staff/
institution portals, AWS deployment bundles, and transactional notifications
(Stripe, Resend, DocuSign, Emergent crons).

## Current P0 — v54h all-in-one (17 Feb 2026)
v54h = v54g + default-country-fix + upload polish:
- `/register` default country now blank with localStorage memory of last
  pick (no more "Kazakhstan by default").
- DocSlot captures the actual rid/tok used for the upload call and uses
  them as a fallback for the View/Download links so the action buttons
  render immediately on upload, not only when parent re-renders.
- `saveDraft` logs stray non-whitelisted fields to the browser console
  and drops them (defence in depth) so the opaque "Extra inputs are not
  permitted" 422 can't block a user — the exact offending field name is
  now diagnosable from console logs.
- Build stamp bumped to v54h.
Deploy the v54h pair and skip all earlier v54x bundles.

## Current P0 — v54g all-in-one (17 Feb 2026)
v54g = v54f + visible build stamp + prod URL fix:
- `.env` default `FRONTEND_URL` changed from the Emergent preview to
  `https://pmcmanagers.com` — root cause of "upload works, then file is
  gone when I open the emailed resume link" was that production emails
  were pointing to the preview environment, so clicking the link opened
  a different environment where the file never existed.
- Public `/api/v1/_version` endpoint + footer stamp showing frontend AND
  backend bundle versions, so we can confirm which bundle is live from
  any browser before testing.
Deploy the v54g pair and skip all earlier v54x bundles.

## Current P0 — v54f all-in-one (17 Feb 2026)
v54f = v54e + resume-link repair: the SEC-002 existing-draft path no longer
navigates to `token=undefined` (root cause of "upload view/download broken
+ email not populated" from the emailed resume link), invalid tokens get a
clear message, the resume page shows the vendor's email, and legacy rows
without magic tokens get one minted on first use. Deploy the v54f pair and
skip all earlier v54x bundles.

## Current P0 — v54e all-in-one (17 Feb 2026)
v54e = v54d + registration validation pack: country-format regex checks
(reg no / tax ID), mandatory non-future incorporation date, ISD phone
dropdowns, country-filtered bank datalist with SWIFT autofill, numeric-only
turnover, UNSPSC mousedown-click fix + comma custom chips, upload
view/download/persist verified via 13-check browser run.
Deploy the v54e pair and skip all earlier v54x bundles.

## Current P0 — v54d all-in-one (17 Feb 2026)
v54d = v54c (registration + escrow fixes) + searchable country combobox in
Section D Operating Regions (type-to-filter with matches on top, full list
below; verified live). Deploy the v54d pair and skip v54c.

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

## Status note — v54i (17 Feb 2026): registration upload "still broken" = stale client
- The long-running "uploads don't View/Download / vanish on save" report was
  reproduced against the user's EXACT production resume link in a clean
  browser and found to be ALREADY WORKING on the deployed build: Sections A,
  C and D upload, render VIEW/DOWNLOAD/DELETE, and persist through Save +
  reload; backend returns all `document_slots` and the file endpoint 200s.
- Root cause of the user still seeing it: their browser ran a cached older JS
  bundle (service worker / CloudFront edge). Fix shipped in v54i: version
  self-heal guard (`frontend/src/lib/versionGuard.js` + `index.js`) that
  reloads stale clients once when `/api/v1/_version` > baked build version,
  plus SW `skipWaiting()` and `CACHE_VERSION=pmc-shell-v54i`.
- Action for user: deploy v54i pair + CloudFront `/*` invalidation. After
  that, stuck clients auto-recover on next load.

