# PMC Managers v54c — FINAL all-in-one build (registration + escrow)

Release target: 17 Feb 2026

**This is the single bundle pair to deploy.** It contains everything from
v54a (escrow EMD pack) + v54b (registration unblocked) + v54c (signature
whitelist + upload persistence fixes). Do NOT deploy v54a/v54b separately.

## What v54c adds on top of v54b

### 1. Signature block actually saves (the "Missing signature field" fix)
The frontend whitelist `REGISTRATION_UPDATE_FIELDS` in `api.js` was
missing `signature_name`, `signature_title`, `signature_date` and
`directors` — so even with the v54b backend fix, the browser silently
dropped the signature block on every save and Submit for Review 400'd.
All four fields are now whitelisted. Verified end-to-end:
save → resume → submit returns `{"ok": true, "status": "submitted"}`.

### 2. Admin "Edit sections" no longer 422s
`adminApi.registrationAdminUpdate` bypassed the field whitelist and sent
server-managed fields (`email`, consent flags, timestamps) → every save
from the admin edit screen failed with "Extra inputs are not permitted".
It now goes through the same whitelist as the public path.

### 3. Uploaded files can no longer be wiped by a stale save
`document_slots` is deliberately kept OUT of the save whitelist and
stripped in `saveDraft` — document state is owned exclusively by the
upload/delete slot endpoints. Previously a PATCH from a stale tab could
overwrite the slots map and make an uploaded file "disappear" from the
form.

### 4. View / Download verified
`GET /api/v1/registrations/{id}/documents/{slot}/file?token=…` returns
200 with the correct content type; all API responses already carry
`Cache-Control: no-store` so CloudFront cannot serve a stale pre-upload
state after navigation.

## Verified E2E (this exact chain now passes against the preview)

1. Create draft (country dropdown now lists all 250 countries)
2. Upload PDF to a document slot → 200
3. Save Draft with signature + directors + declarations → 200
4. Resume → signature, slots, directors all present
5. View file → 200 `application/pdf`
6. Submit for review → `{"ok": true, "status": "submitted"}`

## Deploy (one go)

1. EB: upload `pmc-backend-v54c.zip`, wait for Green.
2. S3: sync the contents of `pmc-frontend-v54c-prod-build.zip` (plain
   `aws s3 sync`, no `--delete`), then CloudFront invalidate `/*`.
3. Hard-reload the site and run your from-zero vendor registration.

## Artifacts

* Backend: `pmc-backend-v54c.zip`
* Frontend: `pmc-frontend-v54c-prod-build.zip`
