# PMC Managers — Release v52cz rev3

**Date:** 14 Feb 2026
**Scope:** Documents tab rebuilt from live data · "Download all" above the list · public per-file downloads · (includes everything from v52cz rev2)

> **Supersedes v52cz rev2** — deploy this rev3 bundle, not rev2.

---

## What's new in rev3 (vs rev2)

### Fix — Documents tab showed 5 rows but the pack zip had 2 files
The E-theme notice detail page shipped 5 **hard-coded demo document rows** (Scope of work, BOQ, Drawings, Draft contract — with dead `href="#"` buttons). Only row 1 was patched with the real file, so the tab claimed "Documents 5" while the tender had 1 real document. The pack zip was correct; the list was lying.

Now the Documents tab is **fully data-driven**:
- Rows are rebuilt from the notice's real documents (primary + attachments) — any count works (1, 3, 5, 20).
- Tab counter shows the real count; dropped entirely when 0.
- Each row has a **working** Download button → public per-file URL (`/api/v1/uploads/public-files/{key}?download=1`).
- New **"↓ Download all (N)"** button sits directly above the list and downloads one ZIP with every document (same pack endpoint as the hero button).

### Fix — notice documents not publicly downloadable
Files uploaded via `POST /notices/{ref}/document` were stored without a `scope` tag, so the public-files endpoint would 403 them. Now:
- New uploads are tagged `scope: "notice-attachments"` + `notice_ref`.
- The endpoint also accepts **legacy** `notice-docs/<ref>/...` keys, still gated on the parent notice being published.

## Carried over from rev2
- Blank registration form always auto-generated (sections A→E), canonical filename `PMC-Vendor-Registration-Form.pdf` — the "chaman raj resume.docx" leak is permanently blocked.
- Bundle picker on vendor bid submission (checkboxes, All/None, Download selected).
- Reg-doc view / Download pack CORS fix (relative `/api/v1/...` URLs).

## Verification
- Backend regression: **16/16 passed** (`test_v52cp_notices.py`, `test_v52cz_downloads.py`, `test_v52cz_blank_form.py`).
- Preview E2E on a seeded 5-document notice: 5 rows rendered with real names/sizes, per-file downloads 200, "Download all (5)" fetch → 200 `application/zip` containing all 5 PDFs + README.
- Legacy (pre-tag) notice files verified downloadable via public-files.

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev3.zip`](./pmc-backend-v52cz-rev3.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev3-prod-build.zip`](./pmc-frontend-v52cz-rev3-prod-build.zip) | S3 / CloudFront static assets (contents of CRA `build/`) |

Backend zip invariants: `Dockerfile` + `.ebextensions/` included; **no** `docker-compose.yml`, `.env`, `keys/`, or tests.

---

## Deployment steps

### Backend → AWS Elastic Beanstalk
1. Upload and deploy `pmc-backend-v52cz-rev3.zip` to the production EB environment.
2. Do not touch environment variables.
3. Smoke checks after deploy:
   ```
   curl -I "https://www.pmcmanagers.com/api/v1/vendors/registration-template?inline=false"
   # → 200, application/pdf, filename="PMC-Vendor-Registration-Form.pdf"
   curl -s "https://www.pmcmanagers.com/api/v1/notices/PMC-NOT-2026-0095/pack" -o pack.zip
   # → application/zip; unzip -l pack.zip lists every real tender document + README.txt
   ```

### Frontend → S3 + CloudFront
1. Unzip `pmc-frontend-v52cz-rev3-prod-build.zip` locally.
2. Sync to the S3 origin bucket (keep `index.html` + `asset-manifest.json` no-cache):
   ```
   aws s3 sync . s3://<your-origin-bucket> --delete \
       --cache-control "public, max-age=31536000, immutable" \
       --exclude "index.html" --exclude "asset-manifest.json"
   aws s3 cp index.html s3://<your-origin-bucket>/index.html --cache-control "no-cache, no-store, must-revalidate"
   aws s3 cp asset-manifest.json s3://<your-origin-bucket>/asset-manifest.json --cache-control "no-cache, no-store, must-revalidate"
   ```
3. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`

### Post-deploy smoke test (browser)
- Open https://www.pmcmanagers.com/notices/PMC-NOT-2026-0095 → **Documents tab shows exactly the real uploaded documents** (no fake "Scope of work / BOQ / Drawings" rows), counter matches, **Download all (N)** above the list returns a ZIP with all of them.
- Each row's **Download** saves the file directly (works for anonymous visitors too).
- Hero **Download pack** still works.

## Rollback
Re-deploy `pmc-backend-v52cy.zip` + `pmc-frontend-v52cy-prod-build.zip` (or rev2) the same way if anything smokes wrong.
