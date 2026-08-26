# PMC Managers Limited v2 — Product Requirements

## Original problem statement
Global tender-management platform mirroring the 39-page Enterprise CRM & e-Tender Revised Integrated Report. Full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, and an AI Audit Copilot. Fully white-labeled AWS deploy — no "Emergent" branding anywhere in code or Git history.

## Core roles
Admin · Vendor · Staff (with sub-roles: escrow_agent, certifier, legal_counsel, accounting, committee_member).

## Core modules (all delivered)
- Notice Board · Vendor Registration · Package Tracker
- Bidding Management + EMD escrow
- BOQ Builder · Evaluation & Contracts
- Vendor Intelligence · Tender/RFP/RFQ Template Builder
- Joint-Signature Escrow · Approval Matrix · Post-Award auto-doc generator
- Product Catalog · Stripe checkout · Quote pipeline · Subscriptions
- Two-Cover enforcement · Reverse Auction Live Room · UNSPSC-lite taxonomy
- Meeting Scheduler (Zoom + Jitsi) · L1 Auto-Comparison · DocuSign eSignature
- Profile ops (avatar, change password, forgot username, help desk)
- Portal Branding (per-tenant logo)

## Integrations
- LLM: Emergent LLM Key (Claude/Gemini/GPT) — AI Audit Copilot
- Email: Resend via Emergent-managed Email Key
- Payments: Stripe (test mode active) · PayPal/Kaspi (backlog — needs real merchant creds)
- eSignature: DocuSign (JWT Grant, embedded signing for demo)
- Video: Zoom + Jitsi
- Storage: AWS S3 + CloudFront (frontend)
- Backend: AWS Elastic Beanstalk Docker (Amazon Linux 2023) · MongoDB Atlas
- KYC: stub → live provider (backlog)

## Production topology
- Frontend: S3 `pmc-managers-frontend-prod` + CloudFront
- Backend: EB env `pmc-backend-prod` (Docker, EU-West-2)
- DB: MongoDB Atlas project `pmc-tender-uk`, cluster `pmc-managers-uk`
- Domain: https://www.pmcmanagers.com (SSL active)
- Git history: purged of "Emergent" branding

## What's been implemented (roll-up as of Aug 26, 2026)
- Full core stack + all core modules above
- All 16 Bugs V2 addressed except items 5, 6, 8, 12, 15 (open, need repro info)
- Illustrated Trainee Manual + Investor Deck (PDF + DOCX) in `/app/deliverables/`
- Header consolidation, profile ops, forgot-username, help requests
- **[NEW Aug 26]** Startup diagnostics: `[PMC-BOOT]`, `[PMC-DB]`, `[PMC-STARTUP-FATAL]` — surfacing config/Mongo issues loudly in `eb logs`
- **[NEW Aug 26]** Motor client `serverSelectionTimeoutMS=8000` + explicit ping at startup → fails fast on Atlas IP-whitelist / DNS issues

## Prioritised backlog

### P0 — Recommended at next deploy window
- Deploy `pmc-backend-v7.1-mongo-guard.zip` (contains permanent Mongo/env guards)

### P1 — Next up
- Bugs still open (need repro from user): #5 sub-admin notice "undefined" · #6 vendor mailing address · #8 invite vendor · #12 new BOQ contract not showing · #15 AI Bid Anomaly blank score
- UNSPSC picker → BOQ Builder + Vendor Registration Section C
- Investor Analytics Dashboard (KPI board: live tenders, GMV, cycle time)

### P2 — Blocked on external creds
- PayPal & Kaspi Pay live (need merchant credentials)
- Firebase / APNs push notifications (need Service Account JSON)
- Live KYC provider (need KYC_BASE_URL + KYC_API_KEY)

### Infra hygiene
- Replace Atlas `0.0.0.0/0` with NAT Gateway + Elastic IP
- Rotate `Admin@12345` → strong password before real go-live

## Master credentials (see /app/memory/test_credentials.md)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Owner: `kannan@emeraldcorporates.com` / `Owner@123`

## Critical rules
1. Never expose `*.preview.emergentagent.com` URLs to end users (only `_dl/` route for temp zip delivery)
2. Frontend deploys: build with `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com yarn build` → S3 → CloudFront `/*` invalidation
3. Backend zips MUST have `Dockerfile` + `Dockerrun.aws.json` at ZIP root, `backend/` as subfolder
4. Strip `_temp_downloads.py` from production zips (see `/app/scripts/build_backend_v7.sh`)
5. Auth changes → call `integration_playbook_expert_v2` first
