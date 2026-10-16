# PMC Managers · v52m deployment bundle

Build date: 15 Oct 2026 · supersedes v52l.

## What's new in v52m

### Audit ledger: chain integrity fix + repair
- **Root cause of "Chain broken at seq #2037":** concurrent audit writes raced (sequence allocated and parent-hash read in two steps), so sibling events pointed at the same parent. Not tampering — a write race. Login bursts triggered it.
- `audit_log` is now serialized through a process-level lock; 30 parallel logins verified to keep the chain intact.
- New **Repair chain** action: when Verify reports a break, admins get a repair button (or `POST /api/v1/audit-events/rechain`). It recomputes hash links only — event payloads are never modified — and records an `audit.chain_repaired` marker on the ledger itself.

### Audit ledger: filters actually filter
- Event type, actor email and date range now filter **server-side** (`GET /api/v1/audit-events?event_type=&actor=&from_date=&to_date=`, limit up to 500). Previously the page only filtered the last 100 loaded events, so older matches never showed up.

## Carried forward from v52l → v52h
Owner-side "institution paused" banners · pause-on-change status gate with auto-restore · pending-count badges · human-readable change diffs · light-palette pins (Escrow institutions + Suggested banks) · multi-row signatory invites with country dropdown + digit validation · signatory claim auto-login · account-first reset + legacy auto-claim · Escrow option on forgot-password · partitioned CSRF cookies · escrow file download gate · blob file viewing · unified login routing · upload crash fix · admin filters · sign-out to `/login`.

## Downloads
- Backend: `/downloads/pmc-backend-v52m.zip`
- Frontend static build: `/downloads/pmc-frontend-v52m-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. EB → **Upload and deploy** → `pmc-backend-v52m.zip` → green → `/api/health`.
2. Env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `FRONTEND_URL=https://pmcmanagers.com`, `RESEND_API_KEY`.

### Frontend (S3 + CloudFront)
1. Unzip → `aws s3 sync` → `aws cloudfront create-invalidation --paths "/*"`.

## Post-deploy smoke (3 minutes)
1. Admin → Audit ledger → click **Verify chain**. If it reports the legacy break, click **Repair chain** once — it re-verifies green. (One-time action on prod.)
2. Type `staff.login` in Event type → only those rows load, including events older than 100 rows.
3. Set From/To dates → ranges respected.
