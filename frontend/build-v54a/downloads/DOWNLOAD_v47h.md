# PMC Managers v2 — Release v47h (Sep 2026)

## What is in this release

### Admin bid detail is now a full PAGE + vendor uploads are actually viewable
- **Root cause fixed**: bid documents stored only a storage `key`, never a servable
  `url`/`mime` — so admin and vendor detail views could not open or preview any vendor
  upload. Both `GET /api/v1/bids/admin/{id}` and vendor `GET /api/v1/bids/{id}` now
  enrich every document with a working URL (`/api/v1/uploads/files/{key}`) and mime type,
  including all pre-existing bids (no data migration needed).
- **View button now opens a dedicated page** (`/admin/bids/{bidId}`) instead of a modal —
  the entire bidder entry: submission meta, commercial + EMD breakdown, technical &
  commercial notes, **every uploaded document** with kind badge (technical / commercial /
  supporting), size, Open + Download buttons, and inline preview for images and PDFs,
  plus full workflow history and Print/Save-PDF.

### Carried over from v47g (same bundles)
- Platform-wide pagination (10/20/30/All) across all 20 admin + vendor listings.
- DocuSign per-row View / Resend (unsigned) / Print (signed).
- DocuSignPanel conditional-hook crash fix.

## Verification
- Backend: admin bid detail on `PMC-BID-2026-00017` returns 3 enriched documents;
  file fetch returns `200 image/jpeg 230,776 B`. Lint: 0 errors.
- Frontend smoke: View → `/admin/bids/{id}` page renders all sections, 3 Open buttons,
  3 inline previews; document link fetches 200.
- Production build scanned: **0 preview-URL references**; SW cache `pmc-shell-v47h`.

## Bundles
- `pmc-backend-v47h.zip` — Elastic Beanstalk.
- `pmc-frontend-v47h-prod-build.zip` — S3/CloudFront (excludes downloads/).

## Deploy notes
- Frontend: upload ALL files including `static/`; no-cache on `index.html`,
  `service-worker.js`, `manifest.json`; CloudFront invalidation `/*`.
- Backend: no new env vars.
