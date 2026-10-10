# PMC Managers — Release v52bs (10 Oct 2026)

Backend changed — redeploy EB this time.

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bs-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bs-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: [`/downloads/pmc-backend-v52bs.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bs.zip)

## 🎯 What's Fixed in v52bs

1. **Stakeholder Reports → Download CSV network error fixed** — `csvUrl` was returning a FULL URL (`${REACT_APP_BACKEND_URL}/api/v1/…`). On production the frontend origin (`pmcmanagers.com`) hitting the preview backend origin tripped CORS → "Network Error" on the toast. Now returns a path only (`/api/v1/stakeholder-reports/<kind>?format=csv`); axios adds the baseURL and the Bearer token, same origin, no CORS. Downloads as `stakeholder-<tab>.csv`.

2. **Tender Builder — Industry filter now sourced from Categories master** — the Industry dropdown previously listed only values found on existing templates. Now it merges the full Categories master (`/api/v1/masters/categories/public`) with template-derived values, so selecting "Public Works / Construction / PMC" (or any master category) properly filters both Master Library and Drafts.

3. **BOQ — Add line item / Edit / Delete inline** — the BOQ viewer used to be read-only (and the "1-5 of 5 · 0 items" was just the empty table showing a stale pager control). Now:
   - **Add line item** form at the top: Description * / Unit / Qty / Rate / running total · UNSPSC picker (sourced from the UNSPSC/Categories master).
   - Each row in the table has **Edit** and **Delete**.
   - New backend endpoint `PATCH /api/v1/boq/templates/{id}` validates + persists items (sl_no auto-renumbered server-side), audit-logged, admin-only.
   - When there are no items the table shows a clean empty state ("No line items yet. Add rows above or import an Excel BOQ.") — no fake pagination.

## 🚀 Deploy

- **Backend** (Elastic Beanstalk): upload `pmc-backend-v52bs.zip`.
- **Frontend** (S3 / CloudFront):
  ```bash
  aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
  aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
  ```
