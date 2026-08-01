# PMC Managers Limited — Business Analysis: Gap Assessment

**Prepared for:** Client / Board Discussion
**Date:** February 2026
**Version:** 1.0
**Prepared by:** Delivery Team

---

## 1. Executive Summary

You have two new source documents on the table:

1. **PMC Transaction Structure & Funds-Flow Report** (v1.0, 24 July 2026) — a **commercial-legal** framework describing how money flows and who must hold what.
2. **PMC Build Sheet v2 AWS** (24 July 2026) — a **technical re-architecture** describing a native-AWS stack with four discrete applications.

Against this, we have already delivered a fully-functional **v2.0 Tender Management Platform** built on Emergent (FastAPI + MongoDB + React). It covers registration, bidding, evaluation, award, and audit — the classic tender lifecycle.

**The core message for the client:**
> **The new scope is not an incremental change. It is a strategic pivot in three dimensions at once: architecture (Emergent stack → AWS-native), scope (single unified platform → four discrete apps), and commercial model (a fee/bid platform → a certified-instruction platform that stewards other people's money).**

The client must be made to understand these three shifts so that decisions on time, cost and re-use can be made deliberately, not by drift.

---

## 2. What We Have Already Built (Baseline)

| Domain | Delivered v2.0 Feature | Status |
|---|---|---|
| **Platform** | Emergent SaaS · React SPA · FastAPI · MongoDB · single-region | Live in production |
| **Auth** | JWT (httpOnly cookies) + Emergent-managed Google OAuth | Working |
| **Vendor onboarding** | Pre-Tender Registration Form (Sections A–E), KYC uploads, 6 declarations + eSignature | Working |
| **Stripe fee** | One-time vendor registration fee via Stripe checkout | Working |
| **Tender lifecycle** | Unified RFP / RFQ / Tender with draft → pending_approval → open → closed / awarded | Working |
| **Multi-level approval** | Buyer Orgs, Departments, budget-threshold approval chains | Working |
| **Two-envelope RFP** | Sealed technical + commercial envelopes, timed open, technical qualification gate before award | Working |
| **Bidding** | Bid creation, comparison view, lowest-bid highlight, RFP weighted scoring | Working |
| **EMD (Earnest Money Deposit)** | Stripe-backed EMD, refund / forfeit workflow | Working |
| **Pre-bid Q&A + Corrigenda** | Anonymised questions, buyer answers, addenda publishing | Working |
| **Notifications** | In-app + Resend email (branded) | Working |
| **Live feed** | Server-Sent Events tender feed with filters + per-user read state | Working |
| **Audit trail** | Application-level SHA-256 hash-chained immutable ledger, admin verify button | Working |
| **FX Conversion** | Live rates (`open.er-api.com`), currency chip on tender detail | Working |
| **SBD Template Library** | Admin uploads standard bidding docs; buyers attach via dropdown | Working |
| **Vendor KPI Dashboard** | Win-rate, avg price/delivery, category history, suggestions | Working |
| **i18n** | English + Russian (Kazakh partial) | Working |
| **Deployment** | Deployed to Emergent-managed production URL | Live |

**Bottom line:** we have a working, tested tender platform (28/28 P2 tests + 42/42 P1 tests pass) that could take live tenders tomorrow.

---

## 3. The New Scope, Decoded

### 3.1 Document 1 — Transaction Structure Report

This is a **commercial and legal framework**, not a build spec. It says:

- **Money splits into two categories:**
  - **Category A — PMC Revenue** (fees for services PMC performs). PMC keeps this.
  - **Category B — Stewarded Funds** (EMD, performance bonds, retention, drawdowns). PMC never holds this — it instructs and reconciles only.
- **Four money pipes**, each with a different holder:
  1. PMC fees → PMC's operating accounts via commercial gateway
  2. Bid security (EMD) → regulated escrow agent
  3. Performance guarantees + retention → guarantee bank
  4. Construction drawdowns → bond trustee / paying agent
- **Ten roles to appoint** externally: Escrow Agent, Guarantee Bank, Bond Trustee, Security Agent, Paying Agent, Independent Certifier, Account Bank, Payment Gateway, Legal Counsel, KYC/Screening Provider.
- **Six controls to build in**: segregation, account-control agreements, certified-instruction workflow, float-interest disclosure, immutable audit trail, related-party register.
- **Six open legal questions** blocking activation of the corresponding money flows.

**Implication for us:** This is largely **legal & organisational work outside the platform**, but it imposes concrete technical requirements — most notably a **certified-instruction workflow** and **immutable ledger** that must interface with regulated third parties.

### 3.2 Document 2 — Build Sheet v2 AWS

This is a **complete technical re-architecture**. It says:

- **Move off Emergent's managed stack** to AWS-native: RDS PostgreSQL 16 Multi-AZ · S3 with Object Lock (Compliance Mode, 7-year retention) · Cognito · ECS Fargate · SES · CloudWatch · Terraform IaC.
- **Split the platform into FOUR separate applications**:
  1. **App 1 — Milestone Evidence Capture** (React Native mobile, offline-first with SQLite, GPS-stamped, witness-signed, WORM evidence).
  2. **App 2 — Package Tracker** (internal, Retool, admin/site_lead only).
  3. **App 3 — Pre-Tender Registration Portal** (React web, magic-link resume, EN/RU/KK).
  4. **App 4 — Public Tender Notice Board** (Next.js SSR, SEO-optimised, no login).
- **One central FastAPI + SQLAlchemy API** on Fargate — apps never touch the database directly.
- **Multi-tenancy via PostgreSQL RLS** driven by session variables from Cognito claims.
- **Explicit OUT-OF-SCOPE clause**: "never implement — encryption, key management, **bid submission, bid opening, evaluation scoring, contract award, payment processing**."

**Implication for us:** The document deliberately **omits most of what we already built** and replaces it with **a milestone-evidence and public-notice-board focus**. Bidding, evaluation and payment are explicitly excluded from this build phase.

---

## 4. Gap Analysis — Point-by-Point Comparison

| # | Area | Current (v2.0, delivered) | New Scope (Doc 1 + Doc 2) | Gap Type | Impact |
|---|---|---|---|---|---|
| 1 | **Cloud platform** | Emergent-managed (opinionated PaaS) | AWS-native (RDS · S3 · Cognito · Fargate · Terraform) | **Replacement** | HIGH — full re-platform |
| 2 | **Database** | MongoDB (document, single-tenant) | PostgreSQL 16 Multi-AZ with RLS multi-tenancy | **Replacement** | HIGH — schema + query rewrite |
| 3 | **Auth** | JWT + Emergent Google OAuth | AWS Cognito with hosted UI + MFA optional / admin mandatory | **Replacement** | MEDIUM — user & session migration |
| 4 | **Tenancy model** | Single-tenant (implicit) | Multi-tenant via `tenant_id` from Cognito, enforced by RLS `force row level security` | **Addition** | HIGH — data model change |
| 5 | **File storage** | MongoDB blob attachments + Emergent object store | S3 with SSE-KMS + Object Lock (Compliance Mode, 7-year, WORM) — **irreversible on day one** | **Replacement + Upgrade** | HIGH — evidence chain-of-custody |
| 6 | **Tender lifecycle (draft → open → award)** | Full lifecycle implemented | **Out of scope** per new build sheet Part 5 | **Removal from Phase 1** | CRITICAL — clarify with client |
| 7 | **Bidding, evaluation, scoring** | Full RFP/RFQ bidding, weighted scoring, comparison, award | **"Never implement"** in the new phase | **Removal from Phase 1** | CRITICAL — clarify with client |
| 8 | **Two-envelope sealed bidding** | Delivered | Not in scope | **Removal from Phase 1** | Retain code for later phase |
| 9 | **EMD workflow** | Stripe-backed EMD refund/forfeit | Doc 1 mandates EMD sits in a **regulated escrow account**, not with PMC. Doc 2 does not implement it. | **Redesign** | Existing EMD code is incompatible with Doc 1's regulatory model |
| 10 | **Payment processing** | Stripe for registration fee + EMD | **"Never implement"** in the new phase | **Removal from Phase 1** | Keep Stripe route but scope out |
| 11 | **Vendor pre-tender registration** | Delivered (Sections A–E, single app) | App 3 (fresh build, magic-link resume, EN/RU/KK) | **Rebuild in new stack** | Existing form logic re-usable as spec |
| 12 | **Public tender notice board** | Not built (auth required for tender views) | App 4 (Next.js SSR, no-auth, SEO + JSON-LD) | **Addition** | New workstream |
| 13 | **Milestone evidence capture** | Not built | App 1 (mobile, offline-first, WORM, GPS, witness signature, idempotent sync) | **Addition** | Largest new workstream |
| 14 | **Package Tracker (internal)** | Partial (admin dashboards) | App 2 (Retool, drag-and-drop board, 203 KZ packages import) | **Replacement / Rebuild** | Use Retool = faster |
| 15 | **Multi-language** | EN + RU + partial KK | EN + RU on App 1 & App 4; EN + RU + KK on App 3 | **Extend** | Add KK completeness on registration app |
| 16 | **Audit trail** | Application-level SHA-256 hash chain in MongoDB | **S3 Object Lock (Compliance Mode)** for evidence + audit_event table with append-only triggers | **Upgrade** | New scope's WORM is stronger — regulator/underwriter-grade |
| 17 | **Certified-instruction workflow** | Not built explicitly | Required by Doc 1 Section 7 for every release of EMD, retention, drawdown | **Addition** | New workstream |
| 18 | **Regulated third-party integration** | None | Doc 1: Escrow Agent, Guarantee Bank, Bond Trustee, Paying Agent, Account Bank must all be integrated for instructions & reconciliation | **Addition** | Depends on legal appointments (Doc 1 Section 6) |
| 19 | **Independent Certifier / Engineer role** | Not built | Doc 1 positions PMC as Independent Certifier via the milestone evidence engine (App 1) | **Addition** | App 1 is the deliverable that makes this role real |
| 20 | **Related-party register + float-interest disclosure** | Not built | Doc 1 Section 7 controls | **Addition** | Small module |
| 21 | **Deployment / IaC** | Emergent one-click | Terraform in `pmc-infra` repo, five GitHub repos, branch protection, CI scans | **Replacement** | DevOps re-work |
| 22 | **Data residency** | Emergent default region | Native regional (Kazakhstan) as a Terraform variable | **Upgrade** | Enables gov / in-country deals |
| 23 | **Monthly OpEx** | Emergent subscription | ~$450–525 / month (RDS + Fargate + S3 + SES + Cognito + Retool + Emergent build months) | **Increase** | +~$150/month over shortcut route |

---

## 5. What the Client Must Decide

There are **five decision points** that will determine the delivery plan and budget. None of these can be answered by us alone.

### Decision 1 — Do we replatform, or do we extend?

- **Option A (Replatform to AWS as Doc 2 says):** Rebuild against AWS-native stack. The v2.0 delivered platform becomes a reference/spec, not the running system. Estimated effort **7 weeks minimum** per Doc 2 Part 8.
- **Option B (Extend the current Emergent platform):** Add App 1 (mobile evidence capture) and App 4 (public board) alongside the existing platform on Emergent. Faster, cheaper, but does not deliver Object Lock, native residency or the multi-tenant AWS control plane.
- **Option C (Hybrid):** Keep v2.0 running for tender lifecycle (which the new build sheet explicitly excludes), and build Doc 2's four apps in AWS in parallel. Costs and integration complexity go up but no functionality is lost.

**Our recommendation:** Option C, phased — because the delivered tender lifecycle is production-ready and the new build sheet does not replace it, only adds to it.

### Decision 2 — Is bidding really out of scope, or only out of Phase 1?

Doc 2 Part 5 says "**Never implement — bid submission, bid opening, evaluation scoring, contract award, payment processing.**"
But those features are **already built and working** in v2.0. This looks like a **phasing statement** ("do not build in the new AWS apps yet") rather than an instruction to **delete** them.

**Client must confirm:**
- Does "never implement" mean (a) don't touch it in the new AWS apps, keep v2.0 running, or (b) formally decommission bidding entirely?

### Decision 3 — Who holds the money?

Doc 1 makes it clear that PMC **must not** hold EMD, performance bonds, retention or construction drawdowns. Today, our v2.0 Stripe-backed EMD workflow does exactly that (funds sit in Stripe under PMC's account).

**Client must confirm:**
- Which regulated party will hold EMD? (Kazakh bank escrow division? AIFC escrow company? A DIFC / ADGM specialist?)
- Until this is decided, the certified-instruction workflow cannot be turned on for real money — but the platform can still be built to instruct-and-reconcile against a mock/test escrow.

### Decision 4 — Open legal questions (Doc 1 Section 9)

Six questions gate the corresponding money flows. Until each is answered, that flow stays disabled in the platform:

1. Land-grant procurement obligations?
2. Concession / PPP status?
3. Legality of verification / document fees?
4. Who may hold EMD and guarantees?
5. Float-interest entitlement?
6. Bond-terms disclosure obligations?

**Client must engage counsel** in UK, Kazakhstan and Luxembourg **before Phase-1 go-live**.

### Decision 5 — GitHub org & AWS account ownership

Doc 2 assumes a **`pmc-managers` GitHub org with five repos** and a dedicated AWS account with Terraform-managed infra. Both must exist and be owned by the correct legal entity before we can begin.

**Client must:**
- Create/nominate the AWS account (payer, region, tag policy).
- Create/nominate the GitHub org with billing plan.
- Confirm who owns the Terraform state (recommend an S3 backend with lock table in the same AWS account).

---

## 6. Proposed Phased Roadmap

Assuming the client agrees to Option C (hybrid — extend + build new apps in AWS):

### Phase 0 — Governance & Legal (Weeks 1–4, in parallel)
- Counsel engaged on 6 open legal questions
- Escrow Agent, Guarantee Bank, Bond Trustee identified & LOI'd
- AWS account + GitHub org provisioned
- Terraform bootstrap (Part 1 of Doc 2)

### Phase 1 — AWS Foundation (Weeks 2–3)
- Terraform provisions RDS, S3 (Object Lock), Cognito, ECS, SES, Secrets Manager, CloudWatch
- **Object Lock configured at bucket creation** (Doc 2 warns this is irreversible)
- `pmc-api` FastAPI + SQLAlchemy scaffolded on Fargate
- RLS policies + tenant middleware working (RLS proof-test 5, 7, 8, 9 in Doc 2 Part 7)

### Phase 2 — App 4 Public Notice Board (Week 4)
- Next.js SSR, no auth, SEO + JSON-LD
- Reuses existing v2.0 tender data via a read-only sync/export bridge until full migration

### Phase 3 — App 2 Package Tracker in Retool (Weeks 4–5)
- 203 KZ packages CSV imported
- Contract & milestone setup (this is the data App 1 consumes)

### Phase 4 — App 1 Milestone Evidence Capture (Weeks 5–7)
- React Native mobile
- SQLite offline queue
- Presign → S3 → sync flow (idempotency, immutability, Object Lock proofs)
- Two site-device pilot

### Phase 5 — App 3 Pre-Tender Registration Portal (Weeks 7–12)
- Rebuild vendor registration in the new stack (reuses v2.0 form logic as spec)
- EN/RU/KK
- Magic-link resume
- Approval workflow ties into existing v2.0 admin queue via API bridge, or fully migrates

### Phase 6 — Certified-instruction & Escrow Bridge (Weeks 10+)
- Machine-readable release instructions to appointed escrow agent
- Reconciliation dashboards
- Related-party register + float-interest disclosure UI

### Phase 7 — v2.0 Bidding Platform Decision (post-Phase 5)
- Depending on Client decision, either:
  - Migrate v2.0 bidding module onto AWS stack, OR
  - Keep v2.0 on Emergent as the bidding platform and integrate via API, OR
  - Decommission v2.0 bidding

---

## 7. Risks & Considerations

| Risk | Severity | Mitigation |
|---|---|---|
| **Object Lock is irreversible** — a wrong config on day one means rebuilding the bucket later and losing chain-of-custody on everything already in it (Doc 2 warns explicitly) | HIGH | Dry-run in a non-prod bucket first; run the Object-Lock refusal test (Part 7 item 9) before any real evidence uploaded |
| **RLS silent failure** — `set local` outside a transaction returns zero rows silently (Doc 2 4.1) | HIGH | Explicit failure-mode test (Part 7 item 5) written into CI |
| **v2.0 investment write-off** — if Option A (full replatform) is chosen, ~4 months of v2.0 work becomes reference material, not running code | HIGH (financial) | Reuse spec, form structure, UX patterns, evaluation logic as documentation for the AWS rebuild |
| **Regulatory delay** — 6 open legal questions could delay real-money go-live by 3–6 months | HIGH | Build against **mock escrow** endpoints so the platform is ready before the appointments are finalised |
| **Multi-tenancy retrofit** — v2.0 is single-tenant. AWS build is multi-tenant with `tenant_id` everywhere. Migrating existing data means synthesising a tenant_id per record. | MEDIUM | Snapshot v2.0 as tenant #1 during migration |
| **Cognito ≠ Emergent Google OAuth** — existing users have Emergent-managed identities. Migration to Cognito is a one-way door for existing session state. | MEDIUM | Password reset flow for all existing users at cutover; SES email templates prepared |
| **Stripe out-of-scope** — Doc 2 Part 5 explicitly excludes payment processing. Existing Stripe integration must be retired or moved out of the AWS build. | MEDIUM | Retain Stripe only in v2.0; new AWS build never touches payments (per doc) |
| **Kazakh + Russian + English language load** — App 3 requires KK; current i18n is EN/RU + partial KK | LOW | Complete KK strings during App 3 build |
| **GitHub push blocker** (current) | LOW | Resolve via OAuth flow (see prior guidance) before Phase 0 |

---

## 8. Cost & Timeline Summary

| Item | Baseline (delivered v2.0) | New Scope (Option C hybrid) |
|---|---|---|
| **Build effort remaining** | ~0 (production-ready) | ~10–12 weeks across 4 apps + API + infra |
| **Monthly OpEx** | Emergent subscription only | ~$450–525 / month (AWS) + Emergent build months |
| **Regulatory / Legal cost** | Not applicable | 3-jurisdiction counsel engagement — external estimate needed |
| **Third-party appointments** | Not applicable | Escrow agent, guarantee bank, trustee, paying agent — negotiate individually |
| **Risk of write-off** | Delivered, protected | HIGH if full-replatform is chosen without hybrid |

---

## 9. Recommended Client Conversation Agenda

Use this in your meeting.

**Slide 1 — What we already built** (5 min) — Show v2.0 dashboard, tender lifecycle, KPI, audit trail. Establish the baseline.

**Slide 2 — The two new documents** (5 min) — One is legal-commercial, one is technical. They point in the same direction but sit at different layers.

**Slide 3 — The three shifts** (10 min) — Architecture · Scope · Commercial model. Confirm the client actually intends all three.

**Slide 4 — The five decisions we need from you** (15 min) — Walk through Section 5 of this doc. Get answers on the record.

**Slide 5 — The proposed hybrid roadmap** (10 min) — Section 6. Confirm phasing.

**Slide 6 — Risks & irreversibility warnings** (5 min) — Section 7, especially Object Lock and the 6 legal questions.

**Slide 7 — Sign-off & next steps** (10 min) — What we start next week; what the client must produce (AWS account, GitHub org, counsel engagement).

---

## 10. Appendix — Terminology Cheat Sheet for Non-Technical Stakeholders

| Term | Plain English |
|---|---|
| **Category A / B money** | Money PMC earns (keep it) vs money PMC just watches over (never hold it) |
| **Escrow** | A regulated bank account run by a neutral third party that holds funds until a defined event |
| **EMD** | Bid deposit — bidders lodge it to prove they are serious; refunded if they lose |
| **Retention** | Money held back from a contractor's payment until they fix any defects after handover |
| **Certified-instruction workflow** | An audit-proof approval process — "no money moves unless the system says so" |
| **Object Lock (Compliance Mode)** | AWS S3 feature — once a file is written, nobody can delete or change it (not admins, not the CEO) for the retention period. Regulator-grade evidence. |
| **Row-Level Security (RLS)** | Database-level rule that ensures user X can only see their own tenant's rows — even if the app has a bug |
| **RLS + `force row level security`** | Even the table owner respects the rule. A safety net against admin mistakes. |
| **Multi-tenant** | One platform, many client organisations, strictly isolated from each other |
| **WORM** | Write-Once-Read-Many — evidence that cannot be tampered with after creation |
| **Idempotent sync** | Send the same batch 10 times, still creates one record. Safe for flaky mobile connections. |
| **Presigned URL** | A time-limited link that lets a mobile app upload directly to S3 without the server acting as a middleman |
| **SSR (Server-Side Rendering)** | Pages rendered on the server first, so Google can index them (matters for the public notice board) |
| **Bond trustee / paying agent** | The professionally-appointed institutions that hold and disburse the bond money (never PMC) |
| **Independent Certifier** | The party who signs off "yes, this milestone is truly complete" — the platform's evidence engine positions PMC for this role |
| **Related-party** | A counterparty connected to the sponsor. Not forbidden, but must be arm's-length and disclosed. |

---

*This document is a delivery-team analysis for client-facing discussion. It is not legal advice. All legal questions in Doc 1 Section 9 must be answered by qualified counsel before the corresponding money flows are enabled.*
