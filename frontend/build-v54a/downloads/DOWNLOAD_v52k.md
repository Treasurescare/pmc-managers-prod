# PMC Managers · v52k deployment bundle

Build date: 15 Oct 2026 · supersedes v52j.

## What's new in v52k

### Institutions pause while changes await PMC review
- An **approved** institution that submits any profile change request immediately flips to **`changes_requested`** (shown as "CHANGES PENDING" chip in the admin pipeline) — it is not live until PMC clears the queue.
- When the **last** pending request is approved, rejected or cancelled, the institution automatically returns to `approved`.
- Signatory invites and other approved-only actions are blocked while paused (403 "not approved").
- Admin pipeline rows now show an orange **"N changes pending"** badge; the status filter has a "Changes pending (awaiting approval)" option; admin chart still includes paused institutions.

### Admin change-request review is human-readable
- Current/Proposed boxes render plain values, document cards (filename · KB · View proposed file) and list items instead of raw JSON.
- Fixed the dark-on-dark boxes: the global slate→dark CSS remap was blacking out the diff boxes and washing out detail text on this light page — palette is now pinned for the whole Escrow institutions screen.

### Owner invite form upgrades
- **"+ Add another teammate"** button — invite multiple signatories in one go; per-row remove; summary toast.
- **Country dropdown for phone** (30 countries, dial codes) with per-country **digit-count validation**; the backend also enforces international format (`+971 501234567` style) with a 422 for anything else.

## Carried forward from v52j / v52i / v52h
Signatory claim auto-login (no 401 after password set) · account-first reset with signatory fallback · legacy institution auto-claim via Forgot password · Escrow option on `/forgot-password` · partitioned CSRF cookie · escrow file download gate · in-iframe blob file viewing · unified login escrow routing · upload crash fix · profile change-request workflow · admin search/date/status filters · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52k.zip`
- Frontend static build: `/downloads/pmc-frontend-v52k-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → backend environment → **Upload and deploy** → `pmc-backend-v52k.zip` → wait for green → `/api/health`.
2. Confirm env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`.

ZIP layout: `Dockerfile` + `.dockerignore` + `.ebextensions/` at root. No `docker-compose.yml`, no `.env`.

### Frontend (S3 + CloudFront)
1. Unzip → `aws s3 sync` into the bucket.
2. `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"` — **required**, stale JS caused the earlier claim 401.

## Post-deploy smoke (5 minutes)
1. Approved institution → submit a change request → pipeline chip flips to **CHANGES PENDING** + "N changes pending" badge; approve it as admin → back to **APPROVED**.
2. Institution profile → "+ Add another teammate" → pick a country, enter wrong digits → validation message; correct digits → invite sent.
3. Admin change request panel shows readable Current vs Proposed (no JSON, no dark boxes).
4. Magic-link claim → straight to dashboard, no 401.
