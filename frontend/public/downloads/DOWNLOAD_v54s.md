# PMC Managers — Release v54s (17 Jun 2026)

## THE ACTUAL ROOT CAUSE of "staff can't log in" (found & fixed)
Reproduced on production with a valid staff account:
- `POST /staff/auth/login` → **200** (login succeeds, cookie sent)
- `GET /staff/auth/me` → **401** immediately after → app bounces back to `/login`
  = "it does not login at all."

Why: the **session cookie (`access_token`) was set with `SameSite=Lax`**.
On preview the Emergent ingress rewrites cookies to `SameSite=None; Partitioned`
(so it worked there), but production CloudFront does not — so the browser
**dropped the Lax cookie**, and the very next request was unauthenticated.

`curl` worked because it stores/sends cookies regardless of SameSite.

## The fix (backend)
`access_token` (and the admin session cookie) are now set with the same
CHIPS attributes already used for `csrf_token`:
`HttpOnly; Secure; SameSite=None; Partitioned`. Logout now clears cookies with
matching attributes so a signed-out cookie is actually removed. Verified the
local backend emits the correct `Set-Cookie` header.

This affects ALL staff + admin logins (not just escrow). It is the real reason
staff login failed on production.

## Artifacts
- Backend (Elastic Beanstalk): `pmc-backend-v54s.zip`
- Frontend (S3 + CloudFront): `pmc-frontend-v54s-prod-build.zip`

## Deploy steps
1. Upload `pmc-backend-v54s.zip` to EB; wait green.  ← this is the one that fixes login
2. Sync the **contents** of `pmc-frontend-v54s-prod-build.zip` to S3 (NO `--delete`).
3. CloudFront invalidation for `/*`.
4. Confirm `https://www.pmcmanagers.com/api/v1/_version` → **v54s**.

(Deploy both — the version guard expects frontend and backend versions to match.)

## Verify after deploy
Log in a staff member (e.g. Site Certifier) → you land on `/staff` and stay
there. Sign out → sign in again → it works. No bounce back to the login screen.
