# PMC Managers — Release v50t (critical production fix + cumulative v50s)

## 🚨 Critical Fix in this build: Production API Routing
Previous frontend builds baked in `REACT_APP_BACKEND_URL=https://pmc-forest-green...`
which caused browsers visiting `www.pmcmanagers.com` to send login, password reset,
and portal API calls to the preview container instead of your production Elastic Beanstalk
backend.

**Fixed at two levels:**
1. **Runtime Domain Guard in `api.js`:** Whenever hostname is `pmcmanagers.com`
   (or any custom domain), API calls strictly use relative `/api/...` (proxied by
   CloudFront to EB).
2. **Build-time:** Built cleanly with `REACT_APP_BACKEND_URL=""`.

## Vendor UX fixes included (v50s):
- **Upload buttons clearly visible:** Technical / Commercial / Other doc upload tiles are now amber dashed boxes with "+ Click to upload" prompts.
- **Re-upload after delete:** File input resets so re-selecting the same file works.
- **My Bids live:** `/vendor/mybids` rewritten to live API (`/api/v1/bids/mine`).
- **Sidebar badges match live data:** Dynamic counts for Find tenders / My bids / Signatures.
- **Approved categories on Company & KYC:** `/vendor/auth/me` returns `business_categories`.
- **Back button on Categories page:** `← Back` link returns to `/vendor/company`.

## Deploy Instructions
1. Frontend: Extract `pmc-frontend-v50t-prod-build.zip` → Upload to S3 bucket → CloudFront invalidate `/*`
2. Backend: `pmc-backend-v50t.zip` → Deploy to Elastic Beanstalk
