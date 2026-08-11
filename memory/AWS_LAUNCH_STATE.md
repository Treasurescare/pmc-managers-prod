# PMC Managers v2 — AWS Launch State (updated 2026-02-11 14:25 UTC)

## 🎯 Where you paused

🎉 **Backend + Frontend both LIVE on AWS.**
- Backend: `http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com` (EB + Docker + Atlas)
- Frontend: `https://d2h9tkca2zjofy.cloudfront.net` (S3 + CloudFront + WAF, Free plan)

## ✅ What's DONE

| Chapter | Status | Details |
|---|---|---|
| 0. AWS account | ✅ | Account `637423434072`, region `eu-west-2` |
| 1. IAM + CLI | ✅ | `pmc-admin`, AWS CLI configured |
| 2. MongoDB Atlas | ✅ | `pmc-managers-uk` cluster, 1,149 docs migrated |
| 3. GitHub | ✅ | `Treasurescare/pmc-tender-v2-aws`, `.emergent/` purged |
| 4. Elastic Beanstalk | ✅ | `pmc-backend-prod` on t3.medium, v8-deps-fixed live |
| 5. Frontend S3+CloudFront | ✅ | Bucket `pmc-managers-frontend-prod`, distribution `d2h9tkca2zjofy.cloudfront.net`, Free plan with WAF |

## 🔧 Fixes applied in this session to get backend LIVE

1. Purged `.emergent/` from GitHub repo (was tracked, showed in every ZIP)
2. Renamed EB env var `EMERGENT_LLM_KEY` → `LLM_API_KEY` (code reads the new name via `pmc_lib`)
3. Bumped EB instance from t3.micro → **t3.medium** (t3.micro OOMed during weasyprint pip install)
4. Fixed ZIP structure — replaced `Compress-Archive` (which writes backslash entries on PS 5.1) with manual `ZipArchive.CreateEntry` + `.Replace('\\','/')` for Linux-compatible forward-slash paths
5. Added missing pip deps to `backend/requirements.txt`: `docusign-esign==6.1.0`, `bleach==6.2.0`, `Markdown==3.10.3`

## ⏭ Next chapter — Chapter 5: Frontend → S3 + CloudFront

- Frontend location: `C:\Users\abcd\pmcmanagers\_check\pmc-tender-v2-aws-main_pmcmanagersv2_aws\frontend\`
- Backend URL to bake into frontend env: `http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`
- S3 bucket to create: `pmc-managers-frontend-prod` in `eu-west-2`
- CloudFront distribution: origin=that bucket, default root = `index.html`, custom error pages for SPA routing (403/404 → `/index.html` with HTTP 200)

## 🔐 Reference — credential snapshot

- AWS Console user (root): via account 637423434072
- AWS IAM user (daily): `pmc-admin`
- PMC admin login on production backend: `adminsupport@pmcmanagers.com` / `Adminsupport@2024` (⚠️ weak — rotate)
- MongoDB Atlas: `managerspmc_db_user` / `ZzO8YoEqAQlrXqa5`
- DocuSign HMAC: `KFSC1ftZ0DzyvFu9hmWdA27YFoCsYtRrKitbCvV6VEs=`

## ⚠️ Post-launch to-dos

- Rotate weak admin password `Admin@123` (previously wrongly recorded as `Adminsupport@2024` — corrected 2026-02-11)
- Replace `STRIPE_API_KEY` placeholder `sk_test_emergent` with a real Stripe test key before enabling billing
- Save-to-GitHub the updated `backend/requirements.txt` so future ZIPs include the deps
- Update DocuSign Connect webhook URL when custom domain goes live (Chapter 6)

## 🧩 CloudFront routing decision (2026-02-11 14:35 UTC)

Because backend on EB is `http://` and frontend on CloudFront is `https://`, browsers block mixed-content requests. Chosen fix: **add a second origin + `/api/*` behavior to the existing frontend CloudFront distribution** so both apps share the same HTTPS domain. This eliminates CORS entirely (same-origin) and gives us HTTPS end-to-end without touching custom domain / ACM yet.

- Frontend rebuilt with `REACT_APP_BACKEND_URL=https://d2h9tkca2zjofy.cloudfront.net`
- CloudFront distribution `E2WZT1TMQ0EK9W`:
  - Origin 1 (existing): S3 bucket `pmc-managers-frontend-prod`
  - Origin 2 (new): EB `pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com` on HTTP-only
  - Behavior 1 (default `*`): S3
  - Behavior 2 (`/api/*`): EB, forward all headers/cookies/query, no cache

## 🔄 RESUME HERE when you return

### First action (30 sec)
Log back into AWS Console → **Elastic Beanstalk** → **Environments** → click **`pmc-backend-prod`**

### Check health
| If Health shows... | Do this... |
|---|---|
| 🟢 **Ok** (green) | 🎉 We're deployed. Reply "Health Ok" — I'll smoke-test the URL and move to Chapter 5 (frontend on S3) |
| 🟡 **Info/Warning** | Wait 2 more min then refresh |
| 🔴 **Severe/Degraded** | Click **Events** tab → screenshot last 10 rows OR click **Logs → Request logs → Full logs** → paste the log URL contents |
| ⚫ **Pending still** (after 20 min) | Same as Severe — grab logs |

### Backend URL to remember
```
http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com
```
Test with:
```
curl http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com/api/v1/meta/health
```
Should return `{"ok": true, ...}` when live.

## ⏭ Remaining chapters (after backend is green)

- **Chapter 5** — Frontend build → S3 upload → CloudFront CDN (25 min)
- **Chapter 6** — Custom domain `www.pmcmanagers.com` + SSL via Route 53 + ACM (20 min)
- **Post-launch** — update DocuSign Connect webhook URL from preview to `https://api.pmcmanagers.com/api/v1/docusign/webhook`
- **Ongoing sync workflow** — you continue coding in Emergent, click "Save to GitHub" whenever ready, then run `yarn build && aws s3 sync ...` on Windows laptop to push frontend updates (docs in earlier chat)

## 🔐 Reference — credential snapshot (encrypted-at-rest in Atlas, AWS Secrets)

- AWS Console user (root): via account 637423434072
- AWS IAM user (daily): `pmc-admin`
- PMC admin login on production backend: `adminsupport@pmcmanagers.com` / `Adminsupport@2024` (⚠️ weak — rotate)
- MongoDB Atlas: `managerspmc_db_user` / `ZzO8YoEqAQlrXqa5`
- DocuSign HMAC: `KFSC1ftZ0DzyvFu9hmWdA27YFoCsYtRrKitbCvV6VEs=`
- DocuSign key base64: `/app/DOCUSIGN_PRIVATE_KEY_B64.txt` in Emergent codebase
- All env vars for AWS: `/app/AWS_ENV_VARS.txt` in Emergent codebase

## 🧠 Design decisions locked in (don't re-litigate)

- Backend hosting: **Elastic Beanstalk** with Docker platform (App Runner was our first choice but got deprecated to new customers Feb 2026)
- Region: **eu-west-2 (London)** — closest for UK/Kazakhstan users
- Instance: **Single instance** (cheaper for launch, we can flip to Load Balanced later)
- Frontend: **S3 + CloudFront** (Chapter 5 pending)
- Domain: `www.pmcmanagers.com` via Route 53 (Chapter 6)
- Database: MongoDB Atlas free M0 (upgrade to M10 when live traffic)
- DocuSign private key delivered via base64 env var (`DOCUSIGN_PRIVATE_KEY_B64`), NOT file mount — cleaner for containers
- Toast/UI: bottom-right (top-right blocked avatar)
- Investor-clean: All "Made with Emergent" scripts removed from index.html; PostHog to `ap.emergent.sh` will disappear automatically once served from AWS instead of Emergent preview
- Internal-strategy docs moved OUT of public downloads folder to `/app/docs/internal-strategy/` (BA_Gap_Analysis.md etc.)

## 💰 Cost so far

Nothing yet — EB just spun up. Expect $15-25/month total once fully live.
