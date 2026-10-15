# PMC Managers · v52i deployment bundle

Build date: 15 Oct 2026 · supersedes v52h.

## What's new in v52i (on top of v52h)

- **Escrow password reset actually works now.** Account reset emails land on `/escrow/login?reset=1&token=…`; that page previously posted only to the *signatory* reset endpoint, so every account reset token failed with "invalid link". The page now tries the account endpoint first and falls back to signatory. Verified in-browser: reset → toast → sign in with new password → dashboard.
- **Locked-out legacy institutions can recover.** If an approved institution was registered under the old magic-link flow (no account record), `Forgot password` now auto-provisions a verified owner account linked to that institution and emails the reset link to the address already on file. Audited as `escrow_account.legacy_claim`.
- **Unified `/forgot-password` page has an Escrow Institution option** — no more dead end from the main sign-in page. It fires both escrow endpoints (account + signatory); neither leaks whether the email exists.
- **Successful reset flips the account to verified** — covers users who never completed the email-verify step.

## Carried forward from v52h
CSRF partitioned-cookie fix · escrow sessions can download their own files · in-iframe file viewing via blob fetch · unified escrow login routing · document upload crash fix · institution profile change-request workflow + admin approve/reject · admin filters (search/date/status) · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52i.zip`
- Frontend static build: `/downloads/pmc-frontend-v52i-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → backend environment → **Upload and deploy** → `pmc-backend-v52i.zip`.
2. Wait for green; hit `/api/health`.
3. Confirm env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`.

ZIP layout: `Dockerfile` at root, `.dockerignore`, `.ebextensions/`, no `docker-compose.yml`, no `.env` inside.

### Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v52i-prod-build.zip`, `aws s3 sync` into the bucket.
2. `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.

## Post-deploy smoke (5 minutes)
1. `/login` → Escrow Institution → your approved institution email → **Forgot password** (or the Escrow option on `/forgot-password`) → check inbox → set new password → sign in lands on `/escrow/me`.
2. Institution profile → submit a change request → no CSRF 403.
3. Click **View** on an uploaded document — opens in a new tab without a sign-in error.
4. Admin → Escrow institutions → search by email, approve a pending change request.
5. Sign out → lands on `/login`.

⚠️ Reminder: sessions created before v52h must sign out and back in once to pick up the new `csrf_token` cookie.
