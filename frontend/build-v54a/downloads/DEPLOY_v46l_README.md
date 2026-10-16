# PMC Managers — Deploy v46l (Unlimited DPR + Async Worker)

## What's new versus v46j / v46k

| Concern | v46j / v46k | **v46l** |
|---|---|---|
| Ingested text ceiling | 800 KB (20 chunks × 40 KB) | **Unlimited** (500-chunk safety, ≈ 20 MB / 5 000 pages) |
| Per-file upload cap | 15 MB | **100 MB** |
| Sync request path | Only path — times out on 60 s idle | Still available for small DPRs |
| Long-running analysis | ❌ hits nginx timeout | ✅ `/dpr/analyze-async` + polling |
| Sections capped | 30 | 60 |
| nginx body / idle | 25 MB / 60 s | **200 MB / 300 s** |
| Progress feedback | None | Real-time % + phase (`mapping 6/14`, `drafting 22/58`, …) |

## Backend changes (`pmc-backend-v46l.zip`)

- `backend/routers/tender_pro.py`:
  - `MAX_CHUNKS = 500` (was 20); overridable via `DPR_MAX_CHUNKS` env.
  - `_run_dpr_analyze(..., progress_cb=None)` — the map-reduce writes progress at every phase.
  - New endpoints:
    - `POST /api/v1/tender-pro/dpr/analyze-async` → returns `{job_id}` immediately.
    - `GET  /api/v1/tender-pro/dpr/jobs/{job_id}` → `{status, progress, phase, result, error}`.
  - Payload cap raised to 140 MB base64 (~100 MB decoded).
- `.platform/nginx/conf.d/proxy.conf`:
  - `client_max_body_size 200M`, all timeouts raised to `300s`.
- Emergent LLM path unchanged.

## Frontend changes (`pmc-frontend-v46l-prod-build.zip`)

- `DprGenerateModal.jsx` now decides sync vs. async per file:
  - `< 4 MB` → existing sync request.
  - `>= 4 MB` → async endpoint, polls every 3 s, renders a live progress bar + phase caption for each file.
- Copy: "max 15 MB each" → **"max 100 MB each"**; each queued file shows its MB size + a "Background" chip when it will use the async path.

## Deploy

```bash
# Backend
eb deploy --staged --label v46l

# Frontend (non-destructive!)
unzip pmc-frontend-v46l-prod-build.zip -d ./v46l-build
aws s3 sync ./v46l-build/ s3://pmc-managers-frontend-prod/ \
  --exact-timestamps --exclude "downloads/*"
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

## Post-deploy validation

1. Log in as admin, open Tender Builder → Generate from DPR.
2. Upload a **large DPR** (≥ 20 MB or 500+ pages).
3. Expect a "Background" chip on the file card; progress bar advances through *reading upload → extracted N chars → mapping k/M chunks → drafting j/S sections → complete*.
4. When it completes the section count should exceed 30 for a 500-page tender.
5. `GET /api/v1/tender-pro/dpr/jobs/<id>` returns the same JSON as the sync analyzer, so the "Create AI-drafted tender" button behaves identically after that.
