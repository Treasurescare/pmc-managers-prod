# PMC Managers · v52cu Release Bundle

**Date:** 13 Feb 2026
**Builds on:** v52cq (last successful EB deploy — rev 8, docker-compose.yml excluded).

## What's in this release

### Frontend (`pmc-frontend-v52cu-prod-build.zip`, ~3 MB)
- **v52ct — New Notice ↔ Tender Builder bridge finished.** Tender template picker sits above Title; picking a template prefills title, description, **category (full UNSPSC)**, delivery country, budget currency, budget amount AND EMD (fixed + percentage + currency). Category field is a type-to-search UNSPSC picker (`UnspscPicker` wired via `testidPrefix='notice-category'` with a new `category_code` slot in the draft state).
- **v52cu — Landing page shows newly published notices instantly.** `NoticeBoardHome.jsx` now requests `limit=100` so the oldest notice doesn't drop off once the catalogue grows past 30.

### Backend (`pmc-backend-v52cu.zip`, ~20 MB)
- **v52cu — Zero-cache on public landing endpoints.** `GET /api/v1/notices` and `GET /api/v1/meta/public/stats` now return `Cache-Control: no-store, no-cache, must-revalidate` + `Pragma: no-cache` + `Expires: 0`. The moment Publish is clicked the notice appears on the home page (no CloudFront / browser stall).
- **v52ct — Budget validation re-asserted** on `POST /api/v1/notices` (rejects 0 / None / negative with HTTP 422).
- Backfill helper: `scripts/backfill_published_at.py` — idempotent, patches any `is_published=true` row with a null `published_at` to `created_at` so the DESC sort stays deterministic. Run once after deploy:
  ```bash
  eb ssh pmc-backend-prod -c "cd /var/app/current && python -m scripts.backfill_published_at"
  ```
- **Dockerfile unchanged from rev-8**: binds gunicorn to `0.0.0.0:80`, EXPOSE 80, curl present for healthchecks, no docker-compose.yml inside the zip.

### Verified before shipping
- Backend regression suite: `python -m pytest tests/test_v52cp_notices.py` → **7/7 pass**.
- End-to-end preview test (iteration 61): **100% backend, 100% frontend** on all six user acceptance criteria.
- Live curl on preview confirmed `Cache-Control: no-store` on both public endpoints.
- `unzip -l pmc-backend-v52cu.zip | grep docker-compose` → empty (critical rule).

---

## Deploy order

1. **Backend first** (EB Elastic Beanstalk, eu-west-2):
   - Download `pmc-backend-v52cu.zip` from this folder.
   - EB console → `pmc-backend-prod` → **Upload and deploy** → pick the zip → version label `v52cu-YYYYMMDD-HHMM`.
   - Wait for "Environment update completed", then open `https://api.YOUR-DOMAIN/health` — expect `{"ok":true,"service":"pmc-tender-v2-api",...}`.
   - (Optional, recommended) run the backfill once via `eb ssh` (see command above).

2. **Frontend second** (S3 + CloudFront):
   - Download `pmc-frontend-v52cu-prod-build.zip`.
   - Unzip into your S3 origin bucket, then invalidate `/*` on the CloudFront distribution.

3. **Smoke-test production**:
   - Admin → Notices → **New notice**. Confirm Tender template field is above Title; category is a search box; select any template and verify title/description/category/country/budget/EMD all pre-fill.
   - Publish a notice. Open the landing page in an incognito window within 2 seconds — the notice should already be at the top of "All published tender notices".

---

## Required EB environment variables (unchanged from v52cq)

Same as rev 8. If you kept them, nothing to touch:
- `ADMIN_PASSWORD`, `OWNER_PASSWORD` — hard required.
- `PMC_SEED_PASSWORDS` (or individual `STAFF_PW_*`) — soft, fall back to demo values.
- `MONGO_URL`, `JWT_SECRET`, `DOCUSIGN_*`, `STRIPE_*`, `EMERGENT_LLM_KEY`, `RESEND_API_KEY`, etc. — same as before.
- `PMC_SSM_PREFIX=/pmc/prod/` if you're loading secrets from SSM Parameter Store.

---

## Known follow-ups (not blocking this release)

- Zero-EMD bid progression needs one real production bid to confirm the local patch holds.
- Production document-viewer defect still awaits a reproduction with record / slot / screenshot.
- Escrow account-change error still awaits exact error text + action path.
