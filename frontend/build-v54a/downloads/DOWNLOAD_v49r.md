# PMC Managers Limited — Release v49r

## What's fixed
### File download & view links everywhere (the "dead links" bug)
Root cause: `PmcLinkPatcher.jsx` routes EVERY in-app click through global
event delegation. Any anchor with a real backend href (e.g.
`/api/v1/uploads/files/...pdf`) inside an Option-E page was being pushed
into the React SPA router via `navigate(href)`. No route matches `/api/...`,
so the click rendered a blank/dead page — downloads never started and
"view" links never opened. This hit admin bid-detail attachments, notice
documents and any page with real file hrefs.

Fix (2 changes in `PmcLinkPatcher.jsx`):
1. `handleDownload` — when the anchor already carries a real `/api/...`
   file href, it now forces the attachment download itself
   (`?download=1` + temp `<a download>`) instead of falling through.
2. Generic href handler — `/api/...` and `/downloads/...` hrefs are no
   longer sent to the SPA router; the browser opens them natively
   (inline view in a new tab where `target="_blank"` is set, or the
   backend's `Content-Disposition` decides).

Verified on preview: notice detail document download fires
(`fake_tender.pdf` saved, "Download started" toast). Verified on
production before the fix: backend already serves
`Content-Disposition: attachment` with `?download=1` and `inline`
without it — only the frontend click handler was broken.

## Bundles
* Frontend: `pmc-frontend-v49r-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront;
  `main.7fd85d7d.js`)
* Backend: unchanged — keep `pmc-backend-v49q.zip` (already live and
  confirmed serving downloads correctly).

## Deploy — Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49r-prod-build.zip`.
2. `aws s3 sync --delete` the contents into your S3 bucket root.
3. Invalidate CloudFront: paths `/*`.
4. Verify: open any notice → Documents tab → Download (file saves);
   admin bid detail → attachment Download/View links (file saves / opens).

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
