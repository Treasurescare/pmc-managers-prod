# PMC v46q — Download Manifest

Every file below is served over HTTPS from the deployed frontend at `/downloads/<file>`.

## 1 · Deployment archives (AWS)

| File | Purpose | Size |
|---|---|---|
| [`pmc-backend-v46q.zip`](./pmc-backend-v46q.zip) | Elastic Beanstalk backend bundle — includes the **Help-panel production fix** (manual content now lives inside `backend/pmc_lib/help_content_data.py` so it survives the EB archive) and the reports-snapshot JSON safety wrapper. Upload via `eb deploy` or the EB console. | ~283 KB |
| [`pmc-frontend-v46q-prod-build.zip`](./pmc-frontend-v46q-prod-build.zip) | CloudFront/S3 frontend build. `REACT_APP_BACKEND_URL` was **stripped before build** so all API calls are same-origin. Contains the re-enabled PWA (manifest + stale-while-revalidate service worker), Bug Blitz fixes, TenderBuilder tab-refetch fix. Sync to your S3 bucket, then invalidate CloudFront. | ~2.3 MB |

### AWS deployment steps

Backend (Elastic Beanstalk):

```bash
aws elasticbeanstalk create-application-version \
  --application-name pmc-managers \
  --version-label v46q \
  --source-bundle S3Bucket=<your-eb-bucket>,S3Key=pmc-backend-v46q.zip

aws elasticbeanstalk update-environment \
  --environment-name <your-env> \
  --version-label v46q
```

Frontend (S3 + CloudFront — **never** use `--delete` at the bucket root; it wipes `/downloads/`):

```bash
unzip pmc-frontend-v46q-prod-build.zip -d ./build
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

## 2 · Master Training Manual (151 pages)

| Format | Link | Size |
|---|---|---|
| PDF | [`PMC_v46p_Master_Training_Manual.pdf`](./PMC_v46p_Master_Training_Manual.pdf) | 9.4 MB |
| DOCX | [`PMC_v46p_Master_Training_Manual.docx`](./PMC_v46p_Master_Training_Manual.docx) | 8.2 MB |

151 pages · 82 chapters · 32 full-page screenshots · sovereign navy cover with gold PMC crest and "CONFIDENTIAL — INTERNAL USE ONLY" watermark on every page.

## 3 · Testing Manual (33 pages)

| Format | Link | Size |
|---|---|---|
| PDF | [`PMC_v46p_Testing_Manual.pdf`](./PMC_v46p_Testing_Manual.pdf) | 128 KB |

Per-module test cases with preconditions, steps, expected UI, expected API/HTTP codes, and test-data references. Covers Public / Registration / 5-Portal Login / Notices / Tender Builder / Evaluation / Escrow / Reverse Auctions / Vendor Portal / Reports / PWA.

## 4 · Diagrams

| Diagram | Link | Format |
|---|---|---|
| Process Flow (5-lane lifecycle) | [`PMC_v46p_Process_Flow.pdf`](./PMC_v46p_Process_Flow.pdf) · [`.svg`](./PMC_v46p_Process_Flow.svg) | A3 landscape |
| Data Flow (20-node domain) | [`PMC_v46p_Data_Flow.pdf`](./PMC_v46p_Data_Flow.pdf) · [`.svg`](./PMC_v46p_Data_Flow.svg) | A3 landscape |

## 5 · Deploy README

- [`DEPLOY_v46p_README.md`](./DEPLOY_v46p_README.md) — full context on v46p contents, regenerate commands, and PWA verification.

---

### What v46q adds on top of v46p

1. **Production Help-panel fix** — `manual_content.py` relocated into `backend/pmc_lib/` so the EB archive always carries it. `help_content.py` prefers the in-package copy and falls back to `/scripts/` for local dev. Result: `/api/v1/meta/help` returns all 28 modules in production, no more blank Help tab.
2. **TenderBuilder tab refetch** — clicking Tender / RFP / RFQ / All Kinds now refetches the sidebar with the correct `?kind=` filter (client-side) so masters and drafts no longer leak across kinds.
3. All v46p Bug-Blitz + PWA + manual deliverables are still shipped as-is.
