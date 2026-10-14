# PMC Managers — Release v52cz rev6

**Date:** 14 Feb 2026
**Scope:** Escrow registration — Save-as-draft + Back on every step · dual phones with ISD code · bank master picker with IBAN/SWIFT/IFSC/sort/ABA validation · document viewer fix (includes everything in rev5 and earlier)

> **Supersedes v52cz rev5.** Deploy rev6.

---

## What's new in rev6

### 1. "Save as draft" + "Previous" on every step
Previously the only way forward was "Save and continue" and there was no Back button. Rev6 wraps steps 2–4 in a shared `StepShell` with:
- **← Previous** button
- **Save as draft** button (PATCH + stay on step)
- **Save and continue** button
Step 1 additionally gets its own Save-as-draft so the user can abandon the draft mid-Core-fill without losing data. Step 5 (Submit) replaces the Next button text with "Submit for PMC review".

Backend model relaxed: every `EscrowInstitutionIn` field is now Optional. The submit endpoint still enforces the mandatory set (`legal_name`, `country`, `registered_address`, `reg_number`, `primary_contact_email`, ≥1 signatory, ≥1 banking row).

### 2. Mobile + Office tel both ISD-prefixed
Core step now has **two** phone fields — `mobile_phone` and `office_phone` — both using the `PhoneInput` primitive with an ISD hint ("Starts with +91" for India). The mobile value is also mirrored into the legacy `primary_contact_phone` for back-compat with existing escrow dashboard code.

### 3. Banking step rewritten with real bank master
Each bank row now has:
- **Bank country** — type-ahead picker from `masters_countries` (250 ISO rows).
- **Bank** — type-ahead autocomplete from `masters_banks` filtered by the chosen country. Picking a bank auto-fills:
  - SWIFT prefix (first 6 chars + "XXX" placeholder for the branch section).
  - Default currency from the bank's supported currencies.
- **State / City (branch)** — cascading from `masters_states` + `masters_cities` so the user can tag which branch holds the account; falls back to free-text "Branch".
- **IBAN / SWIFT** — live-validated:
  - SWIFT: `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$` (8 or 11 chars).
  - IBAN: `^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$` (ISO 13616).
- **Local routing fields** shown only when relevant:
  - UK: Sort code (`\d{2}-?\d{2}-?\d{2}$`).
  - US: ABA Routing (`\d{9}$`).
  - India: IFSC (`^[A-Z]{4}0[A-Z0-9]{6}$`).
- **Correspondent bank + Correspondent SWIFT** fields for international wires.

New `masters_banks` collection seeded with **73 banks across 17 countries** (SBI, HDFC, Chase, Barclays, DBS, Deutsche Bank, Emirates NBD, …). Admin UI can extend; UI gracefully falls back to free text when a country isn't seeded.

New endpoint: `GET /api/v1/masters/banks?country_code=IN&q=sbi` returns the filtered list.

### 4. Document viewer "Sign in to download tender documents" — fixed
The register flow is magic-link based (no admin or vendor session). The old `View` button pointed at the protected `/api/v1/uploads/files/{key}` endpoint which 401s for anonymous callers with that exact message.

New endpoint: `GET /api/v1/escrow-institutions/{iid}/documents/{slot}/file?token=&download=true` validates the magic token against the registration + confirms the file key is attached to it before serving via the existing `_legacy_get_file_body`. The frontend `View` button now uses this endpoint.

### Carried over (rev5 → rev2)
- Searchable Country/State comboboxes, structured address, REQUIRED pills, country-aware reg-no/tax-id/VAT regex validation.
- Production geography auto-seed repaired (one restart heals a prod with 0 states/cities).
- `masters_country_formats` auto-seeded on first boot.
- Documents tab + Download all; blank form canonical; bundle picker; CORS fixes.

### Tests
- `backend/tests/test_v52cz_rev6_escrow.py` — 5 new tests (banks filter+search, banks empty for unknown country, PATCH as draft with partial fields + dual phones, magic-token file serve, wrong-token rejected).
- Targeted suite 14/14 green (rev4 + rev5 + rev6).

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev6.zip`](./pmc-backend-v52cz-rev6.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev6-prod-build.zip`](./pmc-frontend-v52cz-rev6-prod-build.zip) | S3 / CloudFront static assets |

Backend zip includes `scripts/seed_banks.py` + `scripts/seed_country_formats.py` + `scripts/seed_masters.py` + `data/` so bootstrap can auto-seed everything on first boot.

---

## Deployment

### Backend → AWS Elastic Beanstalk
1. Deploy `pmc-backend-v52cz-rev6.zip`.
2. Wait ~3 minutes after green for the background bootstrap to seed `masters_banks` (and anything else missing). Logs: `[bg-bootstrap] seeded banks rows=73`.
3. Smoke:
   ```
   curl -s "https://www.pmcmanagers.com/api/v1/masters/banks?country_code=IN&q=sbi" | python3 -m json.tool
   # → shows SBI
   ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront `/*` invalidation.

### Browser smoke test
Open https://www.pmcmanagers.com/escrow/register → Step 1:
- Dual phones visible (Mobile + Office tel), both with "+91" hint after picking India.
- "Save as draft" button bottom-right.
- Save and continue → Step 2 → **← Previous** + **Save as draft** both work.
- Step 3 Banking → pick India as Bank Country → **Bank** typeahead lists SBI/HDFC/ICICI/…; picking SBI pre-fills SWIFT prefix `SBININXXX`.
- Type a bogus IBAN → red border; type `GB82 WEST 1234 5698 7654 32` → green.
- Step 4 Documents → upload a PDF → **View** opens the file (no more "Sign in to download tender documents").

---

## Rollback
Re-deploy any earlier v52cz revision ZIP pair. The new collections (`masters_banks`) are additive.
