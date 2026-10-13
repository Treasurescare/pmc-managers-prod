# PMC Managers · v52cq Release Notes (rev 4 — crash-fast + log diagnostics)

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
