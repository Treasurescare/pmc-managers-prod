# v46c Delivery Bundle — macOS download guide

Preview URL: `https://tender-hub-57.preview.emergentagent.com`

## One-shot download to your Desktop folder

Paste this into Terminal on your Mac (zsh) — it downloads all three files into `~/Desktop/pmcmanagers/` and verifies the SHA-256 hashes:

```bash
mkdir -p ~/Desktop/pmcmanagers && cd ~/Desktop/pmcmanagers

BASE="https://tender-hub-57.preview.emergentagent.com/downloads"

curl -fSLO "$BASE/pmc-backend-v46c.zip"
curl -fSLO "$BASE/pmc-frontend-v46c-build.zip"
curl -fSLO "$BASE/PMC_Asked_and_Delivered_v46c.md"

echo
echo "== Hashes =="
shasum -a 256 pmc-backend-v46c.zip pmc-frontend-v46c-build.zip
```

Expected SHA-256 (should match exactly):

- `pmc-backend-v46c.zip` — `210268f6eabdbbc0564e6d55cc51680dc2a42e52c98909232c1d1bfbeb51c56d`
- `pmc-frontend-v46c-prod-build.zip` — production build (REACT_APP_BACKEND_URL=https://d2h9tkca2zjofy.cloudfront.net baked in; excludes downloads/ to keep it lean) — `53867b4ba17308ceff57d04fda6308a7bdfd9d41ea4a5a8e04253d20298533ed`
- ~~`pmc-frontend-v46c-build.zip`~~ — SUPERSEDED (had preview URL baked in — do not upload)

## What's in each file

**`pmc-backend-v46c.zip`** — full backend directory (`server.py`, all routers including new `vendor_ratings.py`, updated `auction_live.py` and `billing.py`, models, requirements.txt). Excludes `__pycache__`, `.pytest_cache`, `tests/`, `.venv`.

**`pmc-frontend-v46c-build.zip`** — production build output (`build/index.html`, `build/static/**`). This is what goes into the S3 bucket behind CloudFront distribution `E2WZT1TMQ0EK9W`.

**`PMC_Asked_and_Delivered_v46c.md`** — chronological log of every request you made and exactly what was shipped in response, with verification status per section.

## AWS upload steps (Console-based, matches your usual workflow)

### Backend → Elastic Beanstalk `pmc-backend-prod` (eu-west-2)

1. EB Console → Environments → `pmc-backend-prod`
2. Click **Upload and deploy**
3. Choose file → select `~/Desktop/pmcmanagers/pmc-backend-v46c.zip`
4. Version label: `v46c-<yyyymmdd>` (e.g. `v46c-20260224`)
5. Deploy → wait for health = **Ok**
6. Sanity: `curl -s https://<eb-url>/api/v1/vendor-ratings/public/top?limit=1` should return JSON not HTML

### Frontend → S3 (`www.pmcmanagers.com`)

1. Unzip locally: `cd ~/Desktop/pmcmanagers && unzip -q pmc-frontend-v46c-build.zip`
2. S3 Console → your bucket → **Upload**
3. Add **all files inside `build/`** (drag the contents, not the `build/` folder itself)
4. Under Properties: keep default (public read is already set at bucket level)
5. After upload, invalidate CloudFront cache:
   - CloudFront → distribution `E2WZT1TMQ0EK9W` → Invalidations → **Create invalidation**
   - Path: `/*`
   - Submit
6. Wait ~2 min → hard-refresh `https://www.pmcmanagers.com`

## Rollback safety net

Both EB and S3 keep the previous version. To roll back:
- **EB**: Environments → `pmc-backend-prod` → Application versions → select `v45c-*` → Deploy
- **S3**: If you saved the previous frontend zip (`pmc-frontend-v45-build.zip`) — upload that build folder again and re-invalidate CloudFront

## Optional hardening after this deploy

- Set **`PUBLIC_BASE_URL`** on EB → prevents the Stripe webhook URL from being derived from `request.base_url` (edge case where the ingress host differs from CloudFront)
- Log in to production admin → Auctions → your first draft → Invitations → **Create your standard invitation template** so real bidders get branded emails
- Run one small fee-checkout on production, then **refund** it from the new **Billing & Refunds** tab to confirm production Stripe keys are wired
