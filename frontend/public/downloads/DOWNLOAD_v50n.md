# PMC Managers — Release v50n

## Company & KYC page — fully wired (was static mockup)
- `VendorCompanyKycE.jsx` rewritten on the shared `VendorPortalChrome`.
- Tab bar (Licences & certificates / Company documents / Team & roles /
  Bank accounts / Reviews) now switches panels client-side — no more
  dead tabs.
- Live header: KYC status, supplier ref, categories count, rating — all
  from `/api/v1/vendor/auth/me`.

## Licences & certificates CRUD (new)
- Backend `routers/vendor_licenses.py` + `vendor_licenses` collection:
  - `GET    /api/v1/vendor/licenses` — list + computed status
    (valid / expiring ≤45d / expired) + KZ catalogue + "missing" list
  - `POST   /api/v1/vendor/licenses` — add (dedupes per type+country)
  - `PUT    /api/v1/vendor/licenses/{id}` — renew / edit
  - `DELETE /api/v1/vendor/licenses/{id}` — remove
  - `GET    /api/v1/vendors/{ref}/licenses` — admin read view
- Optional certificate upload via existing uploads presign+direct flow.
- "KYC gap" callout now reflects real expiring/expired/missing counts.

## Profile edit dialog — phone & labels
- Email field label now reads "New email"; reason label reads
  "Reason for the change (optional)".
- Mobile / Office phone fields now show a country-code dropdown
  (30 countries, auto-prefilled with the vendor's registered country),
  locked `+dial` prefix, and per-country digit validation
  (e.g. India = 10 digits, KZ = 10, Oman = 8). Submit is disabled until
  the digit count matches; inline error names the country rule.
- Backend receives the full E.164 number (`+919876543210`).

## Signatures page — Download button only when a PDF exists
- `GET /api/v1/docusign/mine` now returns `has_document` per envelope
  (probes DocuSign `list_documents` for completed envelopes).
- Rows with no archived document show "PDF not archived — ask PMC to
  regenerate" instead of a Download button that 404s.

## Regression fix
- v50m's vendorApi rewrite accidentally dropped `myCategories` /
  `requestCategory` (v50l), crashing /vendor/categories. Restored;
  page verified rendering + request flow intact.

## Deploy
- Backend: `pmc-backend-v50n.zip` → EB.
- Frontend: `pmc-frontend-v50n-prod-build.zip` → S3 + CF invalidate.
- No new env vars required.

## Testing
- Backend curl: licence list/add/renew/409-duplicate/delete all pass.
- Browser: Categories page renders, KYC tab bar switches panels,
  phone dialog rejects 9-digit IN number with named error and accepts
  10 digits, Submit enables only when valid.
