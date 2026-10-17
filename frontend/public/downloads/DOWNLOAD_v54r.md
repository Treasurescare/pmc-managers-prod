# PMC Managers — Release v54r (17 Jun 2026)

## THE REAL ROOT CAUSE of the recurring login crash
Production was already serving v54q code on the server, yet your browser kept
running the OLD, pre-fix code (the one that navigates to `/undefined`). Why:

1. The service worker's `CACHE_VERSION` was accidentally frozen at `pmc-shell-v54n`
   across v54o/v54p/v54q. Because the `service-worker.js` bytes never changed,
   browsers considered the SW "unchanged", never installed a new one, and kept
   serving the **old cached v54n JavaScript** — i.e. the old buggy login.
2. CloudFront also caches `/service-worker.js` and `/index.html` with no
   no-cache header, so even new uploads were masked at the edge.

`curl` showed v54q because curl bypasses the service worker — your browser did not.

## The fix in v54r
- Bumped the service worker to `pmc-shell-v54r`. Now the `service-worker.js`
  bytes DO change on deploy, so every browser installs the new SW, its `activate`
  purges the stale `pmc-shell-v54n` cache, and the old JS is gone for good.
- Carries everything from v54o–v54q: staff RBAC guard, no-escalation login,
  clear MFA message, and the Account type (Admin/Staff) flag.

## Artifacts
- Backend (Elastic Beanstalk): `pmc-backend-v54r.zip`
- Frontend (S3 + CloudFront): `pmc-frontend-v54r-prod-build.zip`

## Deploy steps — the CloudFront invalidation is MANDATORY this time
1. Upload `pmc-backend-v54r.zip` to EB; wait green.
2. Sync the **contents** of `pmc-frontend-v54r-prod-build.zip` to S3 (NO `--delete`).
3. **CloudFront → Invalidations → create `/*`** (this MUST clear
   `/service-worker.js` and `/index.html`, or browsers keep the stale SW).
4. In your browser, load the site; it may reload once as the new SW takes over.
   Confirm the footer shows Frontend v54r / Backend v54r.

## Recommended (prevents this forever)
In S3/CloudFront, set `Cache-Control: no-cache` on `service-worker.js` and
`index.html` so the edge never serves a stale shell. Hashed `/static/*` files
can stay long-cached (their names change every build).

## Verify after deploy
- Log in a staff member, sign out, log in again — no blank `/undefined` screen.
- Masters → Staff shows the Account type (Admin/Staff) selector.
