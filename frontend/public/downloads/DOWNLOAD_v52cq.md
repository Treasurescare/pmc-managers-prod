# PMC Managers · v52cq Release Notes (rev 2 — Docker ready)

**Build date:** 13 Oct 2026
**Rev:** 2 (Dockerfile + .ebextensions + background seeding)

---

## This bundle is for AWS Elastic Beanstalk · Docker on AL2023

### What changed from rev 1 → rev 2
Rev 1 shipped a Dockerfile that broke on EB AL2023 because:
1. The bundled `Dockerrun.aws.json` had `"Image": {"Name": "local"}` — EB tried
   to pull an image literally called `local` and failed with "Command failed
   on all instances". **Fix:** removed `Dockerrun.aws.json` entirely. For a
   Dockerfile build, EB auto-wires the proxy from port 80 → the `EXPOSE`d
   container port using its built-in nginx.
2. Dockerfile healthcheck hit `/api/v1/health` which doesn't exist (that
   path is `/api/v1/meta/health`). **Fix:** healthcheck now hits `/health`
   which is a lightweight probe registered first in `server.py`.
3. Startup event seeded 158k UNSPSC + 150k city rows **synchronously**,
   blocking FastAPI from answering HTTP for 2–3 minutes. EB ALB
   healthchecks timed out → rolled the deploy back. **Fix:** seeding now
   runs as an `asyncio.create_task` background job; the HTTP app is ready
   in <2s, and seeding completes asynchronously within ~3 min (idempotent
   — only runs when collections are empty).
4. Added `.ebextensions/01-healthcheck.config` so EB's ALB target group
   uses `/health` + `200` matcher.

### What's actually inside the zip
```
Dockerfile                     ← python:3.11-slim + gunicorn + uvicorn worker
.dockerignore                  ← keeps .env, .git, zip artifacts out of image
.ebextensions/01-healthcheck.config  ← EB ALB target health path = /health
requirements.txt
server.py                      ← background seeding (v52cr) + /health root probe
routers/                       ← masters_v2, notices, tender_templates, …
scripts/seed_masters.py
data/                          ← UNSPSC v26 SQLite + csc.json (160 MB uncompressed)
… (full backend tree)
```

No `Dockerrun.aws.json` on purpose. If you add one later, use v1 for a
single prebuilt image, not for Dockerfile builds.

---

## Download links

| Bundle | URL | Size |
|---|---|---|
| Backend (Docker) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52cq.zip | ~20 MB zip |
| Frontend | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cq-prod-build.zip | 3.1 MB |

---

## AWS deploy — retry sequence

### Backend → `pmc-backend-prod` (EB Docker AL2023)
1. Download the new `pmc-backend-v52cq.zip` (rev 2).
2. EB console → **Upload and deploy** → pick the zip → next.
3. Confirm the required env vars are still set under **Configuration →
   Updates, monitoring, and logging → Environment properties**:
   - `MONGO_URL` (your MongoDB Atlas / DocumentDB connection string)
   - `DB_NAME` (default `pmc_v2`)
   - `JWT_SECRET`
   - `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`
   - `LLM_API_KEY`
   - `RESEND_API_KEY`
   - `LOCAL_DEV=0`
   - admin + staff seed passwords (see your runbook)
4. Deploy. You should see within ~3 minutes:
   - Events: "Environment update completed successfully"
   - Health: Degraded → **Ok**
   - EB logs: `[bg-bootstrap] seeded masters_unspsc rows=158464` (first boot only)

### Smoke test after it goes green
```bash
API=https://api.YOUR-DOMAIN   # or whatever your EB CNAME is
curl -s $API/health                          # → {"ok":true,"service":"pmc-tender-v2-api",...}
curl -s $API/api/v1/masters/countries | jq 'length'   # → 250 (after bg seed finishes)
curl -s "$API/api/v1/masters/unspsc/public/search?q=biogas&limit=3" | jq .
```

### Frontend → S3 + CloudFront (unchanged from rev 1)
1. Download `pmc-frontend-v52cq-prod-build.zip`.
2. Unzip → `aws s3 sync . s3://YOUR-BUCKET --delete`
3. `aws cloudfront create-invalidation --distribution-id YOUR-ID --paths '/*'`

---

## Troubleshooting

### "Command failed on all instances" after upload
- Check EB **Logs → Request Logs** → `/var/log/eb-engine.log` for the
  Docker build error. Common causes:
  - `MONGO_URL` not set in env → gunicorn exits on startup. Set it and
    redeploy.
  - Instance type too small (t2.micro): the image install step can OOM.
    Scale to `t3.small` (2 vCPU / 2 GB) or larger.

### Deploy green but masters endpoint 404
The background seeder is still running on first boot. Wait ~3 minutes and
retry. Watch `aws elasticbeanstalk request-environment-info` or EB logs
for `[bg-bootstrap] masters bootstrap complete`.

### Preview-as-bidder button doesn't open the amber banner
Ensure CloudFront invalidation finished and your browser isn't serving a
cached pre-v52cq bundle (hard refresh).

---

## Regression footprint
- Pytest: 15/15 (`tests/test_v52cn_masters.py` 11 + `tests/test_v52cp_notices.py` 4).
- Live preview smoke after background-seeding fix: `/health` 200 in <2s,
  `/api/v1/masters/countries` returns 250 immediately (already seeded).
