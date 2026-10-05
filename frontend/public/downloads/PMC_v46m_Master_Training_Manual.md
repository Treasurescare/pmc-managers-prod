# PMC Managers · v46m Master Training Manual

_PMC Managers Limited · Confidential · v46m · September 2026_



This manual is the authoritative operator handbook for the PMC Managers Sovereign Tender Board, version 46m (Sep 2026). It walks every role through every screen with annotated screenshots, field-by-field guidance, known-gotcha callouts, and end-to-end workflow narratives. Use it as the primary onboarding pack for new admins, agents, partners, management, escrow officers and vendors.

## Table of contents

1. Platform overview & architecture
2. Roles at a glance (12-role matrix)
3. Security, audit & data-protection
4. Public visitor journey
5. Vendor / supplier journey
6. Admin console — full module tour
7. Deep-dive: Tender Builder & AI DPR (v46l map-reduce)
8. Deep-dive: Evaluation, awards & escrow
9. Deep-dive: Reverse auctions
10. Tooltip, error-handling & offline system
11. Deployment runbook (S3 + CloudFront + EB)
12. Troubleshooting playbook
13. API reference index
14. Release history
15. Glossary & appendix


## 1 · Platform overview & architecture

The PMC platform is a multi-role tender lifecycle engine covering the full path from notice publication → registration → bidding → EMD → evaluation → award → e-signature → invoicing → post-contract audit. It is delivered as a React single-page app backed by a FastAPI service and MongoDB, with same-origin cookie-based sessions and CSRF double-submit tokens.

**Frontend** — React SPA served from S3 + CloudFront. Sovereign navy/gold editorial design system with Libre Baskerville + IBM Plex fonts. Routing via React Router; state via Context (i18n, auth) + local component state.

**Backend** — FastAPI on AWS Elastic Beanstalk (Docker running on 64-bit Amazon Linux 2). All routes prefixed `/api/v1/…`. Auth realm split into admin, staff and vendor with per-realm login endpoints and cookie names.

**Data** — MongoDB via Motor (async driver). Collections include tenants, notices, tender_templates, registrations, vendors, bids, rubrics, scores, evaluations, awards, escrow_transactions, auctions, corrigenda, audits, ratings, engagements, packages, categories, countries, dpr_jobs.

**AI** — PMC AI service routed through the integration proxy. Used for DPR ingestion (map-reduce), AI Fill All, anomaly detection and the admin copilot. v46l lifts the 800 KB cap and adds an async worker.

**Storage** — S3 for licences, tender attachments, signed PDFs, archived auction rooms. CloudFront in front for global CDN.

**Notifications** — Resend (email), planned Firebase/APNs (mobile push).

**Payments** — Stripe (test + live keys separated); Kaspi + PayPal on the roadmap.

**E-signature** — DocuSign envelope templates + status webhooks.

**Observability** — Structured logs via Python logging, CloudWatch tail, audit_log() collection for every mutation, immutable time-stamped rows.

## 2 · Roles at a glance

| Role | Portal | Scope |
|---|---|---|
| Admin | `/admin` | Full control of every module. |
| Management | `/staff` | Executive dashboards, committee outcomes, escrow financials. |
| Partner | `/staff` | GOC / Bank / Regulator — audit hooks and co-procurement dashboards. |
| Agent | `/staff` | Field-ops — draft tenders, review dossiers, publish corrigenda. |
| Reviewer | `/admin` | Read-only + evaluation scoring. |
| Escrow agent | `/staff` | EMD desk, forfeitures, refunds. |
| Certifier | `/staff` | Tender packet sign-off. |
| Legal counsel | `/staff` | Contract review, DocuSign envelope owner. |
| Accounting | `/staff` | Fee invoicing, refunds, reconciliation. |
| Committee member | `/staff` | Evaluation committee voting. |
| Auditor | `/admin (read)` | Full audit trail with entity filters. |
| Support | `/staff` | Vendor helpdesk, activation resends. |
| Vendor | `/vendor` | Bid on notices, manage profile & invoices. |


## 3 · Security, audit & data-protection

**Authentication** — Three cookie realms (admin_session, staff_session, vendor_session). HttpOnly, SameSite=Lax, Secure in production. CSRF double-submit token on every mutating request. Brute-force lockout after 5 failed attempts within 15 minutes.

**Authorisation** — `require_role(*roles)` dependency guards every mutating endpoint. Read endpoints use `current_admin` / `current_staff` / `current_vendor` for realm assertions. Role membership persists in the staff_users / admin_users / vendors collections with a versioned history so ACL changes are auditable.

**Audit trail** — Every mutation calls `audit_log(action, actor, entity, entity_ref, payload)` which persists into the `audits` collection with an immutable ISO timestamp, actor id, and a JSON payload snapshot. Auditors can filter by entity + action + actor + date range in the Audit tab and export to CSV.

**Data protection** — Vendor licences and legal documents are stored in a private S3 bucket behind pre-signed URLs. Personally identifiable data is redacted from audit-log exports when the actor role is Auditor.

**Compliance** — GDPR data-processing consent is captured on the public registration wizard; ESG questionnaire responses live under the vendor profile.

## 4 · Public visitor journey

###  1 · Sovereign home — hero + live KPIs

The public landing page. Editorial navy/gold hero with a Libre Baskerville headline, three live KPI cards (Notices Published, Suppliers Approved, Work Packages), and three primary CTAs — View Open Notices, Register as Supplier, and the Portal Gateways link.

![Sovereign home — hero + live KPIs](../screens/01_public_home.png)

*Sovereign home — hero + live KPIs*

#### Purpose

The sovereign public entry. Establishes brand authority, states current scope (Kazakhstan Integrated Development), and exposes three live counters and three primary CTAs.

#### How the workflow unfolds

1) A prospective bidder lands from a Google search or a Snapchat post. 2) The live KPIs prove the platform has real, current activity. 3) They tap 'View Open Notices' to browse tenders or 'Portal Gateways' to sign in to their existing account.

#### Fields

- **Kicker line** — 'PMC Managers · Sovereign Gateway' — anchors the brand in an editorial serif register.

- **Sovereign hero** — Libre Baskerville headline, italic gold accent, IBM Plex Mono kicker — deliberately different from generic SaaS.

- **KPI cards** — Notices Published / Suppliers Approved / Work Packages — pulled live from /api/v1/meta/public/stats.

- **Primary CTAs** — View Open Notices (gold button), Register as Supplier (ghost button), Portal Gateways (underline link).

#### Known gotchas

- Counters cache in CloudFront for 60 s — a fresh notice may take up to a minute to appear.

- The hero background is a radial gold gradient at 8% opacity — do not brighten it or the serif headline loses contrast.

###  2 · Public notice board

The reverse-chronological list of every published notice. Fuzzy search, country/category filters, deadline chips and per-row EMD hints. This is the primary discovery surface for prospective bidders.

![Public notice board](../screens/02_public_notices.png)

*Public notice board*

#### Purpose

The reverse-chronological list of every published notice. Primary discovery surface for bidders and researchers.

#### How the workflow unfolds

1) Enter a keyword or filter by country / category. 2) Review the card headline, deadline and EMD hint. 3) Click a row to open the full public detail page.

#### Fields

- **Search box** — Fuzzy match on title, description, country and category — server side.

- **Country / Category filters** — Backed by the same masters used in the admin console.

- **Deadline chip** — Turns red at T-24 h to create urgency.

- **EMD hint** — Shows the EMD amount or percentage inline so bidders can pre-arrange the deposit.

#### Known gotchas

- Deadlines display in the visitor's local timezone; the backend stores UTC ISO strings.

###  3 · Live tenders listing

All tenders currently open for bidding. Same card structure as the notice board with a countdown chip on each card driving urgency.

![Live tenders listing](../screens/03_public_tenders_live.png)

*Live tenders listing*

#### Purpose

Filter of the notice board scoped to tenders currently open for bidding.

#### How the workflow unfolds

Bidders check this daily; the URL is optimised for RSS and Snapchat spotlight posts.

#### Fields

- **Countdown chip** — Live H:MM:SS to submission deadline.

- **Awarding authority** — Small navy tag on each card.

- **EMD hint** — Percentage or absolute value inline.

#### Known gotchas

- If the counter reads 0 despite live data, force a CloudFront invalidation.

###  4 · Completed tenders

Public archive of every tender that has passed its submission deadline. Awards, final prices and winning bidders are shown once the award is finalised and cleared for publication.

![Completed tenders](../screens/04_public_tenders_completed.png)

*Completed tenders*

#### Purpose

Public archive of every tender past its submission deadline.

#### How the workflow unfolds

Journalists, auditors and inbound partners use this to audit PMC's throughput.

#### Fields

- **Award column** — Winning bidder + final price once award is finalised and cleared for publication.

- **Signed award PDF** — Downloadable letter of award.

#### Known gotchas

- A tender only appears here after the award is confirmed and legal has flipped the publish flag.

###  5 · All tenders — unified archive

The combined live + completed archive with a status filter. Used by researchers, auditors, and inbound partners doing due diligence on PMC.

![All tenders — unified archive](../screens/05_public_tenders_all.png)

*All tenders — unified archive*

#### Purpose

The combined live+completed archive with a status filter.

#### How the workflow unfolds

Used by regulators, auditors and inbound partners doing due diligence on PMC.

#### Fields

- **Status filter** — Live / Completed / Cancelled / Withdrawn.

- **Column sort** — Deadline, budget, publish date, awarding authority.

#### Known gotchas

- Cancelled tenders keep their audit trail — never delete a notice, always withdraw it.

###  6 · About Us — company narrative

Editorial About page. Charter, milestones, leadership grid, sector coverage, and press quotes. All copy is content-managed via the notice-board CMS.

![About Us — company narrative](../screens/06_public_about.png)

*About Us — company narrative*

#### Purpose

Editorial About Us — company narrative, milestones, leadership grid, sector coverage, press quotes.

#### How the workflow unfolds

Marketing and BD share this URL with prospective GOC/Bank partners; it also drives Snapchat / Instagram profile clicks.

#### Fields

- **Charter** — One-paragraph mission statement — content-managed via CMS.

- **Milestones** — Chronological chips — feed this monthly during releases.

- **Leadership grid** — Portrait cards with role and short bio.

- **Press quotes** — Curated third-party validators.

#### Known gotchas

- Portraits should be square 512×512 PNGs sized ≤ 120 KB — larger images push the fold below the CTA.

###  7 · Vision & Mission

The strategic doctrine page — Vision, Mission, Values, and the North-Star KPIs the platform is optimised for. Used in tender-committee briefings.

![Vision & Mission](../screens/07_public_vision.png)

*Vision & Mission*

#### Purpose

The strategic doctrine page — Vision, Mission, Values, North-Star KPIs the platform is optimised for.

#### How the workflow unfolds

Referenced by the tender committee in every quarterly briefing. Also cited in ESG questionnaires.

#### Fields

- **Vision statement** — 10-year direction.

- **Mission** — 12-month operational focus.

- **Values** — Three principles used to arbitrate roadmap trade-offs.

- **North-star KPIs** — Cycle time, dispute rate, EMD-refund SLA, vendor NPS.

#### Known gotchas

- Whenever the North-Star KPIs change, re-open every tender committee meeting with the delta explained.

###  8 · Supplier registration — start

Public entry point for vendor self-onboarding. Email, company name, country. A magic link is dispatched via Resend and the bidder resumes the deep intake wizard from that link.

![Supplier registration — start](../screens/08_public_register.png)

*Supplier registration — start*

#### Purpose

Public entry point for vendor self-onboarding.

#### How the workflow unfolds

1) Bidder submits email + company + country. 2) A Resend magic link is emailed. 3) Bidder clicks the link and lands on RegistrationResume where the 5-step wizard begins.

#### Fields

- **Email** — Uniqueness enforced across tenants.

- **Company name (optional)** — Skipping this delays enrichment but does not block the wizard.

- **Country dropdown** — Sourced from the platform-wide country master.

#### Known gotchas

- Resend delivery to first-touch corporate mailboxes can hit spam — admins can resend from the Registrations queue.

###  9 · Sovereign Gateway — 5-portal picker

Five distinct credentials safeguard PMC. Selecting a card reveals a portal-specific credential form (per-role colour + badge).

![Sovereign Gateway — 5-portal picker](../screens/09_public_login_grid.png)

*Sovereign Gateway — 5-portal picker*

#### Purpose

The 5-portal Sovereign Gateway — the new single entry point for every human role.

#### How the workflow unfolds

Users pick the badge matching their role. Each card animates into a portal-specific credential form with the correct colour system, kicker, icon and CTA.

#### Fields

- **System Administrator** — Amber ring · SUPERVISORY · ROOT badge.

- **PMC Management** — Blue ring · EXECUTIVE badge.

- **Strategic Partners** — Cyan ring · GOC · BANK · REGULATOR badge.

- **Procurement Agents** — Emerald ring · FIELD OPS badge.

- **Registered Vendors** — Gold ring · BIDDER badge.

#### Known gotchas

- Each portal has its own audit-log tag — a single email that owns two roles will show up twice in the audit trail with the portal it entered through.

### 10 · Admin portal — credential form

The System Administrator portal — colours default to editorial slate + amber badge. Root-level control of the platform: user provisioning, master catalog, audit.

![Admin portal — credential form](../screens/10_public_login_admin.png)

*Admin portal — credential form*

#### Purpose

Credential form for the Admin portal.

#### How the workflow unfolds

The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).

#### Fields

- **Work email** — Email that appears in the audit trail.

- **Password** — 12+ characters; failures trigger the brute-force lockout after 5 attempts.

- **Portal briefing (right rail)** — Short brief so the user knows they're in the right door.

- **Session security note** — TLS 1.3 + PMC audit log — cite this in security reviews.

#### Known gotchas

- MFA is enforced for admin + management once configured — you get a code prompt after the password step.

### 11 · Management portal — credential form

The PMC Management portal — executive dashboards, committee outcomes and escrow-level financials.

![Management portal — credential form](../screens/11_public_login_management.png)

*Management portal — credential form*

#### Purpose

Credential form for the Management portal.

#### How the workflow unfolds

The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).

#### Fields

- **Work email** — Email that appears in the audit trail.

- **Password** — 12+ characters; failures trigger the brute-force lockout after 5 attempts.

- **Portal briefing (right rail)** — Short brief so the user knows they're in the right door.

- **Session security note** — TLS 1.3 + PMC audit log — cite this in security reviews.

#### Known gotchas

- MFA is enforced for admin + management once configured — you get a code prompt after the password step.

### 12 · Strategic Partners portal — credential form

For GOC / Bank / Regulator personas — bank-guarantee verification, regulatory audit hooks, co-procurement dashboards.

![Strategic Partners portal — credential form](../screens/12_public_login_partners.png)

*Strategic Partners portal — credential form*

#### Purpose

Credential form for the Partners portal.

#### How the workflow unfolds

The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).

#### Fields

- **Work email** — Email that appears in the audit trail.

- **Password** — 12+ characters; failures trigger the brute-force lockout after 5 attempts.

- **Portal briefing (right rail)** — Short brief so the user knows they're in the right door.

- **Session security note** — TLS 1.3 + PMC audit log — cite this in security reviews.

#### Known gotchas

- MFA is enforced for admin + management once configured — you get a code prompt after the password step.

### 13 · Procurement Agents portal — credential form

Field-ops portal for procurement agents drafting tenders, reviewing bidder dossiers, publishing corrigenda and verifying BOQ line items.

![Procurement Agents portal — credential form](../screens/13_public_login_agents.png)

*Procurement Agents portal — credential form*

#### Purpose

Credential form for the Agents portal.

#### How the workflow unfolds

The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).

#### Fields

- **Work email** — Email that appears in the audit trail.

- **Password** — 12+ characters; failures trigger the brute-force lockout after 5 attempts.

- **Portal briefing (right rail)** — Short brief so the user knows they're in the right door.

- **Session security note** — TLS 1.3 + PMC audit log — cite this in security reviews.

#### Known gotchas

- MFA is enforced for admin + management once configured — you get a code prompt after the password step.

### 14 · Registered Vendors portal — credential form

Bidder portal — purchase tender packs, submit digital bids, join live reverse auctions, sign contracts. Gold-accented CTA.

![Registered Vendors portal — credential form](../screens/14_public_login_vendors.png)

*Registered Vendors portal — credential form*

#### Purpose

Credential form for the Vendors portal.

#### How the workflow unfolds

The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).

#### Fields

- **Work email** — Email that appears in the audit trail.

- **Password** — 12+ characters; failures trigger the brute-force lockout after 5 attempts.

- **Portal briefing (right rail)** — Short brief so the user knows they're in the right door.

- **Session security note** — TLS 1.3 + PMC audit log — cite this in security reviews.

#### Known gotchas

- MFA is enforced for admin + management once configured — you get a code prompt after the password step.

## 5 · Vendor / supplier journey

### 30 · Vendor landing (post-login)

Vendor dashboard immediately after sign-in. Header shows company + trust badges; body shows open tenders, held EMDs, active auctions.

![Vendor landing (post-login)](../screens/30_vendor_landing.png)

*Vendor landing (post-login)*

#### Purpose

Vendor dashboard immediately after sign-in.

#### How the workflow unfolds

Bidders arrive here after credential submit. Header shows the trust badges, body shows quick paths to open tenders, held EMDs, active auctions, awarded contracts.

#### Fields

- **Trust badges** — Aggregate rating badge + certified-supplier chip if applicable.

- **Open tenders card** — Categories filtered to the vendor's declared industries.

- **EMDs held** — Total value + release-eligible-date.

- **Auctions strip** — Live and scheduled reverse-auction rooms.

#### Known gotchas

- The dashboard refetches on every route change to avoid stale counts.

### 31 · Vendor · Open tenders

Tenders the vendor may bid on, filtered to declared categories.

![Vendor · Open tenders](../screens/31_vendor_tenders.png)

*Vendor · Open tenders*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 32 · Vendor · My bids

Every submitted bid with envelope status, score summary and award outcome.

![Vendor · My bids](../screens/32_vendor_bids.png)

*Vendor · My bids*

#### Purpose

My bids — every submitted bid with envelope status, score summary and award outcome.

#### How the workflow unfolds

Bidders use this to prove submission for legal disputes and to compare pricing against their prior wins.

#### Fields

- **Bid ref** — PMC-BID-YYYY-NNNN — anchor for every legal reference.

- **Envelope status** — Sealed / Unsealed / Under evaluation / Awarded / Rejected.

- **Score summary** — Technical + commercial weighted score once the envelope is unsealed.

- **Award outcome** — Won / Runner-up / Not qualified.

#### Known gotchas

- A rejected bid keeps its EMD until the notice's dispute window closes.

### 33 · Vendor · Ratings received

Reviews left by admins post-contract with an aggregate trust badge.

![Vendor · Ratings received](../screens/33_vendor_rate.png)

*Vendor · Ratings received*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 34 · Vendor · Contract signatures

DocuSign envelopes pending / signed by the vendor.

![Vendor · Contract signatures](../screens/34_vendor_signatures.png)

*Vendor · Contract signatures*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

## 6 · Admin console — full module tour

### 50 · Admin console landing (Operations Overview)

First screen after admin login — collapsible sidebar grouped into Overview / Procurement / Market / Money & Compliance / Events, environment chip, AI Copilot shortcut.

![Admin console landing (Operations Overview)](../screens/50_admin_landing.png)

*Admin console landing (Operations Overview)*

#### Purpose

Command centre for PMC staff.

#### How the workflow unfolds

Admin arrives here after sign-in; the collapsible sidebar groups 23 modules into Overview / Procurement / Market / Money & Compliance / Events — matching the mental model of the PMC operations team.

#### Fields

- **Sidebar groups** — Overview · Procurement · Market · Money & Compliance · Events.

- **Environment chip** — Which tenant/programme is active.

- **AI Copilot** — In-context question box for procurement policy questions.

- **Alerts strip** — Aging EMDs, publish-ready notices, contract SLA breaches.

#### Known gotchas

- Some tabs require role escalation (e.g. Escrow needs escrow_agent) — a locked-tab tooltip explains.

### 52 · Admin · Audit trail

Immutable action log with entity filters.

![Admin · Audit trail](../screens/52_admin_audit.png)

*Admin · Audit trail*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 53 · Admin · Notices — publish & manage

Create, publish, edit, withdraw, attach documents, EMD.

![Admin · Notices — publish & manage](../screens/53_admin_notices.png)

*Admin · Notices — publish & manage*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 55 · Admin · Tender Builder & DPR AI

Master library, DPR deep-dive, AI Fill All, PDF export.

![Admin · Tender Builder & DPR AI](../screens/55_admin_tender-builder.png)

*Admin · Tender Builder & DPR AI*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 57 · Admin · Work packages

Modular deliverable packages for the KZ programme.

![Admin · Work packages](../screens/57_admin_packages.png)

*Admin · Work packages*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 59 · Admin · Vendor directory

Full CRUD on suppliers, licences, compliance, tenants.

![Admin · Vendor directory](../screens/59_admin_vendors.png)

*Admin · Vendor directory*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 61 · Admin · Vendor intel & ratings

Trust badges, moderation, criteria averages.

![Admin · Vendor intel & ratings](../screens/61_admin_vintel.png)

*Admin · Vendor intel & ratings*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 63 · Admin · Escrow / EMD desk

EMD receipts, forfeitures, refunds.

![Admin · Escrow / EMD desk](../screens/63_admin_escrow.png)

*Admin · Escrow / EMD desk*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 65 · Admin · Evaluation & scoring

Technical + financial scoring, QCBS, L1 comparison, envelope locking.

![Admin · Evaluation & scoring](../screens/65_admin_evaluation.png)

*Admin · Evaluation & scoring*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 67 · Admin · Awards & POs

Letters of award, POs, contract award workflow.

![Admin · Awards & POs](../screens/67_admin_awards.png)

*Admin · Awards & POs*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 69 · Admin · Roles & permissions

Fine-grained ACL matrix.

![Admin · Roles & permissions](../screens/69_admin_permissions.png)

*Admin · Roles & permissions*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 70 · Admin · Reverse auctions

Live auction rooms, invitations, spectator link.

![Admin · Reverse auctions](../screens/70_admin_auctions.png)

*Admin · Reverse auctions*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

### 72 · Admin · Masters — fees, roles, EMD

Fee slabs, staff roles, criteria, categories, countries.

![Admin · Masters — fees, roles, EMD](../screens/72_admin_masters.png)

*Admin · Masters — fees, roles, EMD*

#### How to use

This screen exposes every action available for its module. Use the InfoDot (ⓘ) next to each label to see the field-level rules — hover it in-app for the full policy text. All destructive actions confirm before applying, and every mutation is written to the immutable audit log.

## 7 · Deep-dive: Tender Builder & AI DPR (v46l map-reduce)

v46l ships the most substantial AI upgrade to date: **unlimited DPR ingestion + background workers**. The pipeline turns any Detailed Project Report — up to 100 MB, 500+ pages — into a fully structured tender pack.

**Extraction.** PDFs decode via pypdf, DOCX via python-docx, TXT direct. The extracted text is chunked into 40 KB windows with 3 KB overlap to preserve context across boundaries. The MAX_CHUNKS ceiling is 500 (configurable via `DPR_MAX_CHUNKS`) — the previous 20-chunk cap is removed.

**Pass 1a — per-chunk map.** Each chunk is sent to the LLM with a strict JSON contract requesting header hints (work title, budget, deadlines, EMD) and a list of sections observed in that chunk. Bounded concurrency via an asyncio semaphore of 4 so the LLM proxy is never saturated.

**Pass 1b — reduce.** Local blueprints are merged: header hints first-wins across chunks (rich early chunks dominate), section list is deduplicated by title. Sections cap at 60 (was 30).

**Pass 2 — draft.** Each discovered section is drafted from the passage of the DPR most relevant to its anchor phrase (LLM-provided) or title. Bounded concurrency of 6. Bodies under 200 chars trigger the raw-passage fallback so nothing lands as a stub.

**Progress + async.** Files ≥ 4 MB take the async path. The frontend posts to `/dpr/analyze-async`, gets a `job_id` and polls `/dpr/jobs/{id}` every 3 s until status == done. Every phase writes a percentage + human phase string into the `dpr_jobs` collection (`mapping 6/14`, `drafting 22/58`, `complete`) so the UI shows a real progress bar.

**Nginx tuning.** `.platform/nginx/conf.d/proxy.conf` sets `client_max_body_size 200M` and all timeouts to `300s` so multi-hundred-MB base64 payloads do not trigger 413 or idle timeouts.

## 8 · Deep-dive: Evaluation, awards & escrow

**Rubric.** Every notice defines a scoring rubric — a list of technical criteria with weights summing to 1.00, a commercial weight, and a minimum technical cutoff percentage. RubricEditor enforces every constraint client-side and disables Save until valid.

**Envelope lock.** Once the technical envelope is locked (`POST /api/v1/evaluations/lock-envelope`) the backend refuses new scores (409). v46m hardens this to also refuse re-lock — a rogue direct API call cannot silently overwrite the lock timestamp / attribution. The frontend fetches `GET /evaluations/lock-state/{ref}` on every notice-ref change and swaps Lock buttons to a 'Sealed 🔒' chip with a green banner showing the sealer and timestamp.

**Award report.** With both envelopes sealed, the award report combines weighted technical + commercial scores, applies the technical cutoff, and produces the L1 comparison table. Ties are broken by lower price, then earlier submission timestamp, then higher aggregate rating.

**Escrow.** The joint-account model requires two officers per transaction. The account snapshot is stored on every escrow_transaction row so a later officer roster change does not retroactively affect audit history.

## 9 · Deep-dive: Reverse auctions

Reverse auctions run only for tenders that opt in. Qualified vendors receive an invitation, join with a masked alias (never their company name), and place manual or auto bids.

**Auto-bid** — Vendors set a walk-away floor. The platform undercuts the current lowest by min_decrement whenever the vendor is not the leader, until the vendor hits the floor.

**Anti-sniping** — Bids placed in the final 60 seconds extend the auction by 5 minutes so no one can win by ambushing at the buzzer.

**Public spectator link** — Auditors watch the room via a read-only URL with masked aliases so bidder identity is never exposed even in the audit trail.

## 10 · Tooltip, error-handling & offline system

Three complementary UX safeties keep the platform legible under stress.

**InfoDot (ⓘ)** — Hover tooltip used **166 times** across 20+ admin panels. Every field label with a non-obvious policy has one attached. Source: `frontend/src/components/InfoDot.jsx`.

**`showApiError` / `formatApiError`** — 67 files consume these helpers. Every server error surfaces as a sonner toast with the exact backend detail (never a bare stack trace). The toast is dismissible but not auto-hidden so users can copy the error string into support tickets.

**ErrorBoundary** — mounted at the app root; catches any React crash and renders a graceful fallback with a copyable diagnostic id. Never blocks the entire app.

**Offline** — The service worker was deliberately un-registered in v46 after a stale-cache incident. The current build ships a self-destruct SW that unregisters itself on load. Do not re-enable without adding a cache-busting query string strategy.

## 11 · Deployment runbook (S3 + CloudFront + Elastic Beanstalk)

**Frontend.** Build with `REACT_APP_BACKEND_URL="" yarn build` so the bundle uses same-origin `/api` calls. Sync to S3 with `--exact-timestamps` and `--exclude "downloads/*"` to preserve the public download folder. Invalidate CloudFront `/*` after the sync.

**Backend.** Package `backend/`, `.platform/nginx/conf.d/proxy.conf`, `Dockerfile`, `Dockerrun.aws.json`, `VERSION` into a zip. Never bundle `backend/.env` — use EB environment properties. Deploy via `eb deploy --staged --label vXX`.

**Never** run `aws s3 sync ... --delete` at bucket root — it will delete the public `/downloads/` folder and every manual/artifact in it.

**Rollback.** Elastic Beanstalk keeps every prior version; roll back via the EB console → Application versions → Deploy previous.

## 12 · Troubleshooting playbook

| Symptom | Root cause | Fix |
|---|---|---|
| Landing shows 0 counters | Stale CloudFront cache | Invalidate `/*` on CloudFront |
| 'No matching employee' toast | Preview URL baked into prod bundle | Rebuild with `REACT_APP_BACKEND_URL="" yarn build` |
| DPR returns 5 generic sections | Backend on ≤ v46g | Deploy v46l map-reduce backend |
| Progress bar stuck at 2% | Async worker crashed | Check `/api/v1/tender-pro/dpr/jobs/{id}` for `error` field |
| 413 on large DPR | nginx body limit | Deploy v46l — `client_max_body_size 200M` |
| Login OK but /admin bounces | Cross-site cookie blocked | Ensure frontend calls same-origin `/api` |
| Envelope re-locks silently | Direct API bypasses UI | v46m rejects re-lock with 409 |
| Auction bidder identity leaks | Masked alias not applied | Re-open room; masking is server-side |
| Refund never reaches vendor | Second signer missed the notification | Check joint-account snapshot on the transaction |
| Resend email lands in spam | First-touch corporate MX filter | Resend from Registrations queue with a warm-up sender |


## 13 · API reference index

| Endpoint | Purpose |
|---|---|
| `GET  /api/v1/meta/public/stats` | Public — landing KPIs. |
| `GET  /api/v1/meta/public/notices` | Public — list notices. |
| `POST /api/v1/admin/auth/login` | Admin realm login (cookie). |
| `POST /api/v1/staff/auth/login` | Staff realm login. |
| `POST /api/v1/vendor/auth/login` | Vendor realm login. |
| `POST /api/v1/registrations/draft` | Create registration draft. |
| `POST /api/v1/registrations/submit` | Submit for review. |
| `POST /api/v1/tender-pro/dpr/analyze-json` | Synchronous DPR analysis (< 4 MB). |
| `POST /api/v1/tender-pro/dpr/analyze-async` | **v46l** kick off async DPR analysis. |
| `GET  /api/v1/tender-pro/dpr/jobs/{id}` | **v46l** poll async DPR job status. |
| `POST /api/v1/tender-pro/templates/{id}/save-as-master` | Promote a draft to a reusable master. |
| `POST /api/v1/evaluations/rubric` | Upsert rubric for a notice. |
| `POST /api/v1/evaluations/lock-envelope` | **v46m** now refuses re-lock (409). |
| `GET  /api/v1/evaluations/lock-state/{ref}` | **v46m** returns seal timestamps + attribution. |
| `POST /api/v1/evaluations/score` | Submit a technical or commercial score. |
| `GET  /api/v1/evaluations/award-report/{ref}` | Generate the L1 comparison. |
| `POST /api/v1/escrow/transactions` | Record an EMD transaction. |
| `POST /api/v1/auctions/{ref}/bid` | Place an auction bid. |
| `POST /api/v1/reports/snapshot` | Persist stakeholder-report artefacts to disk. |
| `GET  /api/v1/stakeholder-reports/*` | Tenders / awards / escrow / SLA reports. |


## 14 · Release history

| Version | Highlights |
|---|---|
| **v46m** | Bug Blitz Round Two — envelope re-lock 409, GET /lock-state, EvaluationPanel sealed banner, AuctionRoom mobile overflow fix. |
| **v46l** | Unlimited DPR + async worker (MAX_CHUNKS 500, /dpr/analyze-async, /dpr/jobs/{id}, nginx 200 MB / 300 s, live progress bar). |
| **v46k** | Sovereign Redesign — 5-portal Sovereign Gateway, navy/gold editorial home hero, PmcFooter with social icons. |
| **v46j** | Map-Reduce DPR first cut (still capped at 800 KB). |
| **v46i** | New roles (management/partner/agent), collapsible admin sidebar, editorial public design v1. |
| **v46h** | Admin vendor form: per-section Save buttons + search. |
| **v46g** | DPR deep-dive first cut (26 sections from KMT). |
| **v46f** | Editable tender name + reliable save-as-master. |
| **v46e/d/c/b** | Bug blitz first pass — 60+ tracker items fixed. |


## 15 · Glossary & appendix

- **DPR** — Detailed Project Report — the source document the AI ingests to draft a tender pack.
- **EMD** — Earnest Money Deposit — refundable bid security.
- **QCBS** — Quality- & Cost-Based Selection — the default 70/30 evaluation weighting.
- **L1** — Lowest financial bid post-technical qualification.
- **BOQ** — Bill of Quantities — itemised deliverable+rate schedule.
- **Corrigendum** — Official post-publication amendment to a notice.
- **LOA** — Letter of Award — signed offer letter to the L1 vendor.
- **PO** — Purchase Order — issued after the LOA is accepted.
- **Envelope** — A sealed batch of bid data — technical or commercial.
- **Trust badge** — Bronze / Silver / Gold / Platinum tier surfaced on the public vendor profile.
- **Master** — A reusable Tender Builder template keyed by country + industry.
- **Sovereign Gateway** — The v46k 5-portal login picker.
- **Async pipeline** — The v46l background DPR worker — kicked via /dpr/analyze-async.
- **Sealed 🔒** — The v46m evaluation-panel indicator that an envelope is locked.

## 16 · Role-by-role onboarding checklist (30 / 60 / 90 days)

Every new hire follows the same three-milestone rhythm.

**Admin — Day 1** — shadow an experienced admin through a full tender lifecycle (draft → publish → bid receipt → evaluation → award → contract). Read chapters 1–3 and 7–11.

**Admin — Day 30** — publish your first tender end-to-end unsupervised. Own one committee evaluation cycle. Complete audit-trail search drills for two entity types.

**Admin — Day 60** — configure a new country's masters (EMD, fee, category taxonomy, staff roles). Run one Tender Builder DPR ingestion on a 500-page tender.

**Admin — Day 90** — lead a full quarterly stakeholder-report cycle. Present KPI trends to the Management portal.

**Vendor onboarder (Support)** — Day 1: shadow a live activation. Day 30: process 10 registrations solo. Day 60: own resend-link edge cases and licence re-verification queues. Day 90: run a vendor-education webinar.

**Escrow officer** — Day 1: read the joint-account snapshot model. Day 30: process 20 EMD receipts + 10 refunds. Day 60: handle one forfeiture with legal sign-off. Day 90: lead a monthly reconciliation against Stripe.

**Committee member** — Day 1: complete the COI declaration training. Day 30: score 3 evaluations under a senior member. Day 60: lead one evaluation session. Day 90: chair a full committee meeting including minutes and public Q&A migration.

## 17 · Monthly operations cadence

The rhythm PMC has settled on across six months of live operations.

**Week 1** — Publish weekly digest via Resend. Reconcile prior-month escrow ledger. Publish stakeholder monthly report (tenders / awards / escrow / SLA).

**Week 2** — Committee cycle for tenders whose submission deadline landed in the prior week.

**Week 3** — Award ceremonies + DocuSign countersign push. Vendor invoicing run.

**Week 4** — Roadmap review with GOC + Bank partners. Vendor NPS survey via Resend. Category taxonomy audit.

## 18 · North-Star KPIs and dashboards

| KPI | Definition | Target | Notes |
|---|---|---|---|
| Notice cycle time | Draft → Publish | ≤ 14 days | Every published notice contributes its `published_at - draft_created_at`. |
| Bidder attention | Bidders opening a notice / eligible bidders | ≥ 65 % | Analytics funnel first stage. |
| Bids per notice | Median across last 90 days | ≥ 4 | Signals healthy competition; below 3 triggers a category audit. |
| Technical qualification rate | Technically qualified / bids received | 40–65 % | Too low → tender spec too strict; too high → not selective enough. |
| EMD refund SLA | Refund issued / eligible transactions in 30 days | 100 % | Any breach opens an escrow post-mortem. |
| Contract signature SLA | LOA → PMC countersign | ≤ 10 business days | Legal team KPI. |
| Vendor NPS | Quarterly survey | ≥ 42 | Below 30 triggers a vendor-experience review. |
| Dispute rate | Opened disputes / awarded contracts | ≤ 3 % | Above 5 % opens a legal + evaluation review. |


## 19 · Escalation matrix

| Situation | First responder | 15 min | 1 h | 4 h | Owner |
|---|---|---|---|---|---|
| Auth outage | On-call admin | On-call engineer | CTO | CEO | CTO |
| EMD refund overdue > 60 days | Escrow officer | Legal | Escrow lead | CFO | CFO |
| Suspicious auction pattern | Auction ops | AI anomaly rerun | Legal | CEO | Legal |
| Data breach suspected | Any staff | CTO | CEO | Communications | CTO |
| Regulator inbound | Any staff | Partner lead | CEO | Board | Partner lead |


## 20 · Keyboard shortcuts

| Shortcut | Action |
|---|---|
| ⌘ + K | Global command palette (planned) |
| G then A | Jump to Analytics |
| G then N | Jump to Notices |
| G then T | Jump to Tender Builder |
| G then E | Jump to Evaluation |
| Esc | Close any open modal |
| / | Focus the primary search box |
| Shift + ? | Show the shortcut cheat sheet (planned) |


## 21 · Frequently asked questions (FAQ)

**Q — Can I edit a published notice?**

No — publish a corrigendum. The audit trail keeps every prior state and public visitors see the corrigendum immediately on the notice detail page.



**Q — How do I recover a lost tender draft?**

Every save is a rolling snapshot. Open Tender Builder → Version history and restore any prior snapshot; the restore itself is auto-snapshotted so it is undoable.



**Q — A vendor says they never received a fee invoice.**

Check the Billing tab for the invoice PDF and the Resend delivery log. If the email failed, resend from Billing → Row action. Corporate MX filters sometimes block first-touch domains — use the warm-up sender when needed.



**Q — How large a DPR can the AI ingest?**

v46l allows 100 MB per file / 500+ pages. Files ≥ 4 MB automatically use the async worker and show a live progress bar; you can leave the tab open and come back.



**Q — Can I re-open a locked evaluation envelope?**

No. v46m rejects re-lock with a 409. If you truly need to redo scoring, clone the notice into a new tender and re-run the evaluation cycle. Legal must approve.



**Q — How do I add a new country to the platform?**

Masters → Countries → New. Then seed EMD/fee slabs, category taxonomy, licences and staff roles for that country. The public homepage and registration wizard update immediately.



**Q — How does the AI avoid inventing numbers not present in the DPR?**

The section-drafting prompt forbids inventing numbers, and each draft is passed the specific DPR passage anchored to the section title. Bodies under 200 chars trigger the raw-passage fallback so no output is generated without source.



**Q — Where do I turn off email digests?**

Vendors: Vendor portal → Notifications. Staff: Profile → Preferences (planned).



**Q — How is bidder identity protected in reverse auctions?**

Masked aliases assigned server-side on join. Even the audit trail stores only aliases; de-masking is admin-only post-close.



**Q — A stakeholder-report artefact failed to snapshot. What now?**

Every artefact is wrapped in its own try/except; the response returns a JSON `errors[]` array listing which artefact failed and why. Fix the specific artefact and re-hit /reports/snapshot — the rest are unaffected.



## 22 · Sample workflow — full lifecycle of one tender

The end-to-end journey for a single procurement, from concept to close-out.

**Day 0** — Package owner briefs the drafting agent. Agent opens Tender Builder → picks the country → picks or creates a master → opens the DPR modal and uploads the project brief. AI drafts every section body from the DPR passages. Agent reviews, adjusts EMD/fee, uploads BOQ CSV, saves the draft.

**Day 3** — Legal counsel reviews. Any redlines go into a version snapshot. Legal signs off. Agent hits Publish. Resend digests fire to subscribed vendors. Snapchat + Instagram posts pushed automatically.

**Day 3–17** — Pre-bid meeting held via Zoom on Day 5. Minutes uploaded, substantive Q&A migrated to the public notice. Corrigenda published as needed. Bidders purchase the tender pack; EMDs post to escrow.

**Day 18** — Submission deadline. Admin locks technical envelope; the button flips to 'Sealed 🔒' and a green banner records the sealer and timestamp.

**Day 18–28** — Evaluation committee scores technical. Rubric errors block invalid saves. Once all evaluators have submitted, admin locks commercial envelope. Committee scores commercial. Admin generates the award report → L1 identified.

**Day 29** — LOA issued via DocuSign. Vendor accepts; PMC countersigns. PO number generated.

**Day 30–...** — Contract runs. Milestones, timesheets, variation orders logged. EMD refunded on Day N post-close unless disputed. Vendor rating captured. Auditor exports the CSV bundle if requested.

## 23 · Data model appendix

| Collection | Purpose | Hot indices |
|---|---|---|
| tenants | Multi-tenant scoping | code (unique) |
| admin_users / staff_users / vendors | Auth realms | email (unique per tenant) |
| notices | Published tender notices | notice_ref (unique), published_at, country |
| tender_templates | Reusable master + drafts | (country, industry), is_master |
| registrations | Vendor onboarding wizard state | magic_token, email, status |
| bids | Submitted bids | notice_ref, vendor_ref |
| rubrics | Per-notice scoring config | notice_ref (unique) |
| scores | Evaluator scores | bid_id, evaluator |
| escrow_transactions | EMDs held/refunded/forfeited | notice_ref, status |
| auctions | Reverse auction rooms | notice_ref (unique) |
| corrigenda | Notice amendments | notice_ref, published_at |
| audits | Immutable audit trail | entity_ref, actor_id, at |
| ratings | Post-contract reviews | vendor_ref |
| dpr_jobs | v46l async DPR workers | _id, status |
| reports_snapshots | Materialised stakeholder artefacts | generated_at |


## 24 · Appendix — release notes archive

**v46m** — Bug Blitz Round Two — envelope re-lock 409, GET /lock-state, EvaluationPanel sealed banner, AuctionRoom mobile overflow fix.

**v46l** — Unlimited DPR + async worker (MAX_CHUNKS 500, /dpr/analyze-async, /dpr/jobs/{id}, nginx 200 MB / 300 s, live progress bar).

**v46k** — Sovereign Redesign — 5-portal Sovereign Gateway, navy/gold editorial home hero, PmcFooter with social icons.

**v46j** — Map-Reduce DPR first cut (still capped at 800 KB).

**v46i** — New roles (management/partner/agent), collapsible admin sidebar, editorial public design v1.

**v46h** — Admin vendor form: per-section Save buttons + search.

**v46g** — DPR deep-dive first cut (26 sections from KMT).

**v46f** — Editable tender name + reliable save-as-master.

**v46e/d/c/b** — Bug blitz first pass — 60+ tracker items fixed.

## 25 · Sign-off

This manual is versioned and lives under `/app/deliverables/v46_manual/build/`. The source Markdown is the single source of truth; DOCX and PDF are regenerated from it via `python3 /app/tools/manual/build.py`. Screenshots are re-captured via `python3 /app/tools/manual/capture.py`. Refresh both artefacts after every material release.
