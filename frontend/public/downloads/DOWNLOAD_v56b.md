# PMC Managers — Release v56b (18 Jun 2026)

Fixes the production-only "CSRF token missing or invalid" on POST/PATCH/DELETE
(escrow Save, Backfill, etc.) that persisted even after v56a + CloudFront
invalidation + incognito.

## Root cause
The classic CSRF check required the `csrf_token` COOKIE to match the
`X-CSRF-Token` header. On the production path (behind CloudFront) the
csrf cookie was not reaching the origin, so every state-changing request
403'd — the auth (access_token) cookie worked, but the csrf cookie did not.

## Fix — session-bound HMAC CSRF token
The server now accepts EITHER:
1. the classic cookie == header (unchanged), OR
2. header == HMAC(secret, session) — derived from your already-authenticated
   access_token, so it needs **no csrf cookie at all** yet stays unforgeable
   from a cross-site context.

Login and the csrf-refresh endpoint now issue this session-bound token.
Verified: with the csrf cookie deliberately stripped, a protected POST passes
CSRF (no 403).

## Artifacts
- Backend: `pmc-backend-v56b.zip` (no .env / keys / tests)
- Frontend: `pmc-frontend-v56b-prod-build.zip`

## Deploy (one combined upload)
1. Backend zip → Elastic Beanstalk, wait green.
2. Frontend build contents → S3 root (overwrite).
3. CloudFront invalidation `/*`.
4. Footer should read **Frontend v56b · Backend v56b**; re-test escrow Save + Backfill.
