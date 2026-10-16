# PMC Managers — Release v52cz rev2

**Date:** 14 Feb 2026
**Scope:** Vendor-download fixes — Blank form regeneration · Bundle picker · Reg-doc / Notice-pack CORS

---

## What's in this release

### Fix 1 — Blank registration form always auto-generated
`GET /api/v1/vendors/registration-template` no longer serves whatever an admin uploaded. It now auto-generates a PDF from the live `RegistrationUpdateIn` schema + `DOC_SLOTS` (sections A → E) and returns it with the canonical filename `PMC-Vendor-Registration-Form.pdf`. If you change a field in the form tomorrow, the PDF updates automatically with no admin step. Prevents repeats of the resume `.docx` leak.

### Fix 2 — Bundle picker on vendor bid submission
On `/vendor/bid/new/<ref>`, each uploaded doc now has a checkbox (ticked by default). `N of M selected` counter + `All` / `None` shortcuts. `Download selected (N)` button is disabled when nothing is selected. Backed by new `POST /api/v1/uploads/bundle` which bundles the selected keys into one ZIP for signed-in admin or vendor.

### Fix 3 — Reg-doc view / Notice "Download pack" CORS
Removed every `${REACT_APP_BACKEND_URL}` prefix from frontend download URLs. These were being baked at build time, which pointed production bundles at the preview host → cross-origin → CORS blocked. Fixed in `NoticeDetailE.jsx` (Download pack), `NoticeDetail.jsx` (primary doc + template PDF/ZIP + attachments), `CorrigendaPanel.jsx`, `DocSlot.jsx` (registration doc viewer), `api.js` (templateDownloadUrl, bulkTemplateUrl).

### Also
- Empty-tender "Download pack" shows a friendly toast "No documents available for this tender" instead of a silent 404.
- Latent `Link` import crash in BidSubmit (409 duplicate-bid branch) fixed.

---

## Files

| File | SHA / Size | Purpose |
|---|---|---|
| [`pmc-backend-v52cz-rev2.zip`](./pmc-backend-v52cz-rev2.zip) | see `ls -la` | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev2-prod-build.zip`](./pmc-frontend-v52cz-rev2-prod-build.zip) | see `ls -la` | S3 / CloudFront static assets (contents of CRA `build/`) |

Both are fresh, uniquely-versioned artefacts — not an overwrite of `v52cy`.

Backend zip packaging invariants (per standing EB rule):
- `Dockerfile` + `.ebextensions/` kept.
- `docker-compose.yml` **excluded** (none present in repo anyway — verified empty).
- `.env`, `keys/`, tests, `__pycache__`, `.pytest_cache`, `.git` excluded.
- `.dockerignore` kept, with the same exclusions re-asserted inside the image build.

---

## Deployment steps

### Backend → AWS Elastic Beanstalk

1. Open the EB environment console for the PMC Managers production backend.
2. Upload and deploy `pmc-backend-v52cz-rev2.zip`.
3. **Do not touch environment variables.** All secrets remain managed via EB config (`MONGO_URL`, `DB_NAME`, Stripe, Resend, SSM, etc.).
4. Wait for the environment to go green. If the single container doesn't bind to :80, re-check the health endpoint in `.ebextensions/01-healthcheck.config` — unchanged from the previous working release.

Smoke checks after deploy (run with your production domain):
```
curl -I https://www.pmcmanagers.com/api/v1/vendors/registration-template?inline=false
#   → HTTP 200, Content-Type: application/pdf, filename="PMC-Vendor-Registration-Form.pdf"

curl -I https://www.pmcmanagers.com/api/v1/notices/PMC-NOT-2026-0095/pack
#   → HTTP 200, Content-Type: application/zip   (or 405 on HEAD — then try GET)
```

### Frontend → S3 + CloudFront

1. Unzip `pmc-frontend-v52cz-rev2-prod-build.zip` locally. You get `index.html`, `asset-manifest.json`, `static/`, etc.
2. Sync everything to your S3 origin bucket (preserve paths and set cache-control on `static/` as before).
   ```
   aws s3 sync . s3://<your-origin-bucket> --delete \
       --cache-control "public, max-age=31536000, immutable" \
       --exclude "index.html" --exclude "asset-manifest.json"
   aws s3 cp index.html s3://<your-origin-bucket>/index.html \
       --cache-control "no-cache, no-store, must-revalidate"
   aws s3 cp asset-manifest.json s3://<your-origin-bucket>/asset-manifest.json \
       --cache-control "no-cache, no-store, must-revalidate"
   ```
3. Invalidate CloudFront:
   ```
   aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
   ```

Smoke checks after deploy:
- Open https://www.pmcmanagers.com/register → the "Blank registration form" card shows `PMC-Vendor-Registration-Form.pdf`. Click **Download blank form** → opens cleanly in Word / Preview / Adobe Reader as a 3-page PDF with sections A → E.
- Open any live tender → **Download pack** returns a ZIP (not a blank page / silent fail).
- Log in as a vendor → `/vendor/bid/new/<notice>` → upload 2 PDFs → tick / untick checkboxes → `Download selected (N)` returns a ZIP with exactly the selected files.

---

## Rollback

If anything goes wrong, re-deploy the previous working artefacts (`pmc-backend-v52cy.zip` + `pmc-frontend-v52cy-prod-build.zip`) via the same EB console / S3 sync + CloudFront invalidation. Keep both v52cy and v52cz-rev2 side-by-side until you've smoke-tested production.
