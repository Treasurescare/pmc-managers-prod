# PMC Managers — Release v54p (17 Jun 2026)

## Why this release
A production recording showed a staff account set to **admin + escrow_agent**
crashing on login — "Signed in · undefined" and a blank `/undefined` screen.

**That crash is from the STALE build currently on production**, not from the
current code. On the current code:
- the backend always returns a real active role (never `undefined`),
- the login page navigates only to `/admin` or `/staff` (never `/undefined`),
- an ErrorBoundary catches any render error (no blank white screen).

## What v54p adds (login hardening)
- The "PMC staff" sign-in card now also tries **admin** as a fallback, so an
  account that holds `admin` plus a high-risk role signs in cleanly as admin.
- Login success never reads an undefined role; navigation is always safe.
- If the only matching role is high-risk (escrow_agent / legal_counsel /
  accounting) without MFA, the exact "enable 2FA from the admin portal" message
  is shown instead of a generic error.
- Includes the v54o staff RBAC guard (specialists cannot open the admin console).

## Artifacts
- Backend (Elastic Beanstalk): `pmc-backend-v54p.zip`
- Frontend (S3 + CloudFront): `pmc-frontend-v54p-prod-build.zip`

## Deploy steps
1. Upload `pmc-backend-v54p.zip` to EB; wait for green/healthy.
2. Sync the **contents** of `pmc-frontend-v54p-prod-build.zip` to S3 (NO `--delete`).
3. CloudFront invalidation for `/*`.
4. Confirm `GET https://www.pmcmanagers.com/api/v1/_version` returns **v54p**
   and the footer shows Frontend v54p / Backend v54p.

> Deploying the v54p BACKEND is what makes every stale browser auto-refresh:
> the version guard compares the loaded build against `/api/v1/_version` and, on
> mismatch, clears caches + unregisters the service worker and reloads once.

## Verify after deploy
- Sign in a staff who holds admin (± escrow_agent) via "PMC staff" → lands on the
  admin console (no `/undefined`, no blank screen).
- Sign in an escrow_agent-only account without MFA → clear "enable 2FA" message.
