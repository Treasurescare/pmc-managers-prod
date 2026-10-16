# PMC Managers — Release v52bo (10 Oct 2026)

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bo-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bo-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: [`/downloads/pmc-backend-v52bo.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bo.zip)

## 🎯 What's in v52bo

1. **EMD can be zero** — Removed the "EMD must be positive" validation (both backend and frontend). Walk-in tenders, free RFQs, and pre-qualifications no longer need an EMD. Budget amount is still mandatory and still cannot be zero.

2. **Stakeholder Reports no longer disappears** — Added "Stakeholder reports" to every page's left sidebar (was missing on Bidding Ops, Vendor KYC, Tender Builder, Programme, Evaluation List and Dashboard E-pages).

3. **Public page now reflects the latest corrigendum date** — The hero's "Corrigendum X · DD Mon" pill is now patched from the live notice record. Hard-coded demo pill ("Corrigendum 1 · 26 Sep") no longer leaks. When the most recent active corrigendum is published, the hero pill updates automatically. The pill hides entirely if no active corrigenda exist.

4. **Corrigendum PDF auto-attached to bidder email** — When you publish a corrigendum:
   - A one-page diff PDF is auto-generated (A4): title, effective date, overall change description, full **Field / Before / After / Reason** table (colour-coded red/green), deadline change callout, attachment names.
   - Email is sent via Resend to every active bidder with the PDF attached.
   - PDF is also downloadable publicly at `GET /api/v1/notices/<ref>/corrigenda/<cid>/pdf`.
   - Audit ledger records the PDF generation and the email fan-out size.

## 🚀 Deploy

- **Backend** (Elastic Beanstalk): upload `pmc-backend-v52bo.zip`.
- **Frontend** (S3/CloudFront):
  ```bash
  aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
  aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
  ```
