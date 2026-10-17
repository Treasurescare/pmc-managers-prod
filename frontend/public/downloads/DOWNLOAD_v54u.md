# PMC Managers — Release v54u (17 Jun 2026)

## THE real root cause (finally) — Safari rejecting the session cookie

Staff login on your real domain succeeded (`POST /staff/auth/login` → 200) but
the browser was **immediately logged out** (`GET /staff/auth/me` → 401) and
bounced back to `/login`.

Proven with live tests against production:
- **Server + CloudFront are correct.** A clean Chromium browser logs in,
  `/me` returns 200, and lands on `/staff` with no bounce. `curl` login
  returns `Set-Cookie` and `/me` works.
- It failed in **Safari** (incl. Private) and the user's browser — even in
  Incognito. So it was never a cache problem and never a CloudFront problem.

The backend was setting the session cookie with **`SameSite=None; Partitioned`
(CHIPS)**. That attribute set is needed only for the Emergent *preview* sandbox,
which runs the app in a **cross-site iframe**. On your real, **same-origin**
domain (`www.pmcmanagers.com` serving both the site and `/api`), that is the
wrong cookie type — **Safari/ITP rejects it first-party**, so the cookie is
never stored and the very next request is unauthenticated.

## The fix (in this build)

The backend now sets cookies **based on context**:
- **Production / same-origin (your domain, localhost):** `SameSite=Lax; Secure`
  — a normal first-party cookie that every browser, including Safari, keeps.
- **Preview sandbox (cross-site iframe only):** keeps `SameSite=None; Secure;
  Partitioned` so the preview still works.

Context is detected from the request `Origin`: only the
`*.preview.emergentagent.com` sandbox is treated as cross-site; everything else
is first-party. Applies to the staff login, admin login, role-switch and logout
cookie-clearing paths (clears now match the set attributes, so logout fully
removes the cookie).

Verified locally (the exact code that ships):
- Production-origin login → `access_token` + `csrf_token` = **`SameSite=Lax`**,
  `/me` = 200.
- Preview-origin login → both stay **`SameSite=None; Partitioned`**.

No CloudFront change is needed for this (your `/api/*` behaviour is already
CachingDisabled + AllViewer, which is correct — keep it).

## Artifacts
- Backend: `pmc-backend-v54u.zip`  (no DocuSign key, no `.env`)
- Frontend: `pmc-frontend-v54u-prod-build.zip`

## Deploy
1. **Backend (this is the fix):** upload `pmc-backend-v54u.zip` to Elastic
   Beanstalk, wait until the environment is green.
2. **Frontend:** upload the contents of `pmc-frontend-v54u-prod-build.zip` to
   S3, then invalidate CloudFront `/*` (keeps versions in sync so the
   self-heal/version-guard stays quiet).
3. Test in **Safari**: sign in at `/staff/login` → you should land on `/staff`
   and stay there.
