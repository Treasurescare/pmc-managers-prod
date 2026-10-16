# PMC Managers Limited — Release v49s

## What's fixed
### Sign-in ⇄ Register cross-links (kills the dead-end confusion)
User report: clicking "bid" on a notice from the home page lands on the
sign-in page with no obvious way to register as a new vendor, and the
registration page has no way back to sign-in for existing suppliers.

Fixes:
1. **Sign-in page (`/login`)** — new prominent full-width outlined button
   under the Continue button, separated by a "New supplier?" divider:
   **"Register as a supplier — free, ~15 minutes"** → `/register`.
   (The small text link at the top is kept as well.)
   Testid: `signin-register-btn`.
2. **Registration page (`/register`)** — new footer note inside the form:
   **"Already registered? Sign in to your supplier account"** → `/login`.
   Testid: `reg-start-signin-link`.
3. Service-worker cache bumped to `pmc-shell-v49s-rev1` so returning
   visitors pick up the new build instead of a cached shell.

Verified on preview: button renders on `/login`; register-page link
navigates to `/login`.

## Bundles
* Frontend: `pmc-frontend-v49s-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront;
  `main.c0d42a52.js`). **Includes the v49r download-link fix** — deploy
  v49s instead of v49r.
* Backend: unchanged — `pmc-backend-v49q.zip` (already live).

## Deploy — Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49s-prod-build.zip`.
2. `aws s3 sync --delete` the contents into your S3 bucket root.
3. Invalidate CloudFront: paths `/*`.
4. Verify: `/login` shows the "Register as a supplier" button;
   `/register` shows "Already registered? Sign in"; notice → Documents →
   Download saves the file.

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
