# Chapter 6 — Custom Domain (`www.pmcmanagers.com`) on AWS

## Prerequisites you need in hand

1. **You own `pmcmanagers.com`** at a registrar (GoDaddy / Namecheap / Cloudflare / etc.). If not, buy it before starting (~$12/yr).
2. **AWS account access** as `pmc-admin` (already set up).
3. Approx **30-45 min** including DNS propagation waits.

## Architecture we're building

```
Browser → www.pmcmanagers.com (Route 53) → CloudFront E2WZT1TMQ0EK9W
                                            ├── / (default)          → S3 pmc-managers-frontend-prod (React SPA)
                                            └── /api/*               → EB pmc-backend-prod (FastAPI Docker)
                                            SSL via ACM certificate in us-east-1
```

Same distribution, just add domain aliases + attach an SSL cert.

## Step 1 — Request the SSL cert in **us-east-1** (CloudFront requirement)

⚠️ CloudFront **only accepts ACM certs from us-east-1 (N. Virginia)** — this is a hard AWS rule.

1. **Top-right region switcher** → change to **US East (N. Virginia) us-east-1** (temporarily — we'll switch back after)
2. **AWS Console → Certificate Manager (ACM)** → **Request certificate**
3. **Certificate type**: Public certificate → **Next**
4. **Fully qualified domain names**:
   - `www.pmcmanagers.com`
   - Click **Add another name** → add `pmcmanagers.com` (bare apex — for redirect)
5. **Validation method**: **DNS validation (recommended)**
6. Leave rest default → **Request**

ACM will show status **"Pending validation"** with 2 CNAME records you need to add at your DNS.

## Step 2 — Add validation CNAMEs at your registrar

Click into the cert → **Domains** section → you'll see 2 rows like:
```
Domain: www.pmcmanagers.com
CNAME name:  _abc123.www.pmcmanagers.com.
CNAME value: _def456.acm-validations.aws.
```

At your registrar's DNS panel, add both CNAMEs exactly as shown.

⏱ Wait 2-10 min → ACM status flips to **"Issued"** (green). Refresh the ACM page to check.

## Step 3 — Point Route 53 (or your DNS) at CloudFront

### Option A — Use Route 53 (recommended, $0.50/mo)

1. Switch AWS region back to **eu-west-2 London** (top-right)
2. **AWS Console → Route 53 → Hosted zones → Create hosted zone**
3. **Domain name**: `pmcmanagers.com`
4. **Type**: Public hosted zone → **Create**
5. Route 53 gives you 4 NS records (like `ns-123.awsdns-45.com`). Copy them.
6. At your **registrar**, change nameservers from the registrar's default → paste the 4 AWS nameservers.
   - GoDaddy: Manage DNS → Nameservers → Change → Enter my own → paste 4
   - Namecheap: Domain → Nameservers → Custom DNS → paste 4
7. ⏱ Wait up to 60 min for nameserver propagation (usually 5-15 min).
8. Back in Route 53 hosted zone → **Create record**:
   - **Record name**: `www`
   - **Record type**: `A`
   - Toggle **Alias**: ON
   - **Route traffic to**: `Alias to CloudFront distribution` → pick your distribution (`d2h9tkca2zjofy.cloudfront.net`)
   - **Create records**
9. Repeat for the apex:
   - **Record name**: leave blank (represents `pmcmanagers.com`)
   - Record type: `A` · Alias: ON · Alias to CloudFront → same distribution
   - **Create records**

### Option B — Keep DNS at your registrar

Add these records manually at your registrar (values from CloudFront):
```
www.pmcmanagers.com   CNAME   d2h9tkca2zjofy.cloudfront.net
pmcmanagers.com       ALIAS   d2h9tkca2zjofy.cloudfront.net  (Cloudflare/Namecheap support ALIAS/ANAME)
```
If your registrar doesn't support ALIAS for apex, use option A.

## Step 4 — Attach the domain + cert to CloudFront

1. **CloudFront → Distributions → `E2WZT1TMQ0EK9W`** (your distribution)
2. **General** tab → **Settings** section → **Edit**
3. **Alternate domain names (CNAMEs)** → click **Add item**:
   - `www.pmcmanagers.com`
   - Click **Add item** again → `pmcmanagers.com`
4. **Custom SSL certificate** dropdown → pick your newly-issued cert (should be labelled with the domain names)
5. **Save changes**

⏱ Wait ~5-10 min for CloudFront to redeploy.

## Step 5 — Verify

```powershell
curl.exe -v https://www.pmcmanagers.com/api/v1/meta/health
```

Expected: HTTP 200 with `{"ok":true,...}` — same as before, now on your custom domain.

Open in browser:
- `https://www.pmcmanagers.com` → landing page loads
- `https://www.pmcmanagers.com/admin/login` → login page loads
- `https://pmcmanagers.com` → redirects to www (or loads directly, both work)

## Step 6 — Rebuild frontend with new domain

Since `REACT_APP_BACKEND_URL` is baked into the JS bundle, we need one final rebuild.
Ping me and I'll build a `pmc-frontend-build-v3.zip` with `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com`.

You'll re-sync it to S3 with:
```powershell
aws s3 sync .\frontend-build-v3\ s3://pmc-managers-frontend-prod/ --delete
aws cloudfront create-invalidation --distribution-id E2WZT1TMQ0EK9W --paths "/*"
```

## Step 7 — Post-launch cleanup

Update these external integrations that reference the CloudFront default domain:

1. **EB env vars** — Change `FRONTEND_URL` from `https://d2h9tkca2zjofy.cloudfront.net` → `https://www.pmcmanagers.com`
2. **EB env vars** — `CORS_ORIGINS` add `https://www.pmcmanagers.com,https://pmcmanagers.com`
3. **DocuSign Connect Webhook** — In DocuSign Admin → Connect → Edit your webhook → update URL from preview → `https://www.pmcmanagers.com/api/v1/docusign/webhook`
4. **Stripe** (later, when real key is added) — success/cancel URLs
5. **Zoom** (if any redirect URIs registered) — update to new domain

## Rollback

If something breaks, revert Step 4 (remove alt CNAMEs from CloudFront) and the CloudFront default `d2h9tkca2zjofy.cloudfront.net` will resume serving.
