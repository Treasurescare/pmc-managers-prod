# PMC Managers v54b — Public vendor registration unblocked

Release target: 17 Feb 2026

## Fixes in this build

### 1. Country dropdown now shows all 250 countries
`GET /api/v1/meta/countries` was serving the 30-row pilot config list,
leaving vendors outside the pilot countries with no way to self-register.
It now reads from the full `masters_countries` collection (dr5hn, 250
rows) and falls back to the pilot list only if the master is empty.

### 2. "Extra inputs are not permitted" (422) on Save Draft
`RegistrationUpdateIn` was `extra="forbid"` (for CSRF/SEC-003 defence in
depth), but the frontend was round-tripping the entire registration
object including `directors`, `document_slots`, `email`, consent fields,
and `consent_at`. Every save silently 422'd and `signature_name` never
reached the DB.

Fixed on both sides:
- Backend: `directors` and `document_slots` are explicit optional fields
  on `RegistrationUpdateIn`.
- Frontend: `saveDraft` now strips server-managed / draft-only fields
  (`email`, `data_processing_consent`, `marketing_consent`, `consent_at`,
  `magic_token`, timestamps, `vendor_ref`, reviewer fields) before PATCH.

### 3. "Missing signature field: signature_name" on Submit for Review
Cascade effect of fix #2: once PATCH stops 422ing, `signature_name` /
`signature_title` / `signature_date` are persisted and the submit
endpoint accepts the draft.

`submitFinal` now also halts on save failure (previously it swallowed
the 422 and tried to submit an unsaved draft, producing the confusing
400 followed by 422 toasts you saw).

## What's NOT in this build (planned v54c)

- Country-wise identity format validation on the public form (GST/PAN
  patterns, TRN/CRN regex, etc). The admin masters already have
  `masters_country_formats` seeded; we need to wire the live regex
  checks into Section A and the per-country license uploader.
- State / city dropdowns driven by `masters_states` / `masters_cities`.
- Address-line-1 / address-line-2 split with ZIP validation per country.
- Certificate / licence file-format validation beyond the existing
  "PDF / JPG / PNG · max 5 MB" check.

If you need those shipped on the public form, tell me and I'll build a
dedicated v54c follow-up.

## Artifacts

* Backend: `pmc-backend-v54b.zip`
* Frontend: `pmc-frontend-v54b-prod-build.zip`

Deploy as usual (EB upload for backend, S3 sync + CloudFront
invalidation for frontend). No DB migration required.
