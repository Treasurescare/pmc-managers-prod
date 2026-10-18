# PMC Managers — Release v54v (17 Jun 2026)

## Fixes the unified `/login` page (staff could log in via /staff/login but NOT /login)

### Root cause
CloudFront's SPA "Error Pages" rule rewrites a backend **403/404 on `/api/*`**
into the app's `index.html` with **HTTP 200**. The unified `/login` "PMC staff"
option tries each staff role in turn to find the one you hold. The first
(wrong-role) attempt got a `403` from the backend, which CloudFront turned into
a fake `200` + HTML page. The app mistook that for a successful sign-in,
navigated to `/staff` with **no session cookie**, then `/me` returned 401 and
bounced you back to `/login?expired=1`. (`/staff/login` worked because you pick
your exact role there, so no wrong-role attempt happens.)

### The fix (client-side, robust)
1. A central guard now inspects every `/api` response: if the body is HTML
   (a CloudFront error page) it is treated as the error it really is, instead
   of a success. This protects the staff login loop, the escrow login, and any
   future call from CloudFront's HTML-200 error pages.
2. The unified staff login only treats a proper JSON object with an
   `active_role` as a successful sign-in.

Result: signing in from `/login` as "PMC staff" now probes your roles
correctly, finds the one you hold, sets the session cookie, and lands you on
`/staff`.

### Optional but recommended (complete, server-side fix)
The underlying issue is the CloudFront **"Error pages"** (custom error
responses) that map `403 -> /index.html (200)` and `404 -> /index.html (200)`.
Those are needed so the FRONTEND deep-links work on refresh, but they also
corrupt `/api` error responses. The clean long-term fix is to do SPA routing
with a **CloudFront Function** (viewer-request) instead of custom error
responses, so `/api` errors pass through untouched. Ask and I'll give exact
steps. The v54v client guard makes the app correct even without this change.

## Artifacts
- Backend: `pmc-backend-v54v.zip` (identical to v54u + version bump; no DocuSign key)
- Frontend: `pmc-frontend-v54v-prod-build.zip`

## Deploy
1. Frontend: upload contents of `pmc-frontend-v54v-prod-build.zip` to S3,
   then CloudFront invalidate `/*`. (This is the fix.)
2. Backend: upload `pmc-backend-v54v.zip` to Elastic Beanstalk (keeps the
   version in sync with the frontend so the self-heal stays quiet).
3. Test: sign in at `/login` as "PMC staff" → you should land on `/staff`.
