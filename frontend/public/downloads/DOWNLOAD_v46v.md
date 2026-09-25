# v46v — Vendor first-login redirect + email sender switch to mail.pmcmanagers.com

## What's fixed in v46v

### 1 · Vendor login after admin activation (P0)
- **Bug**: Admins activating a vendor with a temporary password (or an approved registration) sets `must_change_password=True`. The **Vendor Portal** (`/vendor/login`) handled this correctly, but the **Unified login** (`/login` → Vendor tile) and the **Mobile login** dropped the flag and sent the vendor to `/vendor`. Depending on cookie state some vendors would then see the change-password screen briefly, some would see a blank redirect, some would land on the dashboard with an unusable "must change password" flag in memory.
- **Fix**: Both `UnifiedLogin.jsx` and `MobileLogin.jsx` now read `must_change_password` from the login response and route to `/vendor/change-password` on first sign-in. Behaviour matches the dedicated vendor login page.
- **Impact**: Any vendor activated by admin (`POST /api/v1/vendors/{ref}/activate` mode=`set_password`) or approved via registration can now sign in from **any** login entry point.

### 2 · Email sender switched to `admin@mail.pmcmanagers.com` (P0)
- **Change**: `EMAIL_FROM_ADDRESS` default in `backend/config.py` and the `.env` template is now `admin@mail.pmcmanagers.com`. All Resend traffic will send from this address as soon as the domain is verified.
- **DNS setup required before it works** (owner action, not deployment):
  1. Log in to https://resend.com/domains and click **Add Domain**.
  2. Enter `mail.pmcmanagers.com` (the sub-domain, not the root).
  3. Resend will show 3 DNS records to add on your DNS provider:
     - `MX` record on `send.mail.pmcmanagers.com` (or similar — Resend generates the exact host)
     - `TXT` record on `send.mail.pmcmanagers.com` (SPF)
     - `TXT` record on `resend._domainkey.mail.pmcmanagers.com` (DKIM)
  4. Add all three records at your DNS provider (Cloudflare / Route53 / GoDaddy — wherever `pmcmanagers.com` is hosted). Verification is usually done in 5–30 minutes.
  5. Click **Verify DNS records** on the Resend dashboard. Once green, emails will send from `admin@mail.pmcmanagers.com` with no code change.
- Until DNS is verified, Resend will return `403 The mail.pmcmanagers.com domain is not verified` and outgoing emails will not send. To keep emails flowing in the meantime, either verify the root `pmcmanagers.com` domain OR leave the sub-domain unverified and Resend will bounce — no fallback to `emergentmails.com` any more.

---

## Deploy steps

### Backend (Elastic Beanstalk)
1. Upload **`pmc-backend-v46v.zip`** to the EB environment (contains `Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf`, and the full `backend/` tree).
2. **EB environment properties must include**:
   - `MONGO_URL`, `DB_NAME`, `JWT_SECRET`
   - `RESEND_API_KEY` (your existing key)
   - `EMAIL_FROM_ADDRESS=admin@mail.pmcmanagers.com`
   - `EMAIL_FROM_NAME=PMC Managers Limited`
   - Stripe keys, VAPID keys (for push).
3. If `EMAIL_FROM_ADDRESS` is not set as an env-var, the code defaults to `admin@mail.pmcmanagers.com`.

### Frontend (S3 + CloudFront)
1. Unzip **`pmc-frontend-v46v-prod-build.zip`** → `aws s3 sync <unzipped> s3://<bucket>` **without `--delete`** (protects `/downloads/`).
2. This build is **same-origin** — no backend URL is baked in.
3. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.

### Post-deploy smoke test
1. Admin → Vendors → activate an inactive vendor with `mode=set_password`.
2. Open a private window → visit `/login` → click the **Vendor** tile.
3. Sign in with the temp password → should land on `/vendor/change-password`.
4. Set a new password → should land on `/vendor` dashboard.
5. Admin panel should now show **NO** "emergentmails.com" strings anywhere.

---

## Downloads

- **[pmc-backend-v46v.zip](./pmc-backend-v46v.zip)** — EB Docker archive (288 KB)
- **[pmc-frontend-v46v-prod-build.zip](./pmc-frontend-v46v-prod-build.zip)** — same-origin production build (~1.25 MB)
- **[DOWNLOAD_v46v.md](./DOWNLOAD_v46v.md)** — this file
