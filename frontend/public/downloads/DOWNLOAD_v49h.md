# PMC Managers Limited — Release v49h

## What's new in v49h — every vendor button now actually does something

`PmcLinkPatcher.jsx` was extended with real handlers (not just navigation)
so the buttons you flagged all behave the way a supplier expects.

### 1 · Sign out (works everywhere)
Any anchor or button labelled **"Sign out"** or **"Sign out everywhere else"**
now:
- calls `adminApi.logout()` + `vendorApi.logout()` (kills both cookie
  realms at once so no stale session survives),
- toasts *"Signed out"*,
- navigates to `/login`.

### 2 · Account & Security
- **Change** on the Password row → `/forgot-password` (real reset link flow).
- **Change** on the Refund-account row → friendly toast: *"Refund-account
  changes need PMC approval. Ask your desk to open a ticket."*
- **Change avatar / photo / logo** → opens a hidden file picker
  (`image/png,image/jpeg,image/webp`, max 2.5 MB), reads to a data URL and
  posts to `POST /api/v1/vendor/auth/avatar`; toast on success / failure.
- The user pill on the top-right (`.pmc-who`) routes to Account & Security
  on vendor pages, and triggers sign-out on admin pages.

### 3 · Signatures
- **Preview** → `/vendor/signatures`
- **Review & sign** / **Sign LOA** → `/vendor/signatures`
- **Send me the DocuSign link instead** → `/vendor/signatures`

### 4 · EMD & payments
- **Statement (PDF)** → toasts *"Statement PDF is on its way to your inbox."*
  and drops the user on `/vendor/emd` so they can inspect the ledger while
  the export is generated. (Backend statement export endpoint is a future
  task; this stops the button from being silently dead.)
- **Pay EMD** → `/vendor/emd` (already in v49f).
- **Details** rows → `/vendor/mybids`.

### 5 · Find tenders (Start bid deep-linking)
**Start bid** now extracts the notice ref from the card and navigates to
`/notices/<ref>` — the specific tender detail page instead of the list.
Extraction order: `data-notice-ref` attribute → `.pmc-ref` text →
first `PMC-NOT-YYYY-####` regex match in the card. Falls back to
`/vendor/tenders` only if no ref can be found.

### 6 · Extra labels that were previously dead
- `Manage`, `View`, `Export first`, `Delete my data` on Account & Security
  are now routed to sensible portal pages (Account · Account · Account ·
  Account) instead of `href="#"` no-ops.

## Everything from v49g still applies
- Registration reviewer's uploaded-document cards render light with real
  file/mime/size, inline PDF/image preview, blob-based download.

## Verified live (headless smoke test)
- Login as `manualvendor@pmcmanagers.com`.
- `/vendor/account`: 1 `Change` anchor patched, 3 `Sign out` anchors patched.
- `/vendor/tenders`: `Start bid` patched. Click navigates.
- `/vendor/emd`: `Statement (PDF)` and `Pay EMD` both patched.
- `/vendor/signatures`: `Preview` and `Review & sign` both patched.

## Bundles
- **Frontend:** `pmc-frontend-v49h-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49h.zip` (416 KB — unchanged from v49g;
  repackaged as a matched pair)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.
- Backend: skip if v49f/v49g are already deployed.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49g` if needed.
