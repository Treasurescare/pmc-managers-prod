# PMC Managers — Release v52cz rev4

**Date:** 14 Feb 2026
**Scope:** Escrow Institution registration — Step 1 (Core) rewritten with real validation (includes everything in rev3 + rev2)

> **Supersedes v52cz rev3.** Deploy rev4, not earlier revisions.

---

## What's new in rev4

User reported four problems on `/escrow/register` → Step 1 (Core):

1. Country was a plain text box.
2. Mandatory fields had no visual marker.
3. Registered address was a single free-text line.
4. Nothing was validated — any garbage was accepted; reg no / tax id / licence number should match the picked country's real format, not a hard-coded shape.

### Fixes

**a) Country dropdown with phone code + emoji**
Country is now a real `<select>` backed by the `masters_countries` collection (250 ISO rows). Each option shows the flag emoji, name, code and dial code (e.g. "🇮🇳 India (IN) +91"). Picking a country auto-fills the phone country code and resets the dependent address fields.

**b) REQUIRED pills on every mandatory field**
All mandatory fields use the same bold red `REQUIRED` pill as vendor registration (shared `Field` primitive from `registration-portal/sections/FormPrimitives`). On Save, missing fields show inline red error text and a summary banner lists them.

**c) Structured registered address — country → state → city → zip → address 1/2**
Cascading dropdowns:
- **State / Province** loaded from `/api/v1/masters/states?country_code=…`.
- **City** typeahead from `/api/v1/masters/cities` (filterable, backed by the 152k dr5hn city master).
- **Postal / ZIP** live-validated against the country's `postal_code_regex` (format hint shown next to the label).
- **Address line 1 / 2** are plain inputs.

The flat `registered_address` string the backend already stores is auto-composed from these pieces (backwards compatible with existing escrow records).

**d) Country-aware identifier validation (not hard-coded)**
New master endpoint `GET /api/v1/masters/country-formats/{cc}` returns `{reg_number, tax_id, vat}` with `label`, `example`, `regex` for each. The Core form:

- Shows the local label as the field name (e.g. India → "CIN (Company Identification Number)", UK → "Companies House number", Kazakhstan → "BIN").
- Shows the example underneath (e.g. "e.g. L17110MH1973PLC019786").
- Live-validates the typed value against the regex — border turns red on mismatch, submit is blocked.
- Falls back to free-text acceptance if a country isn't seeded yet (no false negatives for exotic jurisdictions).

Seeded for 17 countries: **IN, KZ, SG, JP, CN, AU, AE, SA, GB, DE, FR, US, BR, ZA, NG, RU, UA**. Extending to more countries is a one-row-per-country PR into `scripts/seed_country_formats.py`.

### Carried over
Everything from rev3 (Documents tab data-driven + Download all) and rev2 (Blank form regen, Bundle picker, Reg-doc CORS).

### Tests
- `backend/tests/test_v52cz_rev4_country_formats.py` — 5 new tests pinning the India / UK / KZ regexes against real identifiers, the fallback shape for unknown countries, and seed coverage for the big-17.
- Full suite: 14/14 green (`test_v52cz_rev4_country_formats`, `test_v52cz_downloads`, `test_v52cz_blank_form`).

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev4.zip`](./pmc-backend-v52cz-rev4.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev4-prod-build.zip`](./pmc-frontend-v52cz-rev4-prod-build.zip) | S3 / CloudFront static assets |

Same packaging invariants: `Dockerfile` + `.ebextensions/` kept; **no** `docker-compose.yml`, `.env`, `keys/`, or tests.

---

## Deployment steps

### Backend → AWS Elastic Beanstalk
1. Deploy `pmc-backend-v52cz-rev4.zip` to the production EB environment.
2. **Once deployed, SSH into the backend or run via the EB CLI**:
   ```
   python /app/scripts/seed_country_formats.py
   ```
   This upserts the 17 country-format rows into `masters_country_formats`. Idempotent — safe to re-run. Alternatively, if your EB container doesn't allow SSH, call the admin seed endpoint if available, or run the script against production MongoDB locally.
3. Smoke check:
   ```
   curl -s https://www.pmcmanagers.com/api/v1/masters/country-formats/IN | python3 -m json.tool
   # → shows {reg_number: {label: "CIN...", example: "L17110...", regex: ...}, tax_id: {...}, vat: {...}}
   ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront invalidation (same as rev3).

### Browser smoke test
Open https://www.pmcmanagers.com/escrow/register → Step 1:
- Country is a dropdown with flags + dial codes.
- Pick **India**. Fields change: reg-no label becomes "CIN", example appears underneath. Type a bogus "notACIN" → border turns red, submit shows "Fix the highlighted fields". Replace with `L17110MH1973PLC019786` → green.
- State dropdown lists all Indian states; picking Maharashtra enables the city typeahead; cities load from the master.
- Postal field shows the India postal format and goes red for junk input.
- Missing required fields are called out below the Save button with a red list.

---

## Rollback
Re-deploy any earlier `pmc-backend-v52cz-rev*.zip` + matching frontend ZIP. The new `masters_country_formats` collection is additive and will be ignored by older code.
