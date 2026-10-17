# PMC Managers — Changelog

## v54d — 17 Feb 2026 — Searchable country picker in Operating Regions
- Section D → Operating Regions → Country is now a searchable combobox:
  type letters to float matches (name or ISO code, starts-with first)
  under a MATCHES heading; the full 250-country list remains below an
  ALL COUNTRIES divider. Enter picks first match, Escape closes.
  Verified live via Playwright: "ind" → IN/ID/IO matched → selected.
- Backend identical to v54c; frontend rebuilt.
- Bundles: `pmc-backend-v54d.zip`, `pmc-frontend-v54d-prod-build.zip`.

## v54c — 17 Feb 2026 — FINAL all-in-one (registration + escrow)
- **ROOT FIX**: `REGISTRATION_UPDATE_FIELDS` whitelist in `api.js` was
  missing `signature_name/title/date` and `directors` — the browser
  silently dropped the signature block on every save, so Submit always
  400'd. Whitelist extended; verified save → resume → submit = 200.
- `adminApi.registrationAdminUpdate` now routes through `_stripRegExtras`
  (admin "Edit sections" screen was 422ing on `email`/consent extras).
- `document_slots` deliberately excluded from the save whitelist and
  stripped in `saveDraft` — slot state is owned by the upload/delete
  endpoints only, so a stale-tab save can no longer wipe uploaded files.
- Full E2E verified: create → upload → save (signature persists) →
  resume (slots intact) → view file 200 → submit 200.
- v54c bundles contain v54a + v54b + v54c. Deploy ONLY the v54c pair.

## v54b — 17 Feb 2026 — Public vendor registration unblocked
- **BUG FIX**: `/api/v1/meta/countries` now reads the full
  `masters_countries` master (250 rows) instead of the 30-row pilot
  config. Public Section A country dropdown is complete.
- **BUG FIX**: `RegistrationUpdateIn` whitelists `directors` and
  `document_slots` (new fields that were being blocked by `extra="forbid"`
  and 422ing every Save Draft). Signature block now persists so Submit
  no longer 400s with "Missing signature field: signature_name".
- `RegistrationResume.saveDraft` strips server-managed fields (email,
  consent flags, timestamps, magic_token, reviewer fields) before PATCH
  and now throws on failure so `submitFinal` halts instead of submitting
  an unsaved draft.
- Release bundles: `pmc-backend-v54b.zip`, `pmc-frontend-v54b-prod-build.zip`.

## v54a — 16 Feb 2026 — Escrow EMD operational pack
- **BUG FIX**: `GET /api/v1/escrow/signatory-pool` was falling through
  with no `return` statement; now reliably returns
  `{pmc_officers, institutions}`.
- Institution-officer dropdown resilience: signatory-pool injects the
  approved institution's `primary_contact_email` as a fallback signatory
  entry when `signatories[]` is empty.
- Admin → Joint Escrow Accounts → Edit now includes **Escrow institution**
  picker. Admin can rebind any account to any approved institution master;
  the escrow-officer dropdown repopulates immediately.
- `escrow_accounts` records now carry explicit `institution_id` alongside
  the display `institution` name (backward-compatible — unset on legacy
  rows, matching still falls back to name).
- NEW backend router `escrow_payment_entries.py`:
  - `/api/v1/escrow/transactions/{tid}/payment-entries` (admin list)
  - `/api/v1/escrow/payment-entries` (admin create)
  - `/api/v1/escrow/payment-entries/{peid}/sign` (admin dual-sign)
  - `/api/v1/escrow/payment-entries/{peid}/void` (admin void)
  - `/api/v1/escrow/transactions/{tid}/docusign` (admin issue envelope)
  - `/api/v1/escrow/transactions/{tid}/docusign-url` (admin console view)
- NEW institution-portal endpoints inside `escrow_accounts.py`:
  - `/api/v1/escrow-accounts/me/transactions/{tid}` (detail)
  - `/api/v1/escrow-accounts/me/transactions/{tid}/payment-entries` (create)
  - `/api/v1/escrow-accounts/me/payment-entries/{peid}/sign`
  - `/api/v1/escrow-accounts/me/transactions/{tid}/docusign-url`
  All scoped through the escrow_account_token cookie + CSRF, authorised
  via account signatories' emails matching the transaction's
  escrow_officer snapshot.
- NEW frontend components:
  - `escrow-portal/TransactionDetailModal.jsx` — clickable transaction
    detail with signatures, DocuSign panel, payment-entries CRUD, audit
    trail.
  - Admin `EscrowTransactionsSection.jsx` — **Send DocuSign envelope**
    per row.
  - Admin `EscrowAccountsSection.jsx` — Escrow-institution picker inside
    Edit signers.
- Backend tests: `tests/test_v54a_escrow_payment_entries.py` (15 cases,
  all green) + `tests/test_v54a_e2e_review.py` (15 cases, all green,
  iteration_85).
- Follow-up fixes after E2E review (iteration_85):
  - `transactions/init` enforces same-email governance guard at init.
  - Admin-side `docusign-url` degrades to `email_only` instead of 502.
  - Legacy joint-account rows show "institution not set" instead of "· ·".
  - Fixed typo'd demo institution signatory email in dev DB
    (`escrowwdemo@` → `escrowdemo@pmcmanagers.com`).
  - DocuSign 424/428 auth failures normalised to 503 in the escrow
    envelope endpoint; verified live (503 + 400 missing-officer guard).
- Bundle fixes: backend zip layout matches v53q exactly (Dockerfile at
  root, `.ebextensions` + `.dockerignore` included, `keys/` excluded —
  prod secrets come from SSM/EB env vars); frontend zip excludes
  `build/downloads/` (was 346 MB → 3.9 MB).
- Release bundles: `pmc-backend-v54a.zip`, `pmc-frontend-v54a-prod-build.zip`.

## Earlier releases
See `/app/frontend/public/downloads/DOWNLOAD_v53*.md` for v53i through v53q
summary notes.
