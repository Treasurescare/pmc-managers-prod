# PMC Managers — Release v52bm (10 Oct 2026)

Frontend-only update (backend unchanged from v52bl).

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bm-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bm-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: use the v52bl bundle — [`/downloads/pmc-backend-v52bl.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bl.zip) (unchanged)

## 🎯 What's Fixed / Added in v52bm

1. **Create Notice validation no longer redirects to Tender builder** — the global click interceptor (`PmcLinkPatcher`) was hijacking any admin button whose label starts with "Create" / "New …". Now wired admin controls (`data-testid` present) own their own onClick. When category / budget / EMD / primary doc is missing the toast appears on the SAME page, the form stays open and your typed data is preserved.

2. **Corrigendum form now shows every current field of the selected notice** — pick a notice and the create form renders a 4-column table:
   - **Field** · **Current value** · **New value (optional)** · **Reason for this change**
   - Fields covered: Title, Description, Category, Document type, Delivery country, Submission deadline, Budget currency, Budget amount, Tender fee, Form of contract, EMD fixed amount, EMD %, Pre-bid meeting, Clarifications close.
   - Leave *New value* blank to keep the current value.
   - If you fill a *New value*, a per-row *Reason* becomes mandatory (recorded in the diff + audit).
   - Added a mandatory **Corrigendum date** field (defaults to now).
   - Overall change description is now required with a minimum of 8 characters.
   - The published corrigendum rows now display the full before / after / reason table and the corrigendum date in the admin list.

## 🚀 Deploy

- Replace the frontend bundle on S3 and invalidate `/*`:
  ```bash
  aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
  aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
  ```
- Backend: no redeploy needed (keep v52bl).
