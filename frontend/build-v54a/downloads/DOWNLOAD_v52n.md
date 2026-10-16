# PMC Managers · v52n deployment bundle

Build date: 15 Oct 2026 · supersedes v52m.

## What's new in v52n

### Audit ledger repair · fast path
- `rechain_audit()` now writes in **500-doc Mongo bulk batches** instead of one-at-a-time; the production 4,300-event ledger rechains in well under a second. Fixes "timeout of 20000ms exceeded" on the Repair chain button.
- UI call for `POST /api/v1/audit-events/rechain` has a 120 s per-request timeout as a safety net.

### Reverse-auction invites actually deliver
- **Root cause 1 — missing join link:** the stored default invitation template body had no `{{invite_url}}` placeholder, so recipients got an email with no way to open the auction. Backend now auto-appends a "Join the auction" button + fallback URL whenever a template is missing the placeholder (works for custom templates too). The DB-saved default template is also backfilled.
- **Root cause 2 — Resend rate limit:** bursts over 10 recipients hit Resend's 10 req/s cap and later invites silently 429'd. Backend now sleeps 120 ms between sends, verified a 10-recipient burst delivers `auto_sent: 10` with zero 429s.

## Carried forward from v52m → v52h
Audit ledger: write-race asyncio lock + server-side filters · owner "institution paused" banners · pause-on-change status gate with auto-restore · pending-count badges · human-readable change diffs · light-palette pins · multi-row signatory invites with country dropdown · claim auto-login · account-first reset + legacy auto-claim · partitioned CSRF cookies · escrow file viewing · unified login routing · upload crash fix · admin filters · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52n.zip`
- Frontend static build: `/downloads/pmc-frontend-v52n-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → **Upload and deploy** → `pmc-backend-v52n.zip` → green → `/api/health`.
2. Env vars unchanged: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`.

### Frontend (S3 + CloudFront)
1. Unzip → `aws s3 sync` → `aws cloudfront create-invalidation --paths "/*"`.

### One-time data step after deploy
- Any custom reverse-auction invite templates saved before today are auto-patched by the backend at send time, but if you want them stored clean, open each template and re-save it with `{{invite_url}}` in the body.

## Post-deploy smoke (3 minutes)
1. Admin → Audit ledger → Verify chain. If broken, click **Repair chain** — finishes in under a second, re-verifies green.
2. Admin → Reverse auctions → open any live auction → Invite 2 vendors with their real emails + autosend on → both receive a mail with a working **Join the auction** button.
3. Burst-invite 10+ emails at once → all `auto_sent`; backend log has no 429.
