# PMC Managers · v52cq Release Notes (rev 4 — crash-fast + log diagnostics)
## v52cq rev 6 — SSM Parameter Store loader (13 Oct 2026)

EB's 4,096-byte plaintext env cap cannot hold this app's secret set
(DOCUSIGN_PRIVATE_KEY_B64 alone is ~1.6 KB). `config.py` now loads secrets
from AWS SSM Parameter Store at boot when `PMC_SSM_PREFIX` is set:

- Fetches every parameter under the prefix (recursive, WithDecryption).
- Injects them into the process env; **existing EB env vars always win**.
- Requires only `boto3` (already in requirements) and the EB instance role.

### Setup (one-time, ~10 min)

1. **Systems Manager → Parameter Store → Create parameter**, one per big
   secret, Type = **SecureString**, Tier = Standard (free ≤ 4 KB each):
   ```
   /pmc/prod/DOCUSIGN_PRIVATE_KEY_B64
   /pmc/prod/DOCUSIGN_CONNECT_HMAC_SECRET
   /pmc/prod/VAPID_PRIVATE_KEY
   /pmc/prod/VAPID_PUBLIC_KEY
   /pmc/prod/ZOOM_ACCOUNT_ID
   /pmc/prod/ZOOM_CLIENT_ID
   /pmc/prod/ZOOM_CLIENT_SECRET
   /pmc/prod/STRIPE_API_KEY
   /pmc/prod/STRIPE_WEBHOOK_SECRET
   /pmc/prod/EMERGENT_EMAIL_KEY
   /pmc/prod/EMERGENT_LLM_KEY
   /pmc/prod/RESEND_API_KEY
   /pmc/prod/MONGO_URL
   /pmc/prod/JWT_SECRET
   /pmc/prod/PMC_SEED_PASSWORDS      ← all 7 seed passwords in one string
   ```
2. **IAM → Roles → aws-elasticbeanstalk-ec2-role → Add permissions →
   Create inline policy**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
       "Resource": "arn:aws:ssm:eu-west-2:637423434072:parameter/pmc/prod/*"
     }]
   }
   ```
3. **EB env properties** — delete everything you moved to SSM and keep only
   these small ones inline (well under 4 KB):
   ```
   PMC_SSM_PREFIX   = /pmc/prod
   LOCAL_DEV        = 0
   DB_NAME          = pmc_tender_db
   FRONTEND_URL     = https://www.pmcmanagers.com
   CORS_ORIGINS     = https://www.pmcmanagers.com,https://pmcmanagers.com
   EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME, STRIPE_TAX_MODE, DOCUSIGN_ENV,
   DOCUSIGN_AUTH_HOST, DOCUSIGN_BASE_URI, DOCUSIGN_ACCOUNT_ID,
   DOCUSIGN_USER_ID, DOCUSIGN_INTEGRATION_KEY, OWNER_EMAIL, VAPID_CLAIM_EMAIL
   ```
   Also delete the duplicate individual `ADMIN_PASSWORD` / `OWNER_PASSWORD`
   keys — the `PMC_SEED_PASSWORDS` blob covers them.
4. Save (fits now) → Apply → **Upload and deploy the rev-6 zip**.

Boot log confirms success:
`[PMC-SSM] loaded 15 params from /pmc/prod: [...]`

If IAM permissions are missing you'll see `[PMC-SSM] ... fetch failed
(UnauthorizedOperation)` and the app falls back to env properties only.

---


## v52cq rev 5 — EB 4,096-byte env-properties cap workaround (13 Oct 2026)

EB refused to save the 7 individual seed-password env keys (4,185 / 4,096
bytes used). `config.py::_seed_password` now also reads a single
consolidated `PMC_SEED_PASSWORDS` var (`KEY=value;KEY=value;…`, keep
passwords alphanumeric — avoid `; , =`). Individual keys still take
priority. Verified: all 5 staff + owner resolve from the blob; missing
keys still trigger the intentional SEC-004 fatal.

Also removed `.ebextensions/02-log-env-keys.config` (diagnostic var no
longer needed — root cause was found via logs) so it stops consuming a
property slot; user should delete `PMC_LOG_ENV_KEYS_ON_BOOT` from EB
console to reclaim ~30 bytes.

---



**Build date:** 13 Oct 2026
**Rev:** 4

---

## Status after rev 3

- Container built and ran successfully.
- Deploy completes in ~2 min (no more rollback).
- **BUT**: ELB health = Severe, "50.0 % of the requests to the ELB are
  failing with HTTP 5xx". That exact 50 % number for several minutes
  running is the fingerprint of a **mixed fleet** — the EB auto-scaling
  group has two instances and one of them is still running an older
  broken version while the other is on rev 3.

## What rev 4 adds (diagnostic + crash-fast)

| Change | Why |
|---|---|
| `gunicorn --preload` + exec form (no `sh -c`) | Any import error now crashes the master instantly with a visible Python traceback in `/var/log/eb-docker/containers/eb-current-app/*.stdouterr.log` instead of being masked. |
| Explicit `--access-logfile -` + `--error-logfile -` + `--capture-output` | gunicorn request logs now reach EB's container log collector, so you can see every 5xx. |
| New `.ebextensions/02-log-env-keys.config` | On container boot the app dumps the NAMES (not values) of its 10 critical env vars so you can confirm `MONGO_URL`, `JWT_SECRET`, etc. actually reached the container. |
| Healthcheck interval 20 s / start-period 45 s | Container has a bit more grace while cold-starting; after that it's a hard pass/fail. |

Nothing else changed functionally. v52cp/v52cq app features (Preview as
bidder, Tender → Notice bridge, EMD + Country on public cards, etc.) are
all unchanged.

---

## Download

| | |
|---|---|
| Backend (Docker rev 4) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52cq.zip |
| Frontend | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cq-prod-build.zip |

---

## 🛠️ Deploy + diagnose plan

### Step 1 — deploy rev 4
Upload the new zip via EB → Upload and deploy.

### Step 2 — force a clean fleet
Rev 4 should rebuild both instances, but if the 50 % 5xx persists past
5 min:

- EB console → `pmc-backend-prod` → **Actions → Rebuild environment**

Rebuild terminates every EC2 instance and creates fresh ones from the
latest application version. This is the surest way to kill a stale
instance that's stuck on a prior broken revision.

### Step 3 — fetch container logs (this is where the real answer is)
EB console → `pmc-backend-prod` → left sidebar **Logs** → **Request logs
→ Last 100 lines** → wait ~10 s → **Download**.

Inside the tarball look at these two files:

- `var/log/eb-docker/containers/eb-current-app/eb-stdouterr.log`
  - gunicorn startup banner. Should look like:
    ```
    [INFO] Starting gunicorn 23.x
    [INFO] Listening at: http://0.0.0.0:80
    [INFO] Using worker: uvicorn.workers.UvicornWorker
    [bootstrap-env] set: ['MONGO_URL', 'DB_NAME', 'JWT_SECRET', ...]
    [INFO] Booting worker with pid: 7
    [INFO] Booting worker with pid: 8
    ```
  - If `[bootstrap-env] MISSING: [...]` appears, that env var is NOT set
    on EB and must be added under EB → Configuration → Environment
    properties.
  - If you see a Python traceback instead of "Listening at", the master
    crashed on import. Paste the last 30 lines back to me and I'll fix
    it instantly.

- `var/log/eb-engine.log`
  - EB platform engine. Look for `Successfully built`, `docker run`,
    `Docker container running` lines. If you see `Error: ...` in this
    file, that's a Docker build / image problem.

### Step 4 — if logs show the app is fine but ELB still 5xx

That means the ALB target group is misconfigured. Fix:

- EB → `pmc-backend-prod` → **Configuration → Load balancer → Edit**
- Scroll to **Processes** → `default` → **Edit**
- Confirm:
  - Port = **80**
  - Protocol = HTTP
  - Health check path = **/health**
  - Matcher = **200**
  - Healthy threshold = 2, Unhealthy threshold = 5, Interval = 15 s

Save, then **Apply**. EB will update the ALB target group in ~1 min.

---

## Env vars checklist (must be set under EB → Configuration → Environment properties)

⚠️ **CONFIRMED ROOT CAUSE from your eb-engine.log (rev 4):**
`[PMC-STARTUP-FATAL] Required environment variable 'ADMIN_PASSWORD' is
missing or empty` — gunicorn workers exited with code 1 in a loop, which
is the 50 % 5xx you saw. The app intentionally refuses to boot without
real seed passwords (SEC-004 hardening from v52cj — it must NOT be
weakened). Set ALL of the following, then **Apply**:

| Variable | Required | Notes |
|---|---|---|
| `MONGO_URL` | **yes** | Full mongodb+srv:// string. |
| `DB_NAME` | **yes** | e.g. `pmc_v2` |
| `JWT_SECRET` | **yes** | long random string |
| `ADMIN_PASSWORD` | **yes — was missing** | Master admin seed password. Choose a strong one. |
| `OWNER_PASSWORD` | **yes** | Second owner seed password (kannan@emeraldcorporates.com). |
| `STAFF_PW_ESCROW` | **yes** | escrow@pmcmanagers.com |
| `STAFF_PW_CERTIFIER` | **yes** | certifier@pmcmanagers.com |
| `STAFF_PW_LEGAL` | **yes** | legal@pmcmanagers.com |
| `STAFF_PW_ACCOUNTS` | **yes** | accounts@pmcmanagers.com |
| `STAFF_PW_COMMITTEE` | **yes** | committee@pmcmanagers.com |
| `STRIPE_API_KEY` | prod-only | required for EMD + billing |
| `STRIPE_WEBHOOK_SECRET` | prod-only | required for live Stripe events |
| `LLM_API_KEY` | optional | Emergent universal key |
| `RESEND_API_KEY` | optional | emails |
| `LOCAL_DEV` | **set to `0`** | production flag |
| `FRONTEND_URL` | yes | https://www.pmcmanagers.com |
| `CORS_ORIGINS` | yes | e.g. `https://www.pmcmanagers.com,https://pmcmanagers.com` |

Setting these on EB Console → Configuration → Software → Environment
properties → **Apply** restarts the container with the vars injected; the
boot log will then show `[bootstrap-env] MISSING (expected): []` and
gunicorn workers stay up.

---

## Why this will finally go green

- Rev 4 crashes loudly on bad imports so a hidden Python error can't
  silently keep returning 5xx.
- Rev 4 dumps missing env vars at boot so you can diagnose config gaps.
- The Rebuild environment step kills stale instances so the "exact 50 %"
  mixed-fleet pattern disappears for good.
