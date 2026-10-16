# PMC Managers v2 — v43 AWS Deployment Guide

**Contents of `pmc-deploy-v43-complete.tar.gz`** (44 MB total)
```
pmc-v43/
├── frontend-build/                    → deploy to S3 + CloudFront
├── pmc-backend-v22g.zip               → deploy to Elastic Beanstalk
├── PMC_User_Manual_v43.docx (2.1 MB)
├── PMC_User_Manual_v43.pdf  (2.2 MB)
├── PMC_Bug_Tracker_v16_20260919.xlsx
├── capture_manual_v43.py              → Playwright capture (for future re-runs)
└── build_manual_v43.py                → DOCX/PDF builder
```

Emergent runs inside a sandboxed container and **cannot reach your AWS account** — you (or anyone on your team with `pmc-admin` AWS credentials) must execute these two scripts on a workstation with the AWS CLI configured. Both scripts are copy-paste-safe extensions of the v40/v22f scripts you already ran.

---

## What v43 ships

**Frontend** (bundle: `main.*.js` inside `frontend-build/static/js/`)
- ⓘ **InfoDot tooltips** wired into every primary form field, filter and action button across all 26 admin panels (Notices, Registrations, Vendors, Packages, Bidding, Escrow, Corrigenda, Auctions, Meetings, VendorIntel, L1, Awards, DocuSign, BOQ, Contracts, Evaluation, Analytics, Audit, Masters (all 6 sub-tabs), Permissions, Tender Builder, Product Catalog, Engagements, Committee, AdminVendorCreate, Escrow Transactions).
- 🔴 **Loud red `showApiError()` toasts** on every failing API call — 51 files migrated, verbatim backend error + HTTP status, 12-second minimum duration, close button.
- 📥 The refreshed User Manual DOCX + PDF land in `frontend-build/downloads/` and become live at `https://www.pmcmanagers.com/downloads/PMC_User_Manual_v43.docx` (and `.pdf`).

**Backend v22g** (same zip as v42's — no breaking changes since)
- `/api/v1/meta/help` endpoints that power the in-app **Help** tab.

---

## Step-by-step

### 1. Prep — copy the two artefacts to your workstation

Download either the full tarball or the two individual zips (whichever is easier):

Full tarball:
```
https://www.pmcmanagers.com/downloads/pmc-deploy-v43-complete.tar.gz
```

Or individual pieces:
```
https://www.pmcmanagers.com/downloads/pmc-frontend-v43-build.zip
https://www.pmcmanagers.com/downloads/pmc-backend-v22g.zip
https://www.pmcmanagers.com/downloads/deploy-frontend-v43.sh
https://www.pmcmanagers.com/downloads/deploy-backend-v22g.sh
```
*(Note: the preview URL above will 401 if you're not signed in; alternatively grab them from the tarball you already have locally.)*

Land them all in one folder, e.g. `~/pmc-v43-deploy/`.

### 2. Frontend deploy (~2 min)

```bash
cd ~/pmc-v43-deploy
chmod +x deploy-frontend-v43.sh
./deploy-frontend-v43.sh
```

Expected output:
```
[1/4] Unzipped 41M into ./.deploy-v43
     Bundled main.js : main.XXXXXXX.js
[2/4] Static assets synced (long cache)
[3/4] index.html + manifest + downloads/ synced (no-cache)
[4/4] CloudFront invalidation created: I1234ABCDEF
✅ Frontend v43 deploy complete.
```

Wait 1–3 minutes for the CloudFront invalidation. Then hard-refresh:
- https://www.pmcmanagers.com/admin — log in, open any tab, hover the small ⓘ icons next to field labels → tooltip appears.
- Cause a failure (e.g. click **Publish** on a notice with no title) → red toast with backend error text.

### 3. Backend deploy (~4–6 min)

```bash
cd ~/pmc-v43-deploy
chmod +x deploy-backend-v22g.sh
./deploy-backend-v22g.sh
```

Expected output:
```
[1/3] Uploaded to s3://elasticbeanstalk-eu-west-2-637423434072/artifacts/pmc-backend/v22g-YYYYMMDD-HHMMSS.zip
[2/3] EB application version v22g-YYYYMMDD-HHMMSS registered
[3/3] EB environment pmc-backend-prod updating to v22g-YYYYMMDD-HHMMSS
✅ Backend v22g deploy triggered.
```

Watch status:
```bash
aws --profile pmc-admin --region eu-west-2 elasticbeanstalk describe-environments \
  --environment-names pmc-backend-prod \
  --query 'Environments[0].[Status,Health,VersionLabel]' --output table
```
`Status` should transition `Updating → Ready` and `Health` should end at `Ok`.

### 4. Smoke tests

```bash
# Frontend bundle hash matches expected
curl -sI https://www.pmcmanagers.com/index.html | grep -i etag

# Backend health (should return 200 with role=admin)
curl -sX POST https://www.pmcmanagers.com/api/v1/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"adminsupport@pmcmanagers.com","password":"Admin@12345"}' \
  | head -c 200

# Help meta endpoint (new in v22g)
curl -s https://www.pmcmanagers.com/api/v1/meta/help | head -c 200
```

### 5. Manual acceptance checks

- ✅ Admin console loads → hover the ⓘ next to **Title** on the New Notice form → tooltip appears
- ✅ Save a notice with an empty **Title** → red toast with 422 "Title must be at least 3 characters" (verbatim from backend)
- ✅ **Help** tab in the admin console loads the 28-module index without spinner
- ✅ `https://www.pmcmanagers.com/downloads/PMC_User_Manual_v43.pdf` returns 200 + 2.2 MB PDF

---

## Rollback plan (if anything looks wrong)

Frontend — revert by re-running the previous script:
```bash
./deploy-frontend-v42.sh   # (already in your local archives)
```

Backend — point EB back at the previous version label:
```bash
aws --profile pmc-admin --region eu-west-2 elasticbeanstalk update-environment \
  --environment-name pmc-backend-prod \
  --version-label v22f-<prev-timestamp>
```
(Look up the previous label with `aws elasticbeanstalk describe-application-versions --application-name pmc-backend-prod`.)

---

## Environment overrides

If your account uses different names, override before running:

```bash
AWS_PROFILE=my-profile \
S3_BUCKET=my-bucket \
CLOUDFRONT_ID=EXXXXXX \
./deploy-frontend-v43.sh
```

Same pattern for the backend script (`EB_APP`, `EB_ENV`, `S3_ARTIFACTS_BUCKET`).

---

## After deploy

Update the QA team with:
- **Bug Tracker v16**: `PMC_Bug_Tracker_v16_20260919.xlsx` (marks tooltips, error toasts, granular manual as ✅ COMPLETE)
- **User Manual v43**: `PMC_User_Manual_v43.docx / .pdf` (32 per-modal shots inline)
- Test creds: `adminsupport@pmcmanagers.com` / `Admin@12345`

That's it — hand it to your infra owner and the whole rollout should take ~10 minutes end-to-end.
