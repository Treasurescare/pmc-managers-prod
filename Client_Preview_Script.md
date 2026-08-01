# PMC Managers v2 — Client Preview Script

**Audience:** Kazakhstan client stakeholder(s) reviewing the v2 pilot before Phase-2 AWS migration
**Duration:** 20–25 min walk-through
**Environment:** Preview URL (single-tenant pilot). Real fund flows, Object Lock evidence, and Cognito MFA come in Phase 2 per Build Sheet v2 and Transaction Structure Report.

---

## 0 · Frame the meeting (2 min)

Open with the three-sentence framing so nobody is confused about what they're looking at:

> "This is the pilot. It follows the exact API and data model from the AWS Build Sheet v2, but runs on our development stack for speed and cost. Every screen you'll see today ports 1-for-1 to AWS (RDS PostgreSQL + Cognito + S3 Object Lock + Fargate) in Phase 2 without rewriting the frontend. We built it this way so we can test the workflow live with your team while the legal appointments in the Transaction Structure Report are being finalised."

Then set expectations:
- **In scope today:** Public notice board, vendor registration Sections A–E, admin review workflow, package tracker, audit trail
- **Not in scope today (per Build Sheet Part 5):** bidding, evaluation scoring, contract award, real payment processing, milestone evidence capture (App 1)
- **Not activated today (per Transaction Structure Report §9):** vendor fee collection, EMD flows — these await counsel sign-off on the 6 open legal questions

---

## 1 · The Public Tender Notice Board (3 min)

**URL:** `/` (base of the preview URL)

Show:
- **Hero panel** — "Open tender notices across the Kazakhstan programme" with live counters for notices published, suppliers approved, packages
- **Filter chips** — All / Tender / RFP / RFQ + country dropdown
- **3 seeded demo notices** — Modular OTs, Grid Connection RFP, Hostel Plumbing RFQ

**Key point to make:**
> "This board is public and SEO-indexable. Any global vendor can find open tenders without logging in. There's no bidding here — this is the equivalent of the government-portal notice board, adapted for a private developer."

Click into **Modular OT Suite** (Notice `PMC-NOT-2026-0001`):
- Full scope-of-work on the left
- Right rail: Category, Country, Indicative Budget, Submission Deadline, **Required KZ Licenses** (auto-attached from Medical gas installation + Mechanical works), Procurement contact
- **"Register as a supplier to participate"** CTA — the only action from the public side

**Key point:**
> "The KZ licenses under 'Required' are attached automatically from the category. Any supplier who doesn't hold those licenses can still see the notice, but our system won't let them bid when bidding activates in a later phase."

Switch language: **EN → RU → KK** using the top-right switcher. Show the same page in Russian and Kazakh instantly.

---

## 2 · Supplier Registration (Sections A–E) (7 min)

**URL:** `/register`

Show:
- Enter a demo business email (e.g., `demo.supplier@kazenergy.kz`)
- Country pre-selected as Kazakhstan
- Click **"Send me a resume link"** — in production this emails a magic link; in the pilot we redirect immediately for demo speed

Now on **Section A · Identity & Basic Information:**
- Fill company name, address, registration number, entity type
- Note: 30 countries in the dropdown, KZ default
- Click **"Save draft"** → toast "Saved" (real DB write)
- Click **Next →**

**Section B · Contact & Signatory** — contact name, phone, email + authorised signatory block
**Section C · Banking & Financial** — bank details, SWIFT, 3 years turnover
**Section D · Business Profile & Capability:**
- Primary sector, business description
- Operating regions & categories (comma-separated for pilot; Phase 2 gets multi-select)
- **KZ Licenses held** — 6 checkbox options mapped to the 6 KZ license types from the domain model

**Section E · Documents, Declarations & Signature:**
- Show the **6 declarations** — conflict of interest, integrity, accuracy, data consent, fee acknowledgement, notification consent
- Signature name / title / date
- **Submit for review** is disabled until all 6 declarations are checked

Click Submit → status becomes `submitted` → confirmation screen.

**Key point:**
> "Every field, declaration and status transition matches the approved Pre-Tender Registration form from the v1 spec. What we changed: the form is now bilingual with a magic-link resume flow, so a vendor can start on their phone and finish on their laptop days later. Only the 6-declaration lock at submit is a hard gate — the rest of the form saves progressively."

---

## 3 · Admin Console — Reviewer Workflow (5 min)

**URL:** `/admin/login`
**Credentials:** `admin@pmcmanagers.com` / `Admin@123`

Show:
- Split-layout login — navy-trust institutional aesthetic
- Sign in

**Tab 1 · Registrations:**
- The registration you just submitted is now in the `submitted` filter
- Click into it — full detail view with reg number, entity type, primary sector, KZ licenses, business description
- Three decision buttons:
  - **Approve** → assigns `PMC-SUP-000001` supplier ref + creates vendor record + emails vendor
  - **Request clarification** → notes required → registration goes back to `needs_clarification` (vendor gets email with reviewer notes, can resume via same magic link)
  - **Reject** → notes required → vendor gets email
- Demo: click **Approve** — supplier reference appears, vendor now in `approved` list

**Tab 2 · Notices:**
- Click **New notice**
- Fill a demo notice (title, description, category, deadline, budget)
- Check "Publish immediately"
- Click **Create notice**
- Refresh the public `/notices` page in another tab → the new notice appears

**Tab 3 · Packages:**
- 30 KZ packages already seeded across health, utilities, hostel, hotel, academic
- Kanban-style status columns: Backlog → Scoping → SBD Draft → Ready → Published → Cancelled
- **Drag a package** from Backlog to Scoping — status persists to DB and writes an audit event
- **Import CSV** button — accepts columns `title, category, phase, value, currency, float_target_date, status` — reports created/skipped counts

**Tab 4 · Audit:**
- Every action from the demo has already been logged: `registration.submit`, `registration.approve`, `notice.create`, `package.status`
- Click **Verify chain** → returns `Chain verified · N events`
- **Key point:** "This is an application-level SHA-256 hash chain. In Phase 2 the same events land in PostgreSQL with append-only triggers + evidence attachments in S3 Object Lock (Compliance Mode) — which is the property that makes the record credible to a regulator or an underwriter."

---

## 4 · What Phase 2 Adds (3 min — no demo, whiteboard-style)

State clearly what does NOT exist today, and why that's deliberate:

| Feature | Phase 1 (today) | Phase 2 (AWS) |
|---|---|---|
| Storage | MongoDB, single-tenant | RDS PostgreSQL 16 Multi-AZ, RLS multi-tenant |
| Auth | JWT local | AWS Cognito with MFA mandatory for admin |
| Evidence | In-DB blobs | S3 Object Lock, 7-year Compliance Mode |
| Milestone Evidence App | Deferred — needs Object Lock | React Native offline-first mobile |
| Bidding, scoring, award | Not in scope | Not in scope until Transaction Structure §9 legal Qs cleared |
| EMD & fees | Not activated | Escrow agent + guarantee bank hold funds (never PMC) |
| Deployment | Emergent-managed preview | Terraform-provisioned AWS, Kazakhstan region |

**Key point:**
> "The three things that make the platform regulator-grade — Object Lock evidence, RLS-enforced multi-tenancy, and Cognito MFA — cannot be simulated on the pilot stack. Those are the only irreversible upgrades in Phase 2. Everything else in this pilot moves to AWS without a rewrite."

---

## 5 · Open Legal & Governance Questions (3 min)

Reference the Transaction Structure Report §9 and walk the client through the 6 open questions blocking real-money activation:

1. Land-grant / investment-agreement procurement obligations?
2. Concession or PPP status under Kazakh law?
3. Legality of vendor verification/document fees as a service fee?
4. Who lawfully holds EMD, performance bonds, retention?
5. Float-interest entitlement + disclosure?
6. Bond terms — restrictions on any of the flows above?

**Key point:**
> "Until UK, Kazakhstan and Luxembourg counsel answer these six questions, we keep every money flow disabled in the platform. The screens you saw today all work in 'pilot mode' — no real fees, no real EMD. The moment counsel signs off on any one question, we turn on the corresponding flow. Nothing gets built on assumptions."

---

## 6 · Sign-off Checklist (2 min)

Get concrete answers before the meeting ends:

- [ ] Client approves the pilot look, feel, and flow (or requests changes)
- [ ] Client nominates a **legal counsel primary contact** for the 6 open questions
- [ ] Client confirms **AWS account** availability (payer, region) for Phase 2 provisioning
- [ ] Client confirms **GitHub org** access to `pmc-tender-v2-aws` for code review
- [ ] Client identifies **first 5 pilot vendors** we invite to test the registration flow live
- [ ] Client identifies **first 5–10 packages** they want published in the next 2 weeks

---

## 7 · Q&A Anticipation

Prepare answers for the most likely questions:

**"Can we use this for real tenders today?"**
> "You can accept vendor registrations today, publish notices, and manage the internal package pipeline. You cannot collect vendor fees, take EMD, or run a bid/award because those require the legal appointments to be in place. That's a governance decision, not a technical one."

**"How long is Phase 2?"**
> "4–7 weeks assuming the AWS account and GitHub org are ready and legal counsel is progressing in parallel. Terraform provisions weeks 1–2, App migrations weeks 3–5, cutover week 6."

**"What happens to the v1 platform?"**
> "It's archived in a private GitHub repo (`pmc-tender-v1-legacy`, tag v1.0) as a functional reference. Nothing running publicly. It was superseded because it doesn't meet the Kazakhstan legal validity requirements — that's precisely why we've done the redesign."

**"Can we brand it further — colors, logo, hero images?"**
> "Yes, the design language sits in a single stylesheet (`design_guidelines.md` + `index.css`). Any brand refresh is a 1-day change. We chose the Navy Trust palette as institutional-default; happy to iterate."

**"When can our vendors register?"**
> "As soon as you sign off on the meeting today. The public URL is live now. We recommend a soft launch with 5–10 pilot vendors before opening the door widely."

---

## Notes for the presenter

- Keep the demo device on a stable network — the notice board and admin console both call live APIs
- Have `admin@pmcmanagers.com` / `Admin@123` pre-typed on a sticky note; do not paste passwords on screen
- If a demo action fails, refresh once; if it fails twice, skip to the next tab — don't fight the pilot
- Do NOT commit to Phase-2 timelines that assume legal counsel is done; always caveat with "assuming §9 progresses in parallel"
- Do NOT show the audit-verify button working across a database restart in this demo — the audit chain is intentionally seed-independent
