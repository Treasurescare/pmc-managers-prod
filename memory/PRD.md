# PMC Managers Limited v2 — Product Requirements

## Original problem statement
Global tender-management platform mirroring the 39-page Enterprise CRM & e-Tender Revised Integrated Report. Full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labeled AWS deploy — no "Emergent" branding.

## Roles
Admin · Vendor · Staff (escrow_agent, certifier, legal_counsel, accounting, committee_member, reviewer, auditor, support).

## Modules (all delivered)
Notice Board · Vendor Registration · Package Tracker · Bidding + EMD escrow · BOQ Builder · Evaluation & Contracts · Vendor Intelligence · Tender/RFP/RFQ Template Builder · Joint-Signature Escrow · Approval Matrix · Post-Award Auto-Doc Generator · Product Catalog · Stripe checkout · Quote pipeline · Subscriptions · Two-Cover · Reverse Auction Live Room · UNSPSC-lite · Meetings (Zoom+Jitsi) · L1 Auto-Comparison · DocuSign eSignature · Profile ops · Portal Branding · Help Requests.

## Integrations
- LLM: Emergent LLM Key (AI Audit Copilot)
- Email: Resend via Emergent-managed Email Key
- Payments: Stripe test mode (PayPal/Kaspi backlog)
- eSignature: DocuSign JWT + embedded signing
- Video: Zoom + Jitsi
- Storage: AWS S3 + CloudFront (frontend)
- Backend: AWS Elastic Beanstalk Docker · MongoDB Atlas
- KYC: stub

## Production topology
- Frontend: S3 `pmc-managers-frontend-prod` + CloudFront
- Backend: EB `pmc-backend-prod` (Docker, EU-West-2)
- DB: MongoDB Atlas project `pmc-tender-uk`
- Domain: https://www.pmcmanagers.com

## Status snapshot (Sep 03, 2026)

**Live in prod**:
- Backend `v7-hardened` · Frontend `v8c-header-cleanup` · Atlas whitelist `0.0.0.0/0`
- 12 bugs fixed & shipped
- Startup diagnostics `[PMC-BOOT]` / `[PMC-DB]` / `[PMC-STARTUP-FATAL]`

**Ready to deploy (in `/app/`)**:
- `pmc-backend-v9-wave-e.zip` (mongo/env guards + Bug 5)
- `pmc-frontend-v13-quickwins.zip` (Bugs 5, 22, 23, 24, 46, 50)
- `PMC_Bug_Tracker_v1.xlsx` (master tracker — 62 rows)

**Open backlog** (see tracker sheet 1):
- Wave A: 9 bugs (created-but-not-in-list)
- Wave B: 6 bugs (blank screen / re-login)
- Wave C: 5 bugs (corrigenda + notice lifecycle)
- Wave D: 7 bugs (vendor registration + supplier actions)
- Wave E: 11 remaining after quickwins (validations, i18n)
- Wave F: Handbook rewrite
- Wave G: 5 governance items (dual-sig, COI, RBAC)

## Master credentials (see `/app/memory/test_credentials.md`)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Owner: `kannan@emeraldcorporates.com` / `Owner@123`

## Critical rules
1. Never expose preview URLs to end users
2. Frontend builds must use `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com`
3. Backend zips: Dockerfile + Dockerrun.aws.json at root, backend/ as subfolder
4. Strip `_temp_downloads.py` from prod zips
5. Auth changes → `integration_playbook_expert_v2` first
