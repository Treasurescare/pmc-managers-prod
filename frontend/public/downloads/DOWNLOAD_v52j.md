# PMC Managers · v52j deployment bundle

Build date: 15 Oct 2026 · supersedes v52i.

## What's new in v52j (on top of v52i)

- **Magic-link signatory claim no longer throws "HTTP 401 Invalid email or password".** `POST /escrow-signatories/claim` now sets the session cookie and returns the CSRF token itself; the frontend stopped calling `/auth/login` immediately after a successful claim, so there's no race / autofill mismatch. One request, one toast, straight to `/escrow/me`. If the user ever returns later, standalone email+password sign-in continues to work the same way.

## Carried forward from v52i / v52h
- Escrow password reset posts to the right endpoint (account first, signatory fallback). Legacy approved institutions self-recover via `Forgot password` auto-claim. `/forgot-password` has an Escrow Institution option.
- CSRF cookie set with `Secure; SameSite=None; Partitioned`.
- `_require_any_signed_in` accepts escrow account + signatory cookies.
- `uploadsApi.openFile(key)` opens files via blob-fetch, bypassing partitioned-cookie new-tab block.
- Unified `/login` routes Escrow Institution to the account endpoint first.
- `uploadsApi.uploadFile` chains presign + direct — upload crash gone.
- Institution profile change-request workflow + admin approve/reject.
- Admin Escrow Institutions filters: search + from/to date + status + reset.
- Sign-out routes to unified `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52j.zip`
- Frontend static build: `/downloads/pmc-frontend-v52j-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → backend environment → **Upload and deploy** → `pmc-backend-v52j.zip`.
2. Wait for green; hit `/api/health`.
3. Confirm env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`.

ZIP layout: `Dockerfile` + `.dockerignore` + `.ebextensions/` at root. No `docker-compose.yml`. No `.env` inside.

### Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v52j-prod-build.zip`, `aws s3 sync` into the bucket.
2. `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.

## Post-deploy smoke (5 minutes)
1. Click a signatory magic link (`/escrow/login?claim=1&iid=…&token=…`), set a password → single green toast, land on `/escrow/me`. No 401.
2. `/forgot-password` → **Escrow Institution** → approved email → reset mail → set new password → sign in works.
3. Submit a profile change request → no CSRF 403.
4. Click **View** on a document → opens in a new tab.
5. Sign out → unified `/login`.

⚠️ Sessions created before v52h must sign out once to pick up the new partitioned `csrf_token` cookie.
