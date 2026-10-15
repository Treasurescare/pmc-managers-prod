# PMC Managers · v52o deployment bundle

Build date: 15 Oct 2026 · supersedes v52n.

## What's new in v52n → v52o

### Vendor invite screen (Market → Vendors → Invite vendor)
- **Country is now a dropdown fed from the 250-row country master** (`GET /api/v1/masters/countries`) instead of a free-text input — values are ISO-2 codes, consistent with the full vendor registration form and KYC provider selection.
- **Email delivery is now visible, not silent.** The invite endpoint previously fired `asyncio.create_task(send_email(...))` — the UI toasted "Invited" even when Resend rejected the message. The send is now awaited and the API returns `email_sent: true/false`; the UI shows a warning toast when it is false instead of a fake success.
- Verified live: invite returned `email_sent: true` and the backend log shows Resend `HTTP 200 OK` for the message.

Note: `email_sent: true` confirms Resend **accepted** the message for delivery. If a specific recipient still doesn't see it, check their spam folder and the Resend dashboard delivery log for that address — the app now tells you the moment dispatch itself fails.

## Carried forward from v52n → v52h
Audit ledger bulk rechain (sub-second) + Repair chain button + server-side filters · reverse-auction invites (placeholder auto-append + Resend rate-limit stagger) · owner "institution paused" banners · pause-on-change status gate · pending-count badges · human-readable diffs · light-palette pins · multi-row signatory invites with country dropdown + validation · claim auto-login · account-first reset + legacy auto-claim · partitioned CSRF cookies · escrow file viewing · unified login routing · upload crash fix · admin filters · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52o.zip`
- Frontend static build: `/downloads/pmc-frontend-v52o-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → **Upload and deploy** → `pmc-backend-v52o.zip` → green → `/api/health`.
2. Env vars unchanged: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`.

### Frontend (S3 + CloudFront)
1. Unzip → `aws s3 sync` → `aws cloudfront create-invalidation --paths "/*"`.

## Post-deploy smoke (3 minutes)
1. Market → Vendors → Invite vendor → the Country field is a dropdown (250 countries); pick one and send.
2. Toast reads "Invited … · PMC-SUP-XXXXXX". If email dispatch ever fails you'll see a warning instead.
3. Admin → Audit ledger → Verify chain → Repair chain if it still shows the legacy break — completes in under a second.
