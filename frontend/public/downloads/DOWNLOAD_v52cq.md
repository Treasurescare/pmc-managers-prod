# PMC Managers · v52cq Release Notes

**Build date:** 13 Oct 2026
**Previous release:** v52cm → v52cn → v52co → v52cp → **v52cq**

---

## What's in this bundle

### 1. **v52cp — Notice ↔ Tender Builder bridge fixes** (ships here)
- **"Sometimes 422"** when saving tenders in Tender Builder → fixed. Empty
  section code/title and short placeholder names no longer trip Pydantic.
- **Create Notice from Tender Builder** now:
  - Lands at the TOP of the viewport (scrollIntoView — no scrolling past the list).
  - Prefills **title / description / category / delivery country / budget /
    budget currency / EMD fixed+% / EMD currency** from the tender header.
  - **Leaves submission deadline empty** (user picks at publish time).
  - Shows an amber "Documents from the linked tender" panel listing every
    section attachment with a per-row **View** button + shortcut back to
    Tender Builder for add / modify / delete.
  - **Primary document is now optional** (no more forced upload).
- **Public /tenders landing** cards (legacy and register-table layouts)
  now render EMD and Country alongside Budget / Deadline / Category.

### 2. **v52cq — "Preview as bidder" for draft notices** (new in this bundle)
- Admin → Notices: every draft row now has an amber **"Preview as bidder ↗"**
  button that opens the same public notice page the vendor would see,
  with a top banner reading **"DRAFT PREVIEW — Vendors cannot see or bid
  on this yet"**.
- Published notices still get the original "Preview ↗" button.
- Powered by `GET /api/v1/notices/{ref}/admin` + `?preview=1` query flag.

### 3. **Carried forward from v52cn / v52co / v52cm**
- Full 150k+ UNSPSC codeset searchable (biogas / solar / CBG / STP synonyms).
- 250-country master wired into vendor + company creation; cascading
  country → state → city → ZIP editor.
- Country Licenses CRUD + Geography viewer in Admin → Masters.
- Section D UNSPSC multi-picker for business verticals.
- KZ Licenses Held block hidden unless KZ is relevant.
- Masters → Geography coverage overlay (shaded rows + "N lic" chips).

---

## Download links (preview env)

> Replace `pmc-forest-green.preview.emergentagent.com` with your preview host.

| Bundle | File | Size |
|---|---|---|
| Backend (Elastic Beanstalk) | [`/downloads/pmc-backend-v52cq.zip`](/downloads/pmc-backend-v52cq.zip) | ~20 MB (compressed; 160 MB uncompressed incl. seed data) |
| Frontend (CloudFront / S3)  | [`/downloads/pmc-frontend-v52cq-prod-build.zip`](/downloads/pmc-frontend-v52cq-prod-build.zip) | ~3 MB |

**Full URLs from the preview host:**
```
https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52cq.zip
https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cq-prod-build.zip
```

---

## AWS deploy steps

### Backend → Elastic Beanstalk
1. Download `pmc-backend-v52cq.zip` from the link above.
2. In your EB console: **Upload and deploy** → pick the zip → next.
3. Confirm env vars are still set (nothing new in v52cp/cq):
   - `MONGO_URL`, `DB_NAME`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`,
     `LLM_API_KEY`, `RESEND_API_KEY`, `JWT_SECRET`, admin/staff seed passwords.
4. First boot will **auto-import** master data (UNSPSC + countries + states
   + cities + country licenses) if the collections are empty. This runs
   once; subsequent boots are instant.

### Frontend → S3 + CloudFront
1. Download `pmc-frontend-v52cq-prod-build.zip`.
2. Unzip → upload contents to your S3 bucket (overwrite).
3. CloudFront invalidation: `aws cloudfront create-invalidation --distribution-id <ID> --paths '/*'`

---

## Smoke tests after deploy

```
# Backend
curl -s https://api.YOUR-DOMAIN/api/v1/masters/countries | jq 'length'   # → 250
curl -s https://api.YOUR-DOMAIN/api/v1/masters/unspsc/public/search?q=biogas | jq 'length' # ≥ 10

# Frontend
# 1. Admin → Notices → any DRAFT row → "Preview as bidder ↗" → amber banner
# 2. Admin → Tender Builder → open a draft with a filled header →
#    "Create notice" → lands at the top of /admin/e/notices with every
#    field prefilled except Submission deadline
```

---

## Regression footprint
- Pytest: 15/15 (`tests/test_v52cn_masters.py` 11 + `tests/test_v52cp_notices.py` 4).
- Testing agent iteration 60: 100% backend + frontend acceptance.

---

## Earlier bundles (still available)
- `pmc-backend-v52cm.zip` + `pmc-frontend-v52cm-prod-build.zip` (previous)
