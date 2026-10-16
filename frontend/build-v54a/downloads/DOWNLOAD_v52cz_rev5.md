# PMC Managers — Release v52cz rev5

**Date:** 14 Feb 2026
**Scope:** Escrow registration — searchable country/state pickers · 422 on blank signatory fixed · production geography auto-seed repaired (includes rev4 + rev3 + rev2)

> **Supersedes all earlier v52cz revisions.** Deploy rev5.

---

## What's new in rev5

### 1. Country & State are now typeable / searchable
Plain `<select>` elements forced scrolling through 250 countries / 36+ states. Both are now search-as-you-type comboboxes:
- Country: matches name, ISO code and dial code ("ind", "IN", "+91", "91" all find India). Shows flag emoji + dial code per row.
- State/Province: matches name or state code.
- City stays a typeahead with the 152k-row city master (filterable as you type).

### 2. 422 "email must have an @-sign" on Save and continue — fixed
The form starts with one blank signatory row (`name: "", email: ""`). The backend's `EmailStr` rejected the empty string with HTTP 422 before the draft could be created. Now:
- `Signatory.email` is optional; empty strings coerce to `None` (Pydantic pre-validator).
- Completely blank signatory / banking scaffold rows are dropped before persistence (`_clean_payload`), on both register and update.
- Frontend also strips blank rows before POST/PATCH (defence in depth).
- A partially-filled signatory (name but no email) is kept with `email: null`. Real garbage ("not-an-email") still 422s — guard intact.

### 3. Production "No states for this country" — root cause fixed
Production had countries seeded (duplicated to ~500 rows) but **zero states and zero cities**. The startup auto-seed only ran `seed_geography` when `masters_countries` was empty — since countries already existed, states/cities never got seeded.

The bootstrap now seeds geography when **any** of `masters_countries` / `masters_states` / `masters_cities` is empty, and also auto-seeds `masters_country_formats` (the 17-country CIN/PAN/GSTIN/BIN… regexes) when missing. After this deploy, simply **restarting the backend once** repairs the data automatically — no SSH required.

If you prefer to run it manually instead (or want it immediately without a redeploy):
```
python -m scripts.seed_masters        # geography + UNSPSC + licenses (idempotent; drops & rebuilds)
python scripts/seed_country_formats.py
```
(Running `seed_masters` also fixes the duplicated ~500 country rows — it drops and re-seeds the canonical 250.)

### Carried over (rev4 / rev3 / rev2)
- Escrow Core: structured address (country→state→city→zip→addr1/2), REQUIRED pills, country-aware reg-no/tax-id/VAT regex validation via `/api/v1/masters/country-formats/{cc}`.
- Documents tab on tender detail fully data-driven + "Download all (N)" above the list.
- Blank registration form always auto-generated (canonical `PMC-Vendor-Registration-Form.pdf`), resume-DOCX leak blocked.
- Vendor bid bundle picker (checkboxes, Download selected).
- All download URLs relative (CORS fix for pmcmanagers.com).

### Tests
- `backend/tests/test_v52cz_rev5_escrow_core.py` — 4 new tests: blank signatory row accepted & dropped, partial signatory kept with null email, garbage email still 422, structured address persisted.
- Targeted suite: 9/9 green (rev5 + rev4). Preview UI verified: "kaza"→Kazakhstan, "alm"→Almaty state, city typeahead, KZ BIN hint.

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev5.zip`](./pmc-backend-v52cz-rev5.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev5-prod-build.zip`](./pmc-frontend-v52cz-rev5-prod-build.zip) | S3 / CloudFront static assets |

Backend zip invariants: `Dockerfile` + `.ebextensions/` kept; **no** `docker-compose.yml`, `.env`, `keys/`, tests. `scripts/` + `data/` (csc.json, unspsc sqlite) **are** included so the bootstrap/manual seed can run.

## Deployment steps

### Backend → AWS Elastic Beanstalk
1. Deploy `pmc-backend-v52cz-rev5.zip`.
2. Wait for the environment to go green, then give the background bootstrap ~3 minutes (it logs `[bg-bootstrap] seeded geography …` / `seeded country formats …` to the EB log).
3. Smoke checks:
   ```
   curl -s "https://www.pmcmanagers.com/api/v1/masters/states?country_code=IN" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
   # → 36
   curl -s "https://www.pmcmanagers.com/api/v1/masters/cities?country_code=IN&state_code=MH&limit=5" | python3 -m json.tool | head
   curl -s "https://www.pmcmanagers.com/api/v1/masters/country-formats/IN" | python3 -m json.tool | head
   ```

### Frontend → S3 + CloudFront
Standard sync of the unzipped build + CloudFront `/*` invalidation.

### Browser smoke test
https://www.pmcmanagers.com/escrow/register → Step 1:
- Click Country, **type "ind"** → India appears, pick it.
- State field enables; **type "mah"** → Maharashtra; City typeahead accepts Mumbai.
- Postal code shows the Indian format; CIN hint appears under Registration number.
- Save with a blank signatory → proceeds to Step 2 (no more 422).

## Rollback
Re-deploy any earlier `pmc-backend-v52cz-rev*.zip` + matching frontend ZIP.
