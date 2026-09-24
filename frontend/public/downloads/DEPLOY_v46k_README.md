# PMC Managers — Deploy v46k (Sovereign Redesign + Map-Reduce DPR)

## What's in this drop

**Frontend (v46k)** — `pmc-frontend-v46k-prod-build.zip`
- New **5-Portal Sovereign Gateway** at `/login` (Admin · Management · Partners · Agents · Vendors)
- New public **sovereign navy + gold** hero, editorial typography (Libre Baskerville + IBM Plex)
- Refreshed footer with Snapchat / Instagram / WhatsApp social icons
- Build has no preview URL baked in — same-origin `/api` calls

**Backend (v46j)** — `pmc-backend-v46j.zip`
- Map-Reduce multi-pass AI DPR ingestion in `backend/routers/tender_pro.py`
- KMT (68.7K chars) test: 22 sections drafted with 1,700–2,300 char bodies, ~37s runtime
- Includes `Dockerfile`, `.platform/nginx/conf.d/proxy.conf` (25 MB body limit), `VERSION`

## Frontend deploy (S3 + CloudFront)

```bash
# 1. Unpack locally
unzip pmc-frontend-v46k-prod-build.zip -d ./v46k-build

# 2. Non-destructive sync (NEVER use --delete at bucket root)
aws s3 sync ./v46k-build/ s3://pmc-managers-frontend-prod/ \
  --exact-timestamps \
  --exclude "downloads/*"

# 3. CloudFront invalidation
aws cloudfront create-invalidation \
  --distribution-id <YOUR_DIST_ID> \
  --paths "/*"
```

The `--exclude "downloads/*"` guard keeps existing public download artifacts (manuals, previous packages) intact in S3.

## Backend deploy (Elastic Beanstalk)

Upload `pmc-backend-v46j.zip` via the EB web console or CLI:

```bash
eb deploy --staged --label v46j
```

Wait for **Health: Green (Ok)** before running DPR validation.

## Post-deploy validation

1. Visit `https://www.pmcmanagers.com/login` — you should see 5 portal cards.
2. Click **Registered Vendors** — the vendor login form should slide in, gold submit button.
3. Go to `https://www.pmcmanagers.com/admin`, open Tender Builder → Generate from DPR → upload the KMT DPR PDF.
4. Confirm the response includes ≥ 20 sections, each with 500+ character bodies.
