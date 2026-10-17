# PMC Managers — Release v54t (17 Jun 2026)

## THE actual root cause (proven in your live browser)
Staff login on production: `POST /staff/auth/login` → 200, but the browser
received the response **without a Set-Cookie header**, with
`x-cache: Error from cloudfront` and `age: 154` — i.e. a **CACHED** response.
So the session cookie never reached the browser → `GET /staff/auth/me` → 401 →
app bounces back to `/login` = "staff can't log in".

`curl` worked because it hit a fresh (uncached) response that DID include the
cookie. Preview has no CloudFront, so it always worked there.

**CloudFront is caching your `/api/*` responses and stripping Set-Cookie.**

## Two-part fix

### 1. Code (in this build) — force API responses uncacheable
A middleware now sets `Cache-Control: no-store` (+ `Vary: Cookie, Authorization`)
on every `/api/*` response, so a well-behaved CDN won't cache them.

### 2. CloudFront configuration (YOU must do this — it's the authoritative fix)
If your CloudFront cache policy ignores origin cache headers (fixed TTL), the
code change alone won't be enough. In the CloudFront distribution:
1. Create a **cache behavior** for path pattern `/api/*`.
2. Cache policy = **CachingDisabled** (AWS managed).
3. Origin request policy = **AllViewer** (forwards all headers, cookies, query strings).
4. Allowed methods = GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE.
5. Make sure this `/api/*` behavior has HIGHER precedence than the default.
6. Save, then create an invalidation for `/*`.

After that, API responses (including login) are never cached, Set-Cookie reaches
the browser, and staff login works.

## Artifacts
- Backend: `pmc-backend-v54t.zip`
- Frontend: `pmc-frontend-v54t-prod-build.zip`

## Deploy
1. Backend zip → EB (wait green).
2. Frontend contents → S3 (no `--delete`).
3. Apply the CloudFront `/api/*` CachingDisabled behavior above.
4. CloudFront `/*` invalidation.
5. Verify `/api/v1/_version` → v54t, then log a staff member in → stays on `/staff`.
