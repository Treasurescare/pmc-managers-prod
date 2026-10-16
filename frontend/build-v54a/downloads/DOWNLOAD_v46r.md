# PMC v46r — Production Release Manifest

All files below are hosted on your preview domain and served via HTTPS at `/downloads/<file>`.

## 1 · AWS Deployment Bundles (v46r)

| File | Size | Key Features & Fixes |
|---|---|---|
| **[`pmc-backend-v46r.zip`](./pmc-backend-v46r.zip)** | ~283 KB | **Elastic Beanstalk Docker Bundle**<br>• Complete Docker layout (`Dockerfile` + `Dockerrun.aws.json` + `.platform/nginx/conf.d/proxy.conf` for 200MB DPR uploads).<br>• **Exhaustive Help Content** across all 28 modules authored directly in `backend/pmc_lib/help_content_data.py`.<br>• Snapshot API JSON safety wrapper (never emits raw HTML 500s). |
| **[`pmc-frontend-v46r-prod-build.zip`](./pmc-frontend-v46r-prod-build.zip)** | ~2.3 MB | **S3 / CloudFront Production Build**<br>• **Eradicated all raw `fetch` / `process.env.REACT_APP_BACKEND_URL` calls** across `DashboardDrillCards`, `EngagementsPanel`, `ProductCatalogPanel`, `PurchaseGrid`, `PublicRoadmap`, `BillingResult`, `UnspscPicker`, `EscrowOfficerSign`, `MeetingRoom`.<br>• Zero red toast error banners on Admin Dashboard load.<br>• PWA manifest + stale-while-revalidate service worker enabled.<br>• TenderBuilder tab-switch refetch fix. |

---

## 2 · Manuals & Diagrams (v46p/v46r)

| Deliverable | Formats | Size | Description |
|---|---|---|---|
| **Master Training Manual** | [PDF](./PMC_v46p_Master_Training_Manual.pdf) · [DOCX](./PMC_v46p_Master_Training_Manual.docx) | 9.4 MB / 8.2 MB | **151 pages · 82 chapters · 32 retina screenshots**.<br>Sovereign navy cover with gold PMC crest and watermark on every page. |
| **Comprehensive Testing Manual** | [PDF](./PMC_v46p_Testing_Manual.pdf) | 128 KB | **33 pages** of test cases (preconditions, steps, expected UI, expected API/HTTP codes, test data) across all 11 core modules. |
| **Platform Process Flow** | [PDF](./PMC_v46p_Process_Flow.pdf) · [SVG](./PMC_v46p_Process_Flow.svg) | 112 KB / 23 KB | 5 swim-lane lifecycle diagram at A3 landscape. |
| **Platform Data Flow** | [PDF](./PMC_v46p_Data_Flow.pdf) · [SVG](./PMC_v46p_Data_Flow.svg) | 42 KB / 13 KB | 20-node domain architecture diagram at A3 landscape. |

---

## 3 · AWS Deployment Commands

### Backend (Elastic Beanstalk)
```bash
aws elasticbeanstalk create-application-version \
  --application-name pmc-managers-v2 \
  --version-label v46r \
  --source-bundle S3Bucket=<your-eb-bucket>,S3Key=pmc-backend-v46r.zip

aws elasticbeanstalk update-environment \
  --environment-name pmc-backend-prod \
  --version-label v46r
```

### Frontend (S3 + CloudFront)
> ⚠️ **IMPORTANT:** Never use `--delete` at the bucket root as it wipes `/downloads/`.
```bash
unzip pmc-frontend-v46r-prod-build.zip -d ./build
aws s3 sync ./build s3://<your-frontend-bucket>/ \
  --exclude "downloads/*" \
  --cache-control "max-age=31536000, immutable"
aws s3 cp ./build/index.html s3://<your-frontend-bucket>/index.html \
  --cache-control "no-cache"
aws s3 cp ./build/service-worker.js s3://<your-frontend-bucket>/service-worker.js \
  --cache-control "no-cache"
aws s3 cp ./build/manifest.json s3://<your-frontend-bucket>/manifest.json \
  --cache-control "no-cache"
aws cloudfront create-invalidation \
  --distribution-id <your-distribution-id> \
  --paths "/" "/index.html" "/service-worker.js" "/manifest.json" "/static/*"
```
