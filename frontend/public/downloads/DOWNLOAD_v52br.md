# PMC Managers — Release v52br (10 Oct 2026)

Frontend-only update (backend unchanged from v52bp).

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52br-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52br-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: keep [`/downloads/pmc-backend-v52bp.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bp.zip) — unchanged

## 🎯 What's Fixed in v52br

1. **Stakeholder Reports → Download CSV 401 fixed** — the button was a raw `<a target="_blank">` to an admin-only endpoint; browser tabs don't carry the Bearer token, so it showed `{"detail":"Not authenticated"}`. Now it fetches through the authenticated client and downloads `stakeholder-<tab>.csv` as a real file.

2. **Work Packages → Sample CSV 401 fixed** — same root cause on the admin-gated `/api/v1/packages/import/sample.csv` link. Now downloads `pmc-work-packages-sample.csv` via the authenticated client.

3. **Tender Builder — search results surface at the top** — when any filter is active (search text, country or industry), a **Matches** panel now renders directly under the filter bar with each matching draft (name, sections, kind, industry) — click opens the draft immediately. No more scrolling past Kind + Master Library to find search results.

New shared helper `downloadAuthedFile(path, filename)` in `lib/api.js` — use it for any future admin-gated download link instead of a raw `<a href>`.

Includes everything from v52bq: tender PDF authenticated download, corrigendum PDF + public attachments, vendor-bell PDF deep link, working Tender Builder filters.

## 🚀 Deploy

```bash
aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```
Backend: no redeploy needed (keep v52bp).
