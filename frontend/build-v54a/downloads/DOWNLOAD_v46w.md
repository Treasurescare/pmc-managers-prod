# v46w — All 5 portals log in + email DNS routing guide

## What's fixed in v46w

### 1 · Non-Admin portals sign-in fix (P0)
- **Bug**: The 5-portal login (`/login`) offered Management, Partners, Agents, Vendors and Admin cards, but the seeded master admin only carried `roles=["admin","committee_member","support"]`. When you clicked Management/Partners/Agents and entered admin credentials, the backend correctly replied "You do not hold the management role" and login failed. Only **Admin** worked because its card had a legacy fallback.
- **Fix**:
  - Backend seed: the master admin (`adminsupport@pmcmanagers.com`) and the owner account now carry **all** executive roles: `admin`, `reviewer`, `management`, `partner`, `agent`, `committee_member`, `support`, `auditor`. Backfill runs on every cold-start — no manual DB action.
  - Frontend: every staff portal card first tries its own role, then transparently falls back to `admin`. Same fix in the mobile login screen. A master admin can now sign in from **any** of the 5 portal cards.
- **Impact**: Admin, Management, Partners, Agents and Vendors cards all authenticate the master admin. Specialist users (escrow, legal, certifier, accounting) still authenticate against their exact roles as before.

### 2 · Email sender switched to `admin@mail.pmcmanagers.com` (P0 — carried over from v46v)
- `EMAIL_FROM_ADDRESS` default = `admin@mail.pmcmanagers.com`. No fallback to any `emergentmails.com` domain.
- DNS verification of `mail.pmcmanagers.com` in Resend is required before mail sends — see the routing guide below.

---

## DNS routing guide — verify `mail.pmcmanagers.com` in Resend

You picked `mail.pmcmanagers.com` as the sender sub-domain. Resend gives you 3 DNS records to add: `MX` (accepts bounces), `TXT` for SPF (says which servers may send), and `TXT` for DKIM (signs the outgoing mail). Follow whichever DNS host owns `pmcmanagers.com`.

### Step A — Get the exact records from Resend
1. Log in to https://resend.com → **Domains** → **Add Domain**.
2. Enter **`mail.pmcmanagers.com`** (NOT `pmcmanagers.com`).
3. Region: pick **`us-east-1`** (default is fine).
4. Resend will now show 3 records. They look roughly like this (your exact values will differ — always copy from Resend, not this doc):
   ```
   Type   Host                                  Value                                       Priority
   MX     send                                  feedback-smtp.us-east-1.amazonses.com       10
   TXT    send                                  "v=spf1 include:amazonses.com ~all"         —
   TXT    resend._domainkey                     "p=MIGfMA0GCSqG...verylongkey..."           —
   ```
   Notes:
   - The **Host** column is what you paste into the "Name" / "Host" field at your DNS provider.
   - Where Resend says host `send`, you'll type **`send.mail`** at your DNS provider (because it's a sub-record of the `mail` sub-domain — see the sections below for exact syntax).
   - The DKIM value is one very long string. Copy it verbatim, including any quotes if the provider strips them.
   - Keep the Resend browser tab open; you'll click **Verify DNS Records** at the end.

---

### Step B (Option 1) — Add the records in **AWS Route 53**

Use this if you already host `pmcmanagers.com` in a Route 53 hosted zone.

1. AWS Console → **Route 53** → **Hosted zones** → click **`pmcmanagers.com`**.
2. Click **Create record** three times, once per record below. Route 53 lets you enter the full record name (including the sub-domain) directly.

   **Record 1 — MX for bounce handling**
   - Record name: `send.mail` (Route 53 auto-appends `.pmcmanagers.com`)
   - Record type: **MX**
   - TTL: `300`
   - Value: `10 feedback-smtp.us-east-1.amazonses.com` (paste the Priority + host from Resend, separated by a single space)
   - Save.

   **Record 2 — TXT for SPF**
   - Record name: `send.mail`
   - Record type: **TXT**
   - TTL: `300`
   - Value: `"v=spf1 include:amazonses.com ~all"` (keep the double quotes; Route 53 requires them)
   - Save.

   **Record 3 — TXT for DKIM**
   - Record name: `resend._domainkey.mail`
   - Record type: **TXT**
   - TTL: `300`
   - Value: paste the DKIM string from Resend, wrapping the entire value in double quotes (Route 53 will store it correctly).
   - Save.

3. Go back to the Resend Domains page → click **Verify DNS Records**. Route 53 usually verifies within a minute.

**AWS CLI alternative** (single command, drop your zone ID + DKIM value in and run):
```
aws route53 change-resource-record-sets --hosted-zone-id <YOUR-ZONE-ID> --change-batch '{
  "Changes":[
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"send.mail.pmcmanagers.com","Type":"MX","TTL":300,"ResourceRecords":[{"Value":"10 feedback-smtp.us-east-1.amazonses.com"}]}},
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"send.mail.pmcmanagers.com","Type":"TXT","TTL":300,"ResourceRecords":[{"Value":"\"v=spf1 include:amazonses.com ~all\""}]}},
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"resend._domainkey.mail.pmcmanagers.com","Type":"TXT","TTL":300,"ResourceRecords":[{"Value":"\"<PASTE-DKIM-KEY-HERE>\""}]}}
  ]
}'
```

---

### Step B (Option 2) — Add the records in **GoDaddy**

Use this if `pmcmanagers.com` still has GoDaddy nameservers.

1. Sign in to https://godaddy.com → **My Products** → find `pmcmanagers.com` → click **DNS**.
2. On the DNS Management page you'll see a table of existing records. Click **Add New Record** three times.

   **Record 1 — MX for bounce handling**
   - Type: **MX**
   - Name (Host): `send.mail`  ← GoDaddy auto-appends `.pmcmanagers.com`
   - Priority: `10`
   - Value (Points To): `feedback-smtp.us-east-1.amazonses.com`
   - TTL: `1 Hour` (default is fine)
   - Save.

   **Record 2 — TXT for SPF**
   - Type: **TXT**
   - Name (Host): `send.mail`
   - TXT Value: `v=spf1 include:amazonses.com ~all` (GoDaddy does NOT want the outer double quotes)
   - TTL: `1 Hour`
   - Save.

   **Record 3 — TXT for DKIM**
   - Type: **TXT**
   - Name (Host): `resend._domainkey.mail`
   - TXT Value: paste the DKIM string from Resend (no outer quotes)
   - TTL: `1 Hour`
   - Save.

3. GoDaddy usually applies DNS changes within 5–10 minutes. Return to the Resend Domains page and click **Verify DNS Records**. Keep hitting Verify every few minutes if it stays yellow.

---

### Step C — Confirm mail is actually leaving Resend
Once Resend shows the domain as **Verified** (green tick):
1. In your admin portal, activate a test vendor with mode `set_password`.
2. Check the vendor inbox — the message should arrive within 30–60 seconds from `admin@mail.pmcmanagers.com`.
3. In the Resend dashboard → **Logs**, you should see the send with status `delivered` (or `bounced` if the recipient inbox is invalid — that's a good sign the domain is live).

### Common problems
- **"Domain not verified" still showing in Resend after 30 min** — the TXT DKIM record was truncated by GoDaddy. Check the Value field is the full string (they cap at 255 chars per part but automatically split; some providers don't — if that happens, split the value into `"first-part" "second-part"`).
- **Emails go to spam** — normal for the first 1–2 sends from a new domain. Warm up gradually or add a **DMARC** TXT record at `_dmarc.pmcmanagers.com` with value `v=DMARC1; p=none;`.
- **Cloudflare in front of GoDaddy?** If DNS resolves to Cloudflare, add the records at Cloudflare instead. GoDaddy DNS is only authoritative when the nameservers are `ns*.domaincontrol.com`.

---

## Deploy steps

### Backend (Elastic Beanstalk)
1. Upload **`pmc-backend-v46w.zip`** to the EB environment (contains `Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf`, full `backend/` tree).
2. **EB environment properties** must include:
   - `MONGO_URL`, `DB_NAME`, `JWT_SECRET`
   - `RESEND_API_KEY` (your existing key `re_3FzTQ6...`)
   - `EMAIL_FROM_ADDRESS=admin@mail.pmcmanagers.com`  ← optional; the code already defaults to this
   - `EMAIL_FROM_NAME=PMC Managers Limited`
   - Stripe keys, VAPID keys (for push).
3. On cold-start the master admin + owner rows are auto-backfilled with the full executive role list — you don't need to touch the DB.

### Frontend (S3 + CloudFront)
1. Unzip **`pmc-frontend-v46w-prod-build.zip`** → `aws s3 sync <unzipped> s3://<bucket>` **without `--delete`** (protects `/downloads/`).
2. Same-origin build — no backend URL baked in.
3. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.

### Post-deploy smoke test
1. Open `/login` → click **Management** → sign in with the admin credentials → should land on `/staff` (or `/admin` if the fallback fired).
2. Do the same for **Strategic Partners** and **Procurement Agents** cards.
3. Vendor card with an admin-activated vendor's temp password → should route to `/vendor/change-password`.

---

## Downloads

- **[pmc-backend-v46w.zip](./pmc-backend-v46w.zip)** — EB Docker archive (~290 KB)
- **[pmc-frontend-v46w-prod-build.zip](./pmc-frontend-v46w-prod-build.zip)** — same-origin production build (~1.25 MB)
- **[DOWNLOAD_v46w.md](./DOWNLOAD_v46w.md)** — this file
