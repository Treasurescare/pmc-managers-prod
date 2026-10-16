# PMC Managers Limited — Release v49v

## What's fixed
### Safari: DocuSign "Review & sign" never opened (popup blocker)
User report: in Safari, clicking Review & sign / Preview on a document
does not open the DocuSign page.

Root cause (frontend only): every signing flow called `window.open()`
**after** an `await` on the DocuSign API (minting the recipient-view
URL). Safari only permits popups synchronously inside the click gesture;
once the handler awaits, the open is silently blocked — no tab, no
error. Chrome sometimes allows it, which is why it only showed in
Safari.

Fix pattern applied everywhere a URL is opened after an async call:
1. `window.open("", "_blank")` synchronously inside the click (shows a
   "Contacting DocuSign…" placeholder).
2. When the API responds, steer that tab to the signing/consent/PDF URL.
3. If even the synchronous open was blocked, fall back to same-tab
   navigation so the user ALWAYS reaches DocuSign.
4. On error paths (no pending envelope, API failure) the placeholder
   tab is closed again.

Files fixed:
- `components/PmcLinkPatcher.jsx` — vendor Signatures page
  Review & sign / Preview / Continue (shared `_openSteeredTab` /
  `_steerTab` / `_closeTab` helpers) + envelope PDF preview.
- `apps/vendor-portal/VendorSignatures.jsx` — legacy vendor award
  signing popup.
- `apps/admin-console/DocuSignPanel.jsx` — admin Sign + Resend envelope,
  including the consent-URL redirect on `DOCUSIGN_CONSENT_REQUIRED`.
- `apps/admin-console/AwardsPanel.jsx` — award signing + consent
  redirect.
- Service-worker cache bumped to `pmc-shell-v49v-rev1`.

Verified on preview (Chromium): clicking Review & sign opens the tab
instantly within the click gesture (popup event fires before the API
call completes) — this is precisely the behaviour Safari requires.

## Bundles
* Frontend: `pmc-frontend-v49v-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront).
  **Includes v49r (downloads) + v49s (sign-in⇄register) + v49t
  (dashboard counts) + v49u (notifications)** — deploy only this one.
* Backend: unchanged — `pmc-backend-v49q.zip` (already live).

## Deploy — Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49v-prod-build.zip`.
2. `aws s3 sync --delete` the contents into your S3 bucket root.
3. Invalidate CloudFront: paths `/*`.
4. Verify in Safari: Vendor portal → Signatures → Review & sign opens
   DocuSign in a new tab (or same tab if popups are fully blocked).

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
