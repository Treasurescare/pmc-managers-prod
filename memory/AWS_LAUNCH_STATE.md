# PMC Managers v2 — AWS Launch State (updated 2026-02-12 06:24 UTC)

## 🎯 Where you paused — 2026-02-12

🎉 **CUSTOM DOMAIN LIVE.** `https://www.pmcmanagers.com` serves the full stack over HTTPS. Apex `pmcmanagers.com` 301-redirects to www. CORS validated. Admin login verified via custom domain.

## ✅ COMPLETED

| Chapter | Status | Details |
|---|---|---|
| 0-5 | ✅ | Full AWS stack live end-to-end since 2026-02-11. |
| 6. **Custom Domain** | ✅ **DONE (2026-02-12)** | ACM cert `f9755627-05ac-4dc6-b4ab-5751ddd4f5e8` in us-east-1 covers `www` + apex · GoDaddy CNAME `www → d2h9tkca2zjofy.cloudfront.net` · GoDaddy Domain Forwarding apex → `https://www.pmcmanagers.com` (301, forward-only) · CloudFront alt CNAMEs + cert attached · EB env vars `FRONTEND_URL` + `CORS_ORIGINS` updated |

## 🔴 REMAINING for full launch polish

| Priority | Task | ETA |
|---|---|---|
| 🟠 P1 | **DocuSign Connect webhook** URL update to `https://www.pmcmanagers.com/api/v1/docusign/webhook` | 5 min |
| 🟠 P1 | **Nuclear git reset** — fresh `pmc-managers-prod` GitHub repo | 15 min |
| 🟡 P2 | **Save-to-GitHub** yesterday+today workspace changes | 2 min |
| 🟡 P2 | **Rotate `Admin@123`** before demo | 5 min |
| 🟡 P2 | Real Stripe key (waiting on user) | 5 min |
| 🟢 P3 | Frontend v3 rebuild (cosmetic; old URL still works) | 5 min |
| 🟢 P3 | UNSPSC picker → BOQ + Vendor Reg Section C | 30 min |

## 🌐 Live URLs

- **Primary app**: `https://www.pmcmanagers.com`
- **Apex redirect**: `https://pmcmanagers.com` → 301 → www
- **Fallback CloudFront default (still live)**: `https://d2h9tkca2zjofy.cloudfront.net`
- **Health**: `GET https://www.pmcmanagers.com/api/v1/meta/health` → 200
- **Backend origin (private, only via CloudFront)**: `http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`
- **CloudFront distribution**: `E2WZT1TMQ0EK9W`

## 🔐 Reference — credential snapshot

- AWS root: 637423434072 · region: eu-west-2 (CF cert region: us-east-1)
- IAM daily user: `pmc-admin`
- **PMC admin (verified via www.pmcmanagers.com)**: `adminsupport@pmcmanagers.com` / `Admin@123` ⚠️ rotate before demo
- MongoDB Atlas: `managerspmc_db_user` / `ZzO8YoEqAQlrXqa5`
- DocuSign HMAC: `KFSC1ftZ0DzyvFu9hmWdA27YFoCsYtRrKitbCvV6VEs=`

## 🔄 RESUME TOMORROW — pick up in this order

1. **Chapter 6 — Custom domain `www.pmcmanagers.com`** → step-by-step already written for you in **`/app/memory/CHAPTER_6_DOMAIN_KIT.md`** (Route 53 + ACM in us-east-1 + attach to CloudFront distribution `E2WZT1TMQ0EK9W`). Prereq: own the `pmcmanagers.com` domain at a registrar.
2. **Comprehensive Testing Kit** → **`/app/docs/reports/PMC-v2-Testing-Kit.md`** created. Contains all creds, 55 test scenarios, smoke-test curls. Print alongside the testing flowchart PDF (still to be generated — 5-min task tomorrow).
3. **NEW Testing Flowchart** — code lives in `/app/backend/routers/_testing_flowchart.py` (55-scenario swim-lane SVG) and endpoints registered in `reports.py` at `/api/v1/reports/testing-flowchart.svg|.pdf`. Backend HOT-RELOADED it. Tomorrow: hit `POST /api/v1/reports/snapshot` from admin to persist SVG+PDF to `/app/docs/reports/`, then include the two new files in the next frontend rebuild + S3 sync.
4. **g — Asked-vs-Delivered docs** already regenerated fresh at `/app/docs/reports/PMC-v2-Asked-vs-Delivered.{pdf,docx,xlsx}` (15:25). Copied into `/app/frontend/public/downloads/` — will ship in next frontend rebuild.
5. **d — Nuclear git reset** to a fresh `pmc-managers-prod` repo — do after Chapter 6 completes so the new repo captures the finished config.
6. **e — Save-to-GitHub** (from Emergent chat input) to sync `backend/requirements.txt` (now has `docusign-esign`, `bleach`, `Markdown`) and the new `_testing_flowchart.py` + Chapter 6 kit + Testing Kit.
7. **f — Smoke-test the demo flows** using the Testing Kit (5-min curl set + browser scenario 1-5).

## 📝 Files created / updated this session (ready to Save-to-GitHub tomorrow)

- ✅ `backend/requirements.txt` — added `docusign-esign==6.1.0`, `bleach==6.2.0`, `Markdown==3.10.3`
- ✅ `backend/routers/_testing_flowchart.py` — NEW (55-scenario testing flowchart SVG generator)
- ✅ `backend/routers/reports.py` — added `/testing-flowchart.svg|.pdf` endpoints
- ✅ `docs/reports/PMC-v2-Testing-Kit.md` — NEW (comprehensive QA testing kit)
- ✅ `memory/CHAPTER_6_DOMAIN_KIT.md` — NEW (Route 53 + ACM step-by-step)
- ✅ `memory/AWS_LAUNCH_STATE.md` — updated (this file)
- ✅ `memory/PRD.md` — updated (AWS marked LIVE)
- ✅ `memory/test_credentials.md` — corrected admin password (`Admin@123`, verified working on prod)
- ✅ `frontend/public/downloads/` — added 7 fresh SoT docs (Asked-vs-Delivered + Platform Flowchart + User-Guide Flowchart)

## ✅ What's DONE

| Chapter | Status | Details |
|---|---|---|
| 0. AWS account | ✅ | Account `637423434072`, region `eu-west-2` |
| 1. IAM + CLI | ✅ | `pmc-admin`, AWS CLI configured |
| 2. MongoDB Atlas | ✅ | `pmc-managers-uk` cluster, 1,149 docs migrated |
| 3. GitHub | ✅ | `Treasurescare/pmc-tender-v2-aws`, `.emergent/` purged |
| 4. Elastic Beanstalk | ✅ | `pmc-backend-prod` on t3.medium, v8-deps-fixed live |
| 5. Frontend S3+CloudFront | ✅ | Bucket `pmc-managers-frontend-prod`, distribution `E2WZT1TMQ0EK9W` (`d2h9tkca2zjofy.cloudfront.net`), Free plan with WAF, single-origin routing |
| 5b. Single-origin routing | ✅ | Added EB as 2nd origin (`pmc-eb-backend`) + `/api/*` behavior with `CachingDisabled` + `AllViewer` origin request policy |
| 5c. End-to-end verification | ✅ | Admin login `adminsupport@pmcmanagers.com` / `Admin@123` returns 200 through CloudFront |

## ⏭ REMAINING for full launch

| Priority | Task | ETA |
|---|---|---|
| 🟠 P1 | **Chapter 6 — Custom domain** `www.pmcmanagers.com` via Route 53 + ACM cert (us-east-1 for CloudFront). Then update DocuSign Connect webhook URL. | 30-45 min |
| 🟠 P1 | Nuclear git reset — create fresh `pmc-managers-prod` repo, push scrubbed code as first commit | 15 min |
| 🟡 P2 | Save-to-GitHub the fixed `backend/requirements.txt` (docusign-esign, bleach, Markdown) so future ZIPs include them | 2 min |
| 🟡 P2 | Rotate `Admin@123` → strong password before investor demo | 5 min |
| 🟡 P2 | Replace `STRIPE_API_KEY=sk_test_emergent` placeholder with real Stripe test key | 5 min |
| 🟢 P3 | Attach UNSPSC picker to BOQ Builder + Vendor Registration Section C (deferred from before AWS pivot) | 30 min |

## 🌐 Live URLs

- **App**: `https://d2h9tkca2zjofy.cloudfront.net`
- **Health check**: `https://d2h9tkca2zjofy.cloudfront.net/api/v1/meta/health` → `{"ok":true,...}`
- **Backend origin** (internal): `http://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`
- **CloudFront distribution ID**: `E2WZT1TMQ0EK9W`

## 🔐 Reference — credential snapshot

- AWS account root: 637423434072
- IAM daily user: `pmc-admin`
- **PMC admin (verified working)**: `adminsupport@pmcmanagers.com` / **`Admin@123`** ⚠️ rotate before demo
- MongoDB Atlas: `managerspmc_db_user` / `ZzO8YoEqAQlrXqa5`
- DocuSign HMAC: `KFSC1ftZ0DzyvFu9hmWdA27YFoCsYtRrKitbCvV6VEs=`

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
