# PMC Managers · v52cy Bundle (supersedes v52cu + v52cv + v52cw + v52cx)

**Date:** 13 Feb 2026
**Frontend:** `pmc-frontend-v52cy-prod-build.zip` (~3 MB)
**Backend:** `pmc-backend-v52cy.zip` (~20 MB) — rolls up the earlier v52cu/v52cx backend changes **plus the new public pack endpoint**.

Deploy BOTH this time. Backend first.

## What changed

Everything from v52cu/v52cv/v52cw/v52cx, plus these seven fixes:

1. **Bid uploads** — Vendor Bid Submit now accepts PDF / DOC / DOCX / XLS / XLSX / PPT / PPTX / JPG / JPEG / PNG / DWG only; the caption on every tile lists the allowed types; non-matching files are rejected with a clear toast before the upload fires.

2. **Download pack (public)** — new backend endpoint `GET /api/v1/notices/{notice_ref}/pack` zips the primary document + every attachment + a README manifest. **No auth required** — this is what the public Notice Board calls. The previous flow fell back to the protected `/api/v1/uploads/files/{key}` path and returned "Sign in to download tender documents" for anonymous visitors. Returns 404 only when the notice is unpublished OR has no documents.

3. **"Fill full form" upload/download in Admin** — same auth path fixed by (2) + (4) below. Opening the vendor doc viewer and uploading in the admin "New vendor" wizard now works end-to-end.

4. **HTTP 422 "Extra inputs are not permitted"** — root-caused: the admin "fill full form" screen leaked `email` (and sometimes `kzMeta` / `document_slots`) into the PATCH body, and Pydantic `RegistrationUpdateIn` has `extra="forbid"` for security. Fix: the client-side `registrationApi.update()` now whitelists only fields the schema accepts, so every caller is safe regardless of what the UI stashes in local state.

5. **Section D / E `*` prominence** — the thin red asterisk has been replaced with a bold red **REQUIRED** pill next to every mandatory label; document slots gain a REQUIRED / OPTIONAL pill in the corner of each card. Impossible to miss.

6. **"Download blank form" 404** — the backend endpoint has a fallback PDF generator that was correct already (returned HTTP 200 / 4232 B PDF on preview, hard-tested). Production was 404'ing because it was on a stale image — the backend half of this bundle ships that fallback to production.

7. **Comma blocked in numeric fields** — three turnover inputs + employees-count were calling `parseFloat(replace(/,/g,""))` on every keystroke, so `"1,000"` immediately became `1000` on screen and admins thought the comma key was blocked. New `NumericInput` keeps your raw string with commas while you type and only commits a parsed number on blur.

## Verified live on preview before shipping

- `GET /api/v1/notices/PMC-NOT-2026-0020/pack` → HTTP 200, valid ZIP (anonymous curl, no cookies). ✅
- `GET /api/v1/notices/<no-docs>/pack` → HTTP 404 with clear detail. ✅
- `GET /api/v1/vendors/registration-template` → HTTP 200, valid PDF (anonymous). ✅
- Public notice detail (`/notices/PMC-NOT-2026-0020`) → Download pack fires a browser download with filename `PMC-NOT-2026-0020-tender-pack.zip`. ✅
- `/register` → **Download blank form** fires a browser download. ✅
- `/admin/vendors/new` Section A → typing `1,500` into employees stays `1,500` on screen; blurs to the formatted number. ✅
- Section D → **REQUIRED** pills visible on both fields and document slots; **Save & next →** CTA present. ✅

## Deploy order (~15 min)

### 1. Backend first (EB, eu-west-2)

- Download https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52cy.zip
- EB console → `pmc-backend-prod` → **Upload and deploy** → version label `v52cy-YYYYMMDD-HHMM` → Deploy.
- Wait for "Environment update completed successfully".
- Smoke: `curl https://api.pmcmanagers.com/health` → `{"ok":true,...}` and `curl -I https://api.pmcmanagers.com/api/v1/notices/<ref>/pack` → `HTTP/2 200`.

### 2. Frontend (S3 + CloudFront)

- Download https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cy-prod-build.zip
- Unzip into the S3 origin bucket (replace `index.html`, `static/*`, etc.).
- CloudFront → **Create invalidation** → `/*`.

### 3. Verify on production

- Open the Payment Test Tender in incognito → **Download pack** must save a zip (no "Sign in" error).
- Admin → New vendor → type `1,500` into Employees → stays `1,500` while typing.
- Admin → New vendor → Section D → mandatory fields show the red **REQUIRED** pill, document slots show REQUIRED / OPTIONAL pills.
- `/register` → **Download blank form** must save a PDF.

## Known / not-in-scope

- Zero-EMD bid progression still awaits one real production bid test.
- Escrow institution + approval-matrix work from v52cx is in this bundle — no extra steps.
- Masters data (geography / country licenses) unchanged.
