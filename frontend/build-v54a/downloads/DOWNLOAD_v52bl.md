# PMC Managers — Release v52bl (10 Oct 2026)

Full production release bundle containing all recent fixes across Evaluation, Notices, EMD display, Engagements, Work Packages, and Currencies master.

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bl-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bl-prod-build.zip) (3.0 MB)
- **Backend (AWS Elastic Beanstalk)**: [`/downloads/pmc-backend-v52bl.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bl.zip) (528 KB) — *Root layout with Dockerfile, Dockerrun.aws.json, .platform/*

---

## 🎯 What's Included in v52bl

1. **Evaluation Panel Crash Fix**:
   - Fixed `AwardReport` crashing with "Something crashed on this screen" on partial or empty reports.
   - Guarded on `report.notice_ref` and safely defaults minimum technical cutoff.

2. **Public Tender EMD Display**:
   - Fixed EMD showing as "—" on public notice pages.
   - Backend now computes and exposes flat `emd_amount`, `emd_currency`, and `emd_percentage` from `emd_config` + `budget_amount`.
   - Notice detail page accurately renders currency amounts (e.g., "$204,000" or "3% of bid value").

3. **Notice Timeline Matching**:
   - Fixed Key Dates rail on the notice preview page: dynamically pulls real published date, corrigenda history, clarification deadline, pre-bid meeting, and final submission deadline rather than static demo dates.

4. **Notice Creation Zero-Value Guard**:
   - Backend & frontend reject notices created with `$0` budget or `$0` EMD. Both fields are now mandatory with positive non-zero validation.

5. **Engagements Cancel Modal**:
   - Fixed Cancel action to open a dedicated modal requiring a minimum 5-character reason, logged to audit ledger.

6. **Engagements Buyer / Supplier Meetings**:
   - Added lightweight PMC-internal meeting scheduler (date/time, duration, agenda, attendee selector, printable agenda sheet) with backend persistence and notification triggers.

7. **Work Packages Sample CSV**:
   - Added `GET /api/v1/packages/import/sample.csv` endpoint and a one-click "Sample CSV" download button on the Work Packages panel.

8. **Masters Currencies Tab**:
   - Added new "Currencies" master tab with full CRUD UI (add, inline edit, deactivate) backed by the 25-code ISO-4217 master database.

9. **Notice Preview Signed-in Navigation**:
   - Public notice detail page detects authenticated admin, staff, or vendor sessions and displays the dashboard avatar chip instead of "Sign in / Register".

---

## 🚀 Deployment Instructions

### 1. Backend (AWS Elastic Beanstalk)
- Upload `pmc-backend-v52bl.zip` directly to your Elastic Beanstalk environment.
- Root files (`Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf`) are pre-configured for the Docker platform.

### 2. Frontend (AWS S3 + CloudFront)
- Unzip `pmc-frontend-v52bl-prod-build.zip` and sync files to your S3 bucket:
  ```bash
  aws s3 sync . s3://<your-frontend-bucket>/ --delete
  ```
- Create a CloudFront cache invalidation:
  ```bash
  aws cloudfront create-invalidation --distribution-id <your-dist-id> --paths "/*"
  ```
