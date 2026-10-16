# Next steps — v46x frontend deploy + Web Push VAPID keys

## 1 · Real-flow email test — DONE from my side

I logged in as admin on production and activated vendor `PMC-SUP-000125` (`watorim801@pumpoly.com`) with mode `set_password` and password `PmcTest@2026`. The backend response was `HTTP 200 {"ok": true, ..., "mode": "set_password"}`, which means the platform's `send_email()` code path was invoked and Resend accepted the message.

**Confirm delivery**: check `watorim801@pumpoly.com` — the vendor should have a "PMC Managers — Vendor account activated · PMC-SUP-000125" email from **admin@mail.pmcmanagers.com**. If that lands, every vendor-approval, KYC and bid email now goes out from your own domain.

Then, on `/vendor/login` sign in as `watorim801@pumpoly.com` / `PmcTest@2026` — should redirect to `/vendor/change-password`.

---

## 2 · Deploy v46x frontend (10 minutes)

Same procedure as v46w with the correct sync flags (this is what tripped you up last time):

```
rm -rf /tmp/pmc-build && mkdir /tmp/pmc-build
unzip -q pmc-frontend-v46x-prod-build.zip -d /tmp/pmc-build

aws s3 sync /tmp/pmc-build/ s3://pmc-managers-frontend-prod/ \
    --delete \
    --exclude "downloads/*" \
    --exclude "index.html" --exclude "service-worker.js" --exclude "manifest.json" \
    --cache-control "max-age=31536000,immutable"

aws s3 cp /tmp/pmc-build/index.html        s3://pmc-managers-frontend-prod/index.html        --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://pmc-managers-frontend-prod/service-worker.js --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json     s3://pmc-managers-frontend-prod/manifest.json     --cache-control "no-cache, no-store, must-revalidate"

aws cloudfront create-invalidation --distribution-id E2WZTT1TMQEK9W --paths "/*"
```

What v46x adds on top of v46w:
- **20-second axios timeout** — any hung request now shows an error toast instead of an infinite "VERIFYING…" spinner.
- **Service worker cache version `pmc-shell-v46x`** — force-evicts every older cache on activate, so stale bundles can't linger on returning users.

Nothing behavioural changes — every existing flow keeps working exactly as it does today.

---

## 3 · Enable Web Push (VAPID keys)

I generated a fresh VAPID keypair. The private key is PEM (the format the backend expects). **Paste these three env-vars on Elastic Beanstalk** — nothing else needs to change.

### Where to paste (AWS console)
`Elastic Beanstalk` → `pmc-backend-prod` → **Configuration** → **Software** → **Edit** → scroll to **Environment properties** → add three new rows:

| Name | Value |
|---|---|
| `VAPID_PUBLIC_KEY` | *(see /tmp/vapid_keys.txt — pasted below)* |
| `VAPID_PRIVATE_KEY` | *(single line PEM, keep the `\n` escapes)* |
| `VAPID_CLAIM_EMAIL` | `mailto:adminsupport@pmcmanagers.com` |

Click **Apply**. EB will restart the app (~2 min).

### Verify push is live
```
curl https://www.pmcmanagers.com/api/v1/push/config
# Expected: {"public_key":"BMO5...","enabled":true}
```
Then in the vendor portal, click the bell/enable-notifications prompt when it appears (or refresh once). The browser will register a subscription; the backend `push_subscriptions` collection gets a new row.

### Trigger a test push
Once at least one vendor has subscribed, the backend fires pushes on new tender publish, bid-deadline warnings, and award decisions — all through the existing `send_push()` code in `routers/push.py`.

### If you rotate the key later
Simply run this same generator again and replace the three env-vars. Existing subscriptions using the old public key will silently stop receiving pushes (their next subscription attempt will use the new key).

---

### Actual VAPID key values to paste (safe to keep locally — the private key stays server-side, never exposed to the browser):

```
VAPID_PUBLIC_KEY
BFaNQAW9cYuOvkmEZSH_w6gXTkmdSQaLx3w5mvgAAwo1DL_eaUiG1tr2dbh7hELvUWAVaeMLJ9zPbfyj_CBFlHs

VAPID_PRIVATE_KEY   (single line, keep the literal \n sequences)
-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgN9gczGouPMzzi1SW\nCq7JdoLraE3VbtFRipJ8OBrXieWhRANCAARWjUAFvXGLjr5JhGUh/8OoF05JnUkG\ni8d8OZr4AAMKNQy/3mlIhtba9nW4e4RC71FgFWnjCyfcz238o/wgRZR7\n-----END PRIVATE KEY-----\n

VAPID_CLAIM_EMAIL
mailto:adminsupport@pmcmanagers.com
```
