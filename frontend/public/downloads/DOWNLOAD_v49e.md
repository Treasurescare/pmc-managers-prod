# PMC Managers Limited — Release v49e

## What's new in v49e

### 1 · Real "Forgot password?" reset flow (vendor + admin/staff)
- **Backend** `routers/password_reset.py` — three endpoints under
  `/api/v1/auth/password-reset`:
  - `POST /request  {email, portal}` — always returns `{ok:true}`
    (no user enumeration). Mints a 30-minute JWT with a fresh `jti`,
    persists the `jti` on the user record, and emails the reset link
    via the Option E `account.password_reset` template (`02-password-reset.html`).
  - `POST /verify   {token}` — returns `{ok, email, portal}` when the
    signature + `jti` still match; 400 otherwise.
  - `POST /confirm  {token, new_password}` — writes `password_hash`,
    clears `must_change_password`, unsets the stored `jti` so the
    link cannot be replayed, and sends `account.password_changed`
    (`03-password-changed.html`) as confirmation.
- **Frontend** two new Option E screens:
  - `/forgot-password` — `ForgotPasswordE` with portal picker
    (Supplier / PMC staff · Admin), one email field, "Check your inbox"
    confirmation state.
  - `/reset-password?token=…` — `ResetPasswordE` with three states:
    `verifying` → `ready` (with strength meter) → `done`, plus an
    `invalid` state with a "Request a new link" CTA when the JWT is
    stale/expired/replayed.
- **Sign-in wiring** — the "Forgot password?" link on `/login` now
  routes to the new page (it previously pointed to `#`).
- `data-testid`s across every element: `forgot-form`, `forgot-email`,
  `forgot-portal-vendor|staff`, `forgot-submit`, `forgot-sent-panel`,
  `reset-form`, `reset-new`, `reset-confirm`, `reset-submit`,
  `reset-invalid`, `reset-done`, `reset-request-new`, `reset-go-signin`.

### 2 · Vendor change-password UI upgraded to Option E chrome
- Rewrote `/app/frontend/src/apps/vendor-portal/VendorChangePassword.jsx`
  from the old Navy Tailwind card into the same two-column Option E
  layout as sign-in: forest-green left rail with brass display quote,
  cream right column with the form. Adds:
  - Password-strength meter (Too short → OK → Good → Strong).
  - Live mismatch hint when Confirm ≠ New.
  - "Same as temporary" guard so users can't recycle the emailed password.
  - "Lost the temporary password? Request a reset link" shortcut into
    the new `/forgot-password` flow.
  - `data-testid`s preserved for the testing agent.

## Verified live
- `POST /api/v1/auth/password-reset/request` → 200 for known + unknown emails.
- `POST /api/v1/auth/password-reset/verify` → 400 for bogus token, 200 for real.
- `POST /api/v1/auth/password-reset/confirm` → 200; replay of same token → 400.
- Vendor login with rewritten password → 200.
- `/forgot-password` and `/reset-password?token=badtoken` render Option E
  chrome; invalid state shows the correct link-problem card.

## Bundles
- **Frontend:** `pmc-frontend-v49e-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront ready)
- **Backend:** `pmc-backend-v49e.zip`
  (`Dockerfile`, `Dockerrun.aws.json`, `.platform/` at zip root as EB requires)

## Deploy
- **Frontend to S3** — unzip into bucket root, invalidate CloudFront `/*`.
- **CloudFront SPA rule** (still required) — custom error responses:
  both `403` and `404` → `/index.html` with HTTP `200`.
- **Backend to Elastic Beanstalk** — upload the zip; no new env vars.
  The reset router uses the existing `JWT_SECRET`, `FRONTEND_URL`,
  `RESEND_API_KEY`, and `EMAIL_FROM_ADDRESS`.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49d` if needed.
