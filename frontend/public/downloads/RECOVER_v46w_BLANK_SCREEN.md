# v46w recovery — blank white screen after deploy

## What actually happened
Your S3 bucket has the new `index.html` but **not** the accompanying `static/js/` and `static/css/` files. CloudFront's SPA-fallback returns `index.html` for every missing path, so the browser gets HTML when it asks for `/static/js/main.*.js` and dies with `Unexpected token '<'` → blank white screen.

Proof: `curl -I https://www.pmcmanagers.com/static/js/main.e3e79d6e.js` returns `content-type: text/html`, content-length `1602` — that's the size of your index.html, not a JS file.

**No code fix required. Just a proper re-sync.**

---

## Step-by-step recovery (5 minutes)

### 1. Download the correct zip
`pmc-frontend-v46w-prod-build.zip` from this Downloads folder. Sanity check the contents:
```
unzip -l pmc-frontend-v46w-prod-build.zip | grep static/js/main
# Expect:  static/js/main.e3e79d6e.js  (~1.38 MB)
```

### 2. Extract to a clean folder
```
rm -rf /tmp/pmc-build && mkdir /tmp/pmc-build
unzip -q pmc-frontend-v46w-prod-build.zip -d /tmp/pmc-build
ls /tmp/pmc-build
# Expect:  asset-manifest.json  index.html  static/  service-worker.js  manifest.json  hero-containers.jpg  pmc-logo.png
```

### 3. Sync to S3 — **use --delete and exclude downloads/**
This is the critical fix. Point the sync at the extracted folder and remove stale assets while preserving `/downloads/`:
```
aws s3 sync /tmp/pmc-build/ s3://<your-bucket>/ \
    --delete \
    --exclude "downloads/*" \
    --cache-control "max-age=31536000,immutable" \
    --exclude "index.html" \
    --exclude "service-worker.js" \
    --exclude "manifest.json"

# index.html + service-worker.js MUST have no-cache so CloudFront serves the fresh copy immediately
aws s3 cp /tmp/pmc-build/index.html s3://<your-bucket>/index.html \
    --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://<your-bucket>/service-worker.js \
    --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json s3://<your-bucket>/manifest.json \
    --cache-control "no-cache, no-store, must-revalidate"
```

### 4. Invalidate CloudFront
```
aws cloudfront create-invalidation \
    --distribution-id <YOUR-DIST-ID> \
    --paths "/*"
```

### 5. Verify from a clean browser (no cache)
Open an **Incognito/Private window** and go to `https://www.pmcmanagers.com/`.
- Login page should render (dark navy with the 5 portal cards).
- Press F12 → Network → filter `js`. `main.e3e79d6e.js` should return **200** with `content-type: application/javascript`.

### 6. If you already deployed and users have a stale service worker
Anyone who visited the broken page has a cached broken service worker. To force-update:
- The new `service-worker.js` (cache key `pmc-shell-v46u`) skips itself and self-updates within one page load.
- If a user is still stuck, ask them to: DevTools → Application → Service Workers → **Unregister** → hard-refresh (Ctrl-Shift-R).

---

## Why the previous sync failed
The most common causes when only `index.html` lands but `static/` doesn't:
1. You ran `aws s3 cp index.html s3://<bucket>/index.html` instead of `aws s3 sync` on the whole folder.
2. You extracted the zip but pointed the sync at the wrong folder (e.g. the folder containing the zip, not the folder with `index.html` inside it).
3. You used a GUI tool (S3 Browser, Cyberduck) that skipped hidden or nested folders because of a size limit.
4. The upload timed out mid-way and only committed the small files.

Whichever it was, Step 3 above with `aws s3 sync ... --delete` fixes it in one shot.

---

## After recovery, verify these key behaviours
1. `/` loads the 5-portal login page.
2. Admin card → `adminsupport@pmcmanagers.com` / `Admin@12345` → lands on `/admin`.
3. Management / Partners / Agents cards → same credentials → lands on `/staff`.
4. Vendor card → your activated vendor's temp password → lands on `/vendor/change-password`.
5. Set a new vendor password → lands on `/vendor` dashboard.
