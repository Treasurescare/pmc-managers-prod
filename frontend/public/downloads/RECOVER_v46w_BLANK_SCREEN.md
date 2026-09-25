# RECOVER — blank screen / login stuck on "VERIFYING…" on pmcmanagers.com

## Diagnosis (confirmed with curl + screen recording)

Two separate problems stacked on top of each other. **Neither is a code bug in v46w/v46x — both are deployment + stale-cache issues on your side.**

### Problem 1 — S3 is missing the `static/` folder
Your bucket has `index.html` but not `static/js/main.*.js` or `static/css/*`. CloudFront's SPA-fallback returns `index.html` for every missing path, so the browser receives HTML when it asks for JS → `Unexpected token '<'` → blank white page for anyone without a cache.

Proof (run yourself):
```
curl -sI https://www.pmcmanagers.com/static/js/main.e3e79d6e.js
# content-type: text/html  content-length: 1602   ← that's index.html, not JS
```

### Problem 2 — Your browser is running a stale Service Worker from the 2024 build
Your recording shows footer "© 2024 PMC MANAGERS LIMITED" — the current code says 2026. That old build shipped a service worker with a bug (fixed in v46u) where POST `/api/*` requests get intercepted and the response is never returned. Result: the login request **hangs forever** → "VERIFYING…" with no error toast. The production API itself is fine (`curl` returns a proper `401 Invalid email or password` in 0.3s).

The v46x frontend adds a 20-second axios timeout so even if this ever happens again, you'll get an error toast instead of an infinite spinner.

---

## Recovery (10 minutes)

### Step 1 — Extract the v46x build cleanly
```
rm -rf /tmp/pmc-build && mkdir /tmp/pmc-build
unzip -q pmc-frontend-v46x-prod-build.zip -d /tmp/pmc-build
ls /tmp/pmc-build
# Expect: index.html  static/  service-worker.js  manifest.json  asset-manifest.json  hero-containers.jpg  pmc-logo.png
```

### Step 2 — Full S3 sync (this is what went wrong last time)
```
aws s3 sync /tmp/pmc-build/ s3://<your-bucket>/ \
    --delete \
    --exclude "downloads/*" \
    --exclude "index.html" --exclude "service-worker.js" --exclude "manifest.json" \
    --cache-control "max-age=31536000,immutable"

aws s3 cp /tmp/pmc-build/index.html        s3://<your-bucket>/index.html        --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://<your-bucket>/service-worker.js --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json     s3://<your-bucket>/manifest.json     --cache-control "no-cache, no-store, must-revalidate"
```

### Step 3 — Invalidate CloudFront
```
aws cloudfront create-invalidation --distribution-id <YOUR-DIST-ID> --paths "/*"
```

### Step 4 — Kill the stale service worker in YOUR browser (one-time)
The old SW keeps serving the 2024 shell even after S3 is fixed, so do this once:
1. Open `https://www.pmcmanagers.com` in Chrome/Edge.
2. Press `F12` → **Application** tab → **Service Workers** (left sidebar).
3. Click **Unregister** next to the PMC worker.
4. Same **Application** tab → **Storage** → **Clear site data** → confirm.
5. Hard-refresh: `Cmd + Shift + R` (Mac) / `Ctrl + Shift + R` (Windows).
6. The new SW (`pmc-shell-v46x`) installs, deletes every old cache, and from now on self-updates within one page load.

Other users/devices will heal automatically on their second visit after Step 3 — no action needed for them.

### Step 5 — Verify
- `/` shows the 5-portal login with footer **© 2026**.
- DevTools → Network → `main.*.js` returns `200` + `content-type: application/javascript`.
- Vendor card → wrong password → you now get a red **"Invalid email or password"** toast within a second (not a silent hang).

---

## About the vendor account `evvcorporates@gmail.com`
The production backend answers login correctly, so once the frontend is healthy you'll see either the dashboard or a clear error. If you get "Invalid email or password" with the password you believe is right, the most likely cause is that this vendor was activated on the **preview** database, not production — production EB has its own MongoDB (`MONGO_URL` env var on EB). Re-activate the vendor from the **production** admin console (Vendors → select → Activate with `set_password`), then log in with that temp password.

---

## Downloads
- **[pmc-frontend-v46x-prod-build.zip](./pmc-frontend-v46x-prod-build.zip)** — same-origin prod build + axios timeout + SW `pmc-shell-v46x`
- **[pmc-backend-v46w.zip](./pmc-backend-v46w.zip)** — backend unchanged since v46w (5-portal role backfill)
- **[DOWNLOAD_v46w.md](./DOWNLOAD_v46w.md)** — v46w release notes incl. Resend DNS guide (Route 53 / GoDaddy)
