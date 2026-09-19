# PMC Managers v2 — AWS Deployment Kit (v40 + v22f)

**Prepared 2026-09-19**
**Bundles cumulative fixes:** Batch #9 (11 tracker items) + #9b (committee dissolve CSRF) + #9c (escrow same-email governance) + #9d (loud error toasts)

---

## 📦 What's in this folder

| File | Purpose |
|---|---|
| `pmc-frontend-v40-build.zip` | Frontend build (2.0 MB) — `main.727b5a39.js` |
| `pmc-backend-v22f.zip` | Backend source (240 KB) — Batches #9 + #9c |
| `deploy-frontend-v40.sh` | One-shot S3 sync + CloudFront invalidate |
| `deploy-backend-v22f.sh` | One-shot EB application-version create + update-environment |
| `verify_prod_v40.sh` | 8-check smoke test after deploy |
| `PMC_Bug_Tracker_v13_20260919.xlsx` | Bug tracker current state |

---

## ✅ Verified locally on preview

- `main.727b5a39.js` compiles cleanly
- `Cache-Control: no-store` on `/api/v1/admin/auth/me` (Bug #29)
- Rubric `weight=2` → HTTP 422 with clear message (Bug #49)
- Rubric `minimum_technical=150` → HTTP 422 (Bug #49)
- Escrow `sign` on same-email account → HTTP 409 with full remediation text
- Escrow `list_accounts` returns `governance_summary: {ok, broken}` + per-account `governance_ok` flag
- Committee dissolve now sends CSRF → HTTP 200 (Bug #9b)
- Deep-link `/admin?tab=evaluation` lands on Evaluation tab (Bug #63)
- Notices Publish checkbox enabled for master admin (case-insensitive role check, Bug #21)

---

## 🚀 Deploy — 3 commands from any machine with AWS CLI

Prerequisite: AWS CLI configured with the `pmc-admin` profile in `~/.aws/credentials`.

```bash
# 0. Change into the delivery folder
cd /path/to/deliverables/

# 1. Frontend  (60-90s upload + 1-3 min CloudFront invalidation)
bash deploy-frontend-v40.sh

# 2. Backend   (upload → EB register → environment update; 3-6 min end-to-end)
bash deploy-backend-v22f.sh

# 3. Verify   (8 checks against https://www.pmcmanagers.com)
bash verify_prod_v40.sh
```

That's it. Each script is idempotent — safe to re-run.

---

## 🔧 Override defaults (if your AWS names differ)

Each script honours env vars. Example:

```bash
AWS_PROFILE=default AWS_REGION=eu-west-2 \
S3_BUCKET=pmc-managers-frontend-prod \
CLOUDFRONT_ID=E2WZT1TMQ0EK9W \
bash deploy-frontend-v40.sh

EB_APP=pmc-backend-prod EB_ENV=pmc-backend-prod \
S3_ARTIFACTS_BUCKET=elasticbeanstalk-eu-west-2-637423434072 \
bash deploy-backend-v22f.sh
```

Defaults are taken from `/app/memory/AWS_LAUNCH_STATE.md`.

---

## 🔍 What each script does (transparent — no magic)

### `deploy-frontend-v40.sh`
1. Unzips `pmc-frontend-v40-build.zip` into `./.deploy-v40/`
2. `aws s3 sync .../static/ s3://pmc-managers-frontend-prod/static/ --delete --cache-control "public, max-age=31536000, immutable"`
3. `aws s3 sync ./ s3://.../ --exclude "static/*" --cache-control "public, max-age=0, must-revalidate"`
4. `aws cloudfront create-invalidation --distribution-id E2WZT1TMQ0EK9W --paths "/" "/index.html" "/asset-manifest.json" "/manifest.json"`

### `deploy-backend-v22f.sh`
1. Uploads the zip to `s3://elasticbeanstalk-eu-west-2-637423434072/artifacts/pmc-backend/v22f-<timestamp>.zip`
2. `aws elasticbeanstalk create-application-version --application-name pmc-backend-prod --version-label v22f-<ts>`
3. `aws elasticbeanstalk update-environment --environment-name pmc-backend-prod --version-label v22f-<ts>`

### `verify_prod_v40.sh` — 8 checks
1. Apex `pmcmanagers.com` returns 301 to `www`
2. `https://www.pmcmanagers.com/` index references `main.727b5a39.js`
3. New `main.js` loads with `Content-Type: application/javascript`
4. Backend health = 200 via same-origin `/api/v1/meta/health`
5. `/api/v1/admin/auth/me` emits `Cache-Control: no-store` (Bug #29)
6. Rubric endpoint reachable (auth-required)
7. Escrow accounts endpoint reachable (auth-required)
8. Apex redirect chain resolves cleanly to www

---

## ⚠️ Post-deploy action for production escrow account

Preview + production both have a legacy joint account **`PMC-KZ EMD Escrow #1`** with the SAME email on both PMC officer and Escrow officer (`adminsupport@pmcmanagers.com`). Signatures cannot dual-sign until this is fixed. Two options:

### Option A — Edit the account from the UI (recommended, no keys needed)
1. Log in to `https://www.pmcmanagers.com/admin?tab=escrow`
2. Under **Joint Escrow Accounts**, hit *Edit* on `PMC-KZ EMD Escrow #1`
3. Change the **Escrow officer** email to a distinct trustee (e.g. an escrow institution employee)
4. Save. The stuck transaction `BID-2026-TEST2` can then be re-signed by both sides cleanly.

### Option B — Issue a magic-link to an external trustee
```bash
# Replace TRUSTEE_EMAIL with the real escrow institution officer's email
TRUSTEE_EMAIL="trustee@escrow-institution.com"
ACC_ID="$(curl -s -b cookies.txt https://www.pmcmanagers.com/api/v1/escrow/accounts \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['items'][0]['id'])")"

curl -s -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -X POST https://www.pmcmanagers.com/api/v1/escrow/magic-tokens \
  -H "Content-Type: application/json" \
  -d "{\"account_id\":\"$ACC_ID\",\"officer_email\":\"$TRUSTEE_EMAIL\"}"
# → returns {"token": "...", "portal_url": "/escrow/officer/<token>"}
# Email that URL to the trustee. They open it, review the pending EMD tx,
# click "Sign — release_to_contractor". Both sides now signed → PMC clicks
# Release in the UI → funds move on the bank rail.
```

---

## 🧯 Rollback (unlikely, but here just in case)

Frontend — one-liner using the previous version zip:
```bash
ZIP=./pmc-frontend-v36-build.zip bash deploy-frontend-v40.sh
```

Backend — flip EB back to a previous version label:
```bash
aws --profile pmc-admin --region eu-west-2 elasticbeanstalk update-environment \
  --environment-name pmc-backend-prod --version-label v22d
```

---

## 🆘 If a deploy step fails

- **`aws: command not found`** → install AWS CLI v2 first, then `aws configure --profile pmc-admin`
- **`Unable to locate credentials`** → run `aws sts get-caller-identity --profile pmc-admin` to verify the profile exists
- **`AccessDenied` on S3** → the IAM user needs `s3:PutObject`, `s3:DeleteObject` on the bucket + `cloudfront:CreateInvalidation`
- **EB `update-environment` returns InvalidParameterCombination** → the env is mid-deploy from another action, wait ~2 min and re-run
- **Old bundle still served after invalidation** → wait 1-3 min for CloudFront edges to purge, then `curl -sI $WWW/index.html` and check ETag changed
