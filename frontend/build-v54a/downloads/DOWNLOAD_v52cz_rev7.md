# PMC Managers — Release v52cz rev7

**Date:** 14 Feb 2026
**Scope:** Escrow registration quality-of-life round 2 — ISD prefix dropdown + length validation · duplicate-email guard · bank roster expansion · in-page document viewer (includes everything in rev6 and earlier)

> **Supersedes v52cz rev6.** Deploy rev7.

---

## What's new in rev7

### 1. Phone numbers now have an ISD dial-code dropdown + length validation
Rev6 only showed a hint "Starts with +91". Users could still type free-form garbage. Rev7 introduces `PhonePrefixInput`:
- **Left side:** country-code button pre-selected from the Core country (e.g. India → `+91`). Clicking opens a searchable list of all 250 countries ("ind", "+44", "ger" all find a match). The user can override per field (e.g. London office tel on a Mumbai registration).
- **Right side:** digits-only local number, max length 15−dial-code (ITU E.164), min length 7−dial-code with a soft floor of 4. Border turns red + inline "Must be N–M digits for +XX" error if the local number is too short/long. Pasted +signs/spaces/hyphens are stripped automatically.
- Combined value stored as E.164 (`+919876543210`) so backend callers see one canonical string.

Used in **Core step** (Mobile + Office tel) and **Signatories step** (Phone per signatory). Both default to the Core country but let each field pick its own country.

### 2. Duplicate email guard
`POST /api/v1/escrow-institutions/register` now checks for ANY existing institution with the same `primary_contact_email` (case-insensitive, any status) and returns **HTTP 409** with:
```json
{ "detail": {
    "error": "escrow_email_already_registered",
    "message": "An escrow institution is already registered with info@emeraldcorporates.com (status: draft). If this is you, use the resume link we emailed, or contact PMC support.",
    "status": "draft"
}}
```
The frontend's `showApiError` surfaces this cleanly. If you were legitimately resuming, use the magic link from your invitation email or ask PMC support to reissue it.

### 3. Bank master expanded (146 banks across 20+ countries)
Doubled from 73 → 146. Includes major **neobanks**: Monzo, Starling, Revolut, Wise, N26, Chime, SoFi, Mercury, Varo, Ally; plus **payments banks** (Jio, Paytm, Airtel, Fino), **small finance banks** (AU, Equitas), and additional PSU/foreign bank rosters in India/UK/US/EU. Admin can extend the `masters_banks` collection; the UI still gracefully falls back to free text for any bank that isn't listed.

> **Note:** We can't ship a literally exhaustive list of every bank globally — there are ~25,000 licensed banks worldwide and no single public master dataset. If a specific bank is missing for your deployment, send me the country + name list and I'll seed it in a dedicated rev; or your admin can run `python scripts/seed_banks.py` with additions.

### 4. Document viewer stays in-page
Rev6 opened documents in a bare browser tab via `<a target="_blank">`. Rev7 adds an **in-page modal viewer** — click View → the PDF renders in an iframe beside the form (Download + Close buttons in the header), so the user never leaves the registration page.

### Carried over
Everything from rev6 (Save-as-draft + Previous on every step · dual phones · bank picker · magic-token file endpoint · structured address · searchable country/state · country-aware regex validation · prod geography auto-seed · blank form canonical · bundle picker · CORS fixes).

### Tests
- `backend/tests/test_v52cz_rev7_escrow.py` — 3 new tests (duplicate-email 409 w/ structured detail, bank roster size for IN/GB/US, neobank searchability).
- All targeted tests green on preview (rev7 + rev6).

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev7.zip`](./pmc-backend-v52cz-rev7.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev7-prod-build.zip`](./pmc-frontend-v52cz-rev7-prod-build.zip) | S3 / CloudFront static assets |

Backend zip includes expanded `scripts/seed_banks.py`. The bootstrap seeds `masters_banks` on first boot if empty. If `masters_banks` already has rev6 rows, **run the seed script once** to add the new banks:
```
python scripts/seed_banks.py
# → seeded masters_banks: inserted 73, updated 73, total 146
```
This is idempotent — safe to re-run.

---

## Deployment

### Backend → AWS Elastic Beanstalk
1. Deploy `pmc-backend-v52cz-rev7.zip`.
2. If prod already had the rev6 `masters_banks`, SSH in and run `python scripts/seed_banks.py` to upsert the new rows. Otherwise the first-boot bootstrap seeds all 146 automatically.
3. Smoke:
   ```
   curl -s "https://www.pmcmanagers.com/api/v1/masters/banks?country_code=IN&limit=200" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
   # → 34
   curl -s -o /dev/null -w "%{http_code}\n" -X POST \
       "https://www.pmcmanagers.com/api/v1/escrow-institutions/register" \
       -H "Content-Type: application/json" \
       -d '{"primary_contact_email":"info@emeraldcorporates.com","legal_name":"test"}'
   # → 409 (email already registered)
   ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront `/*` invalidation.

### Browser smoke test
Open https://www.pmcmanagers.com/escrow/register:
- Pick India → mobile shows `+91` prefixed button; typing "9876" shows "Must be 10–13 digits for +91" until length ≥ 10.
- Try registering with an already-used email → clear 409 toast.
- Step 3 → Bank country India → Bank list now includes SBI, HDFC, Axis, Yes, Kotak, AU SFB, Paytm, Jio, Airtel, Deutsche Bank India, Standard Chartered India… (34 options).
- Step 4 → upload a PDF → click View → opens in a modal with Download + Close.

---

## Rollback
Re-deploy any earlier v52cz revision. All new collections / fields are additive.
