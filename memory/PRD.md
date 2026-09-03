# PMC Managers Limited v2 — Product Requirements

## Original problem statement
Global tender-management platform mirroring the 39-page Enterprise CRM & e-Tender Revised Integrated Report. Full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labeled AWS deploy — no "Emergent" branding.

## Roles
Admin · Vendor · Staff (escrow_agent, certifier, legal_counsel, accounting, committee_member, reviewer, auditor, support).

## Modules (delivered)
Notice Board · Vendor Registration · Package Tracker · Bidding + EMD escrow · BOQ Builder · Evaluation & Contracts · Vendor Intelligence · Template Builder · Joint-Signature Escrow · Approval Matrix · Post-Award Auto-Doc · Product Catalog · Stripe · Quote pipeline · Subscriptions · Two-Cover · Reverse Auction · UNSPSC-lite · Meetings (Zoom+Jitsi) · L1 Auto-Comparison · DocuSign · Profile ops · Portal Branding · Help Requests.

## Integrations
LLM: Emergent LLM Key · Email: Resend · Payments: Stripe (test) · eSignature: DocuSign · Video: Zoom+Jitsi · Storage: AWS S3+CloudFront · Backend: AWS EB Docker · DB: MongoDB Atlas · KYC: stub.

## Production topology
- Frontend: S3 `pmc-managers-frontend-prod` + CloudFront
- Backend: EB `pmc-backend-prod` (Docker, EU-West-2)
- DB: MongoDB Atlas cluster `pmc-managers-uk` (0.0.0.0/0 whitelist)
- Domain: https://www.pmcmanagers.com

## Status snapshot (Sep 03, 2026)

**Live in prod**:
- Backend `v7-hardened` · Frontend `v8c-header-cleanup`
- 12 bugs fixed & shipped previously
- Startup diagnostics `[PMC-BOOT]` / `[PMC-DB]` / `[PMC-STARTUP-FATAL]`

**Ready to deploy (in `/app/`)**:
- `pmc-backend-v10-waves-abcd.zip` (222 KB)
- `pmc-frontend-v14-waves-abcd.zip` (42 MB)
- `PMC_Bug_Tracker_v2.xlsx` (62-row master tracker)

**Fixes in this v10/v14 batch** (17):
- Bug 5 (madhavi notice), 22 (form reset), 23 (validation msg), 24 (publish gate), 28 (bulk invite blank), 36 (audit hang — mitigated), 39 (award report hang — mitigated), 43 (auction Start), 44 (auction Close), 46 (nudge toast), 50 (verb typo), 51 (nudge notifications), 52 (dup 28), 57 (dup 39), 58 (blank flows — ErrorBoundary)

**Open backlog** (see tracker):
- Wave A2 (retest first): 8 bugs
- Wave C2 (clarify UX): 3 bugs
- Wave D2 (need repro): 5 bugs
- Wave E (misc): 16 bugs
- Wave F (docs): handbook rewrite
- Wave G (governance): 5 items — investor-critical

## Master credentials (see `/app/memory/test_credentials.md`)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Owner: `kannan@emeraldcorporates.com` / `Owner@123`

## Critical rules
1. Never expose preview URLs to end users
2. Frontend builds must use `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com`
3. Backend zips: Dockerfile + Dockerrun.aws.json at root
4. Strip `_temp_downloads.py` from prod zips
5. Auth changes → `integration_playbook_expert_v2` first
