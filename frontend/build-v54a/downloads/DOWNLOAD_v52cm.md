# PMC Managers v52cm — Masters data pull (12 Oct 2026)

## What's shipped
Addresses user Q (a) and Q (b): categories master was thin, geography was free text.

### 1. UNSPSC master — full codeset (158,464 rows)
- Imported **UNSPSC v26.0801** from `codebysaadbouh/unspsc-fr` (88 MB SQLite in release artifact).
- Covers all 4 levels (58 segments · 559 families · 7,998 classes · 149,849 commodities) with EN + FR titles.
- Mongo collection: `masters_unspsc` with indexes on `(code, level)` unique, `segment`, `level`, and a `title_en + title_fr` text index.
- Verified live:
  - `solar` → 20 hits incl. **26111607 Solar generators**, **26131507 Solar power plants**, **25202002 Spacecraft solar arrays**.
  - `biogas` / `methane` → hits incl. biogas generators and methane monitors.
- **API**:
  - `GET /api/v1/masters/unspsc/search?q=...&level=commodity&segment=26&limit=50` — admin
  - `GET /api/v1/masters/unspsc/public/search?q=...&limit=30` — public, lighter payload for the registration portal
- The existing hand-curated `categories` collection is left untouched; UNSPSC is the lookup universe.

### 2. Geography masters — 250 countries · 5,328 states · 152,021 cities
- Imported **dr5hn countries-states-cities-database** (ODbL — attribution required).
- Collections: `masters_countries`, `masters_states`, `masters_cities` (indexed `country_code`, `state_code`, `name`).
- Countries carry each nation's `postal_code_format` and `postal_code_regex` — ZIP stays a free-text field but is **live-validated** against the country rule (no 10M-row dropdown needed).
- **API**:
  - `GET /api/v1/masters/countries` — 250 entries
  - `GET /api/v1/masters/states?country_code=IN` — 36 for India (verified)
  - `GET /api/v1/masters/cities?country_code=IN&state_code=MH&q=mumb&limit=100`

### 3. Country license requirements master
- Hand-curated seed for 6 countries the user listed:
  - **IN**: GST, PAN, MSME/Udyam, ESI, EPFO, Shop & Establishment
  - **KZ**: BIN, State registration, Construction licence
  - **AE**: Trade licence (DED/FZ), VAT TRN, ESR filing
  - **US**: EIN, State business registration, SAM.gov/CAGE
  - **GB**: Companies House, VAT, HMRC UTR
  - **SG**: ACRA UEN, GST, BCA contractor licence
- Admin-editable per country.
- **API**:
  - `GET /api/v1/masters/country-licenses/{country_code}` — public
  - `GET /api/v1/masters/country-licenses` — admin, all countries configured
  - `PUT /api/v1/masters/country-licenses/{country_code}` — admin upsert

### 4. Vendor Registration — Section D cascading dropdowns
- `RegionOfficeEditor.jsx` now uses the master-driven cascade:
  **Country → State → City (search-as-you-type over 152k) → ZIP (regex-validated)**.
- Existing offices show the country code only (country/state/city immutable after add); edit still works for address, name, zip.
- Legacy string-regions backward-compat banner preserved.

### 5. Auto-seed on startup
- `server.py::_bootstrap_masters` auto-runs `seed_unspsc` / `seed_geography` / `seed_country_licenses` when each collection is empty, so **a fresh production deploy auto-seeds all masters on first boot** — no manual script run required.
- Data files baked into the backend archive at `backend/data/` (`unspsc_v26.sqlite` 112 MB · `csc.json` 53 MB).

## Deploy
- **Backend**: `pmc-backend-v52cm.zip` — ~170 MB (includes master data files).
- **Frontend**: `pmc-frontend-v52cm-prod-build.zip` — supersedes v52cl.
- First prod boot takes ~90 s to seed; subsequent boots are instant (collections are already populated).

Files:
- `pmc-backend-v52cm.zip`
- `pmc-frontend-v52cm-prod-build.zip`
