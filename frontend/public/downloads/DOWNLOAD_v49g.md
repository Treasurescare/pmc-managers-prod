# PMC Managers Limited — Release v49g

## What's new in v49g

### Admin Registrations — uploaded documents are now genuinely viewable
The reviewer panel (Admin → Registrations → select an applicant) listed the
uploaded KYC documents but the tiles were inert-looking and the plain
`<a href>` View/Download anchors broke on cross-origin previews, corporate
proxies and in-app WebViews (dropped `Content-Disposition`, missing cookies).

Rebuilt the documents block (`RegistrationsPanel.jsx` → new `RegDocCard`):

- **Every document card now shows**: slot name, real file name, MIME type,
  and size in KB — so the reviewer can see at a glance what was uploaded.
- **View** — fetches the file via axios (`withCredentials`, so the admin
  session cookie is always attached), builds a Blob URL, and:
  - Images (`image/*`) → inline preview under the card.
  - PDFs (`application/pdf`) → inline `<iframe>` preview under the card.
  - Other types → opens the Blob URL in a new tab.
  - Click again to hide the preview (toggle).
- **Download** — same Blob pipeline, then a programmatic
  `<a download="real-file-name">` click so the file saves with its original
  name on every platform (Android, desktop, WebView).
- **Busy states** — `Opening…` / `Saving…` while fetching; Blob URLs are
  tracked in a ref and revoked on unmount (no memory leaks).
- `data-testid`s: `reg-doc-<slot>`, `reg-doc-view-<slot>`,
  `reg-doc-download-<slot>`, `reg-doc-preview-<slot>`.

### Dark-tile rendering bug fixed
The Option E global override `[data-ui="e"] .bg-slate-50 { background:
var(--e-bg-deep) }` (`index.css`) was repainting the registration doc cards
deep green while the text stayed dark — making them look like empty black
boxes. Added a scoped exclusion
(`[data-ui="e"] [data-testid^="reg-doc-"]`) restoring a light card with
readable ink. Cards now show slot name, file name, MIME type and size.

### Verified live
- `GET /api/v1/uploads/files/registration-docs/<id>/incorporation_certificate/<uuid>_upload.pdf`
  → **HTTP 200**, `content-type: application/pdf`, `Content-Disposition: inline; filename="upload.pdf"`.
- Registrations list API returns `document_slots` with `url`, `file_name`,
  `content_type`, `size_bytes` for each uploaded doc.
- Frontend production build passes (36 s, no preview-URL refs).

## Everything from v49f still applies
- Vendor portal in-page CTAs + KPI tiles wired.
- Password-reset rate limiting (60 s per email, 10 per 5 min per IP).
- Real forgot-password flow + Option E vendor change-password.

## Bundles
- **Frontend:** `pmc-frontend-v49g-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront ready)
- **Backend:** `pmc-backend-v49g.zip` — no backend code change vs v49f;
  re-packaged only so you have a matched pair.

## Deploy
- **Frontend to S3** — unzip into bucket root, invalidate CloudFront `/*`.
- **CloudFront SPA rule (still required)** — custom error responses:
  both `403` and `404` → `/index.html` with HTTP `200`.
- **Backend** — skip if v49f is already deployed (identical contents).

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49f` if needed.
