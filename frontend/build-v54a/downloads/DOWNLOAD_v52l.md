# PMC Managers · v52l deployment bundle

Build date: 15 Oct 2026 · supersedes v52k.

## What's new in v52l

### Owner-side pause visibility
- When an institution has change requests awaiting PMC review (`changes_requested`), the escrow **Overview** dashboard and **Institution profile** tab now show an amber banner: "Changes pending PMC review — your institution is paused (not live)… signatory invites are temporarily locked and re-enable automatically once the queue is cleared."
- The invite section explains the lock instead of showing a raw status string, and the form is visibly disabled while paused.

### Light-palette pinning extended
- The **Suggested banks curation** admin page (`/admin/e/suggested-banks`) gets the same light-palette pin as the Escrow Institutions screen — backgrounds, text ink, inputs and hover states can no longer be darkened by the global Option-E slate remap.

## Carried forward from v52k / v52j / v52i / v52h
Pause-on-change status gate (`approved` ⇄ `changes_requested`) with auto-restore · pending-count badges + changes-pending filter · human-readable Current/Proposed diffs · multi-row signatory invites with country dropdown + digit validation · signatory claim auto-login · account-first password reset + legacy auto-claim · Escrow option on `/forgot-password` · partitioned CSRF cookies · escrow file download gate · blob file viewing · unified login routing · upload crash fix · admin search/date/status filters · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52l.zip`
- Frontend static build: `/downloads/pmc-frontend-v52l-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → **Upload and deploy** → `pmc-backend-v52l.zip` → wait for green → `/api/health`.
2. Env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`.

### Frontend (S3 + CloudFront)
1. Unzip → `aws s3 sync` into the bucket.
2. `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"` — required.

## Post-deploy smoke (5 minutes)
1. Approved institution → submit a change request → owner dashboard shows the amber "paused" banner; admin pipeline shows CHANGES PENDING + "N changes pending".
2. Admin approves the request → institution returns to APPROVED, banner disappears on the owner's next load.
3. While paused, owner invite form is disabled with the lock explanation.
4. Admin → Suggested banks renders light and readable.
