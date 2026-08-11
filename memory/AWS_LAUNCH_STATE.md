# PMC Managers v2 — AWS Launch State (paused 2026-02-11)

## 🎯 Where you paused

Elastic Beanstalk **environment provisioning in progress**. The Docker container is still being built inside your EC2 instance.

## ✅ What's DONE

| Chapter | Status | Details |
|---|---|---|
| **0. AWS account** | ✅ Done | Account `637423434072`, region `eu-west-2` London |
| **1. IAM user + CLI** | ✅ Done | User `pmc-admin`, ARN `arn:aws:iam::637423434072:user/pmc-admin`, AWS CLI configured on Windows laptop |
| **2. MongoDB Atlas** | ✅ Done | Cluster `pmc-managers-uk` (`pmc-managers-uk.7zsyyyq.mongodb.net`), user `managerspmc_db_user`, **1,149 docs migrated** (all preview data — DocuSign envelopes, products, notices, users, vendors) |
| **3. GitHub push** | ✅ Done | Repo `Treasurescare/pmc-tender-v2-aws`, branch `main_pmcmanagersv2_aws`, includes `Dockerfile` + `.dockerignore` + `Dockerrun.aws.json` |
| **4. Elastic Beanstalk setup** | 🟡 IN PROGRESS | App: `pmc-managers-v2`, Env: `pmc-backend-prod`, Env ID: `e-fp8nem6xeu`, Domain: `pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`, Platform: Docker on 64bit Amazon Linux 2023/4.13.5, Instance: single (t3.micro/small), 20 env vars pasted incl. `MONGO_URL` + 2,240-char `DOCUSIGN_PRIVATE_KEY_B64` |

## ⏸ Last observed state (updated 2026-02-11)

- Previous deploy on t3.micro stalled → OOM during weasyprint install (root cause identified)
- Investor-purge complete: `.emergent` folder removed from Treasurescare/pmc-tender-v2-aws via GitHub web UI
- User has clean ZIP at `C:\Users\abcd\pmcmanagers\pmc-tender-v2-aws-main_pmcmanagersv2_aws.zip`
- Next actions given to user: (1) flatten ZIP if wrapped in top folder, (2) bump EB instance to t3.medium, (3) upload flattened `pmc-backend-eb.zip`, (4) curl /api/v1/meta/health

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
