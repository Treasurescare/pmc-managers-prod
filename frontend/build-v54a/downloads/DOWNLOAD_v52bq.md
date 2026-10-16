# PMC Managers — Release v52bq (10 Oct 2026)

Frontend-only update (backend unchanged from v52bp).

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bq-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bq-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: keep [`/downloads/pmc-backend-v52bp.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bp.zip) — unchanged

## 🎯 What's Fixed in v52bq

**Tender Builder → DOWNLOAD PDF 401 fixed** — the button was opening a raw browser tab to `GET /api/v1/tender-templates/<id>/export/pdf`, an admin-only endpoint. Browser navigations don't carry the Bearer token, so the new tab showed `{"detail":"Not authenticated"}`. The button now fetches the PDF through the authenticated axios client, converts it to a Blob and triggers a real download (`<tender-name>_<lang>.pdf`). Errors surface as a toast instead of a dead tab.

(The PRINT / PDF button next to it stays client-side — it builds a print-ready HTML view and calls the browser's Save-as-PDF dialog, no backend call involved.)

Includes everything from v52bp: corrigendum PDF + public attachments, vendor-bell 📄 Open PDF deep link, Tender Builder filters that actually filter (masters + drafts), country dropdown seeded from the country master.

## 🚀 Deploy

```bash
aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```
Backend: no redeploy needed (keep v52bp).
