# PMC Managers Limited — Release v49w

## What's fixed (4 issues)
### 1. DocuSign resend didn't send emails
Root cause: the resend endpoint called `ModifyRecipients` with
`resend_envelope="true"`, but the only "change" was re-assigning the
signer email to **the same value** DocuSign already had. DocuSign
treats that as a no-op and skips the reminder email. Both the list-
view Resend and the detail-view Resend hit the same path.

Fix (`backend/routers/docusign.py` resend_envelope):
- Primary path now uses envelope-level `envelopes.update(…, envelope=
  Envelope(status="sent"), resend_envelope="true")` — the documented
  DocuSign call that forces a reminder email without mutating
  recipients.
- Fallback (if the SDK variant rejects the envelope update) still uses
  `update_recipients`, but now also refreshes the signer's name on
  the first signer so the diff is non-empty and the resend actually
  fires.
- Response includes `resent_to: <email>` so the UI toast can confirm
  which inbox the reminder went to.

### 2. Admin left sidebar scrolled away with the page
Root cause: `.pmc-side` had `position: relative` which lets the
sidebar scroll out of view in long admin pages (Notices, Bidding,
Vendors, …).

Fix (`frontend/src/pmc-responsive.css`, desktop ≥1101 px only — mobile
drawer unchanged):
`[data-ui="e"] .pmc-adm > aside.pmc-side` → `position: sticky; top: 0;
height: 100vh; overflow-y: auto; align-self: start;` with a thin
custom scrollbar.

### 3. Sign-out routed to the old portal-specific login
Root cause: `AdminAvatarMenu.onSignOut` redirected to `/admin/login`
(a legacy route), confusing admins who expected the unified `/login`.

Fix (`frontend/src/apps/admin-console-e/AdminAvatarMenu.jsx`):
`navigate("/login", { replace: true })` after the logout call.
Supplier side was already landing on `/login` (handleSignOut in
PmcLinkPatcher).

### 4. "Open the full Help Centre" / FAB didn't open on the first page
Root cause: `PmcLinkPatcher` fired the help trigger by calling
`document.querySelector(".pmc-helpfab")?.click()`. Each Option-E page
embeds its OWN static `.pmc-helpfab`; `querySelector` returned that
static button first, whose click just re-fired the delegated handler.
After navigating to another page and back, DOM re-ordering happened
to put the React FAB first, which is why it "worked after any tab".

Fix (`PmcLinkPatcher.jsx` + `PmcHelpDrawer.jsx`):
- Patcher dispatches `window.dispatchEvent(new CustomEvent("pmc:open-
  help"))` on every data-help-open click / Help label.
- `PmcHelpDrawer` listens for `pmc:open-help` and flips its React
  state to `open=true` directly — works on the very first page load.

Service-worker cache bumped to `pmc-shell-v49w-rev1`.

## Bundles
* Frontend: `pmc-frontend-v49w-prod-build.zip` (same-origin,
  REACT_APP_BACKEND_URL=""). Includes v49r + v49s + v49t + v49u + v49v.
* **Backend: `pmc-backend-v49w.zip`** — ships the DocuSign resend
  fix. REQUIRED to make resend actually email the signer.

## Deploy
Frontend — S3 + CloudFront:
1. Unzip `pmc-frontend-v49w-prod-build.zip`
2. `aws s3 sync --delete` into the bucket root
3. CloudFront invalidation `/*`

Backend — Elastic Beanstalk:
1. Upload `pmc-backend-v49w.zip` to the `pmc-backend-prod` environment
2. Wait for Health = OK

Verify:
- Admin dashboard: sidebar stays fixed while right pane scrolls.
- Admin DocuSign → Resend on a `sent` envelope → signer receives
  the reminder email; toast says "Resent to <email>".
- Admin or Vendor → Sign out → lands at `https://www.pmcmanagers.com/
  login`.
- Fresh page load → Help FAB opens the drawer on the first click.

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
