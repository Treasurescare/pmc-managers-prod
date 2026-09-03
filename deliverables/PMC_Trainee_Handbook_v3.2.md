# PMC Managers v2 — Trainee & User Handbook
*Version 3.2 · Full-module edition*

Generated September 03, 2026

## Table of contents
1. [Introduction & Roles](#chapter-1-introduction--roles)
2. [Notices](#chapter-2-notices)
3. [Corrigenda](#chapter-3-corrigenda)
4. [Tender Builder](#chapter-4-tender-builder)
5. [Bidding Ops](#chapter-5-bidding-ops)
6. [Reverse Auctions](#chapter-6-reverse-auctions)
7. [Escrow (EMD)](#chapter-7-escrow-(emd))
8. [Evaluation](#chapter-8-evaluation)
9. [Awards & POs](#chapter-9-awards--pos)
10. [DocuSign](#chapter-10-docusign)
11. [BOQ & Contracts](#chapter-11-boq--contracts)
12. [Engagements (Quotes)](#chapter-12-engagements-(quotes))
13. [Vendor Intel](#chapter-13-vendor-intel)
14. [Portal Branding](#chapter-14-portal-branding)
15. [Masters & Permissions](#chapter-15-masters--permissions)
16. [Governance](#chapter-16-governance)
17. [Reports & Snapshots](#chapter-17-reports--snapshots)
18. [Audit & Notifications](#chapter-18-audit--notifications)
19. [Change log — v3.2](#chapter-19-change-log-—-v3.2)

## Chapter 1 · Introduction & Roles

PMC Managers v2 is a global tender-management platform. This handbook walks a new trainee through every screen in the admin console + vendor/committee portals, in the order they show up in a real procurement engagement.

### Roles at a glance
* **Admin** — master account (adminsupport@pmcmanagers.com). Full read/write.
* **Reviewer / Sub-Admin** — creates drafts, cannot publish.
* **Escrow Officer** — signs escrow releases, no other write access.
* **Certifier / Legal / Accounting** — role-scoped decision steps.
* **Committee Chair / Member** — votes on shortlisted bids.
* **Vendor** — public registrant, submits bids + BOQ + KYC.
* **Support / Auditor** — read-only, no state changes.

### Where to log in
Every role uses the same portal URL. The login card auto-detects the role
from the email domain. If you see a 403 on any screen it means your role
does not have the required permission — go to Masters → Permissions to check.

## Chapter 2 · Notices

The Notices module is the entry point for every tender / RFP / RFQ. A notice becomes public only after publish.

### Create a notice
1. Admin → **Notices** → *+ New notice*.
2. Fill Title (≥3 chars), Description (≥10 chars), Category, Country, Deadline.
3. Choose Document type (tender / RFP / RFQ) and pick a matching Tender Template.
4. Upload the primary document (PDF/DOCX) + attachments.
5. Master Admin ticks *Publish immediately*; reviewers save as draft.
6. Click **Create notice** — a `PMC-NOT-YYYY-####` reference is issued.

### Filter & search
The panel now has a search bar (title / ref) + Status dropdown (any / published / draft / expired) + a *Template-linked only* toggle.
Use *Clear* to reset filters.

### Template-linked notices
Notices with a linked template gain a **📐 template linked** badge and expose the public 'Download PDF (watermarked)' and '.zip bundle' buttons on the bidder page.

## Chapter 3 · Corrigenda

Corrigenda are formal amendments to published tenders. Every corrigendum has an auto-number, a reason field, and re-publishes the parent notice deadline.

### Publish a corrigendum
1. Admin → **Corrigenda** → *+ New*.
2. Pick the parent notice → describe the amendment (≥8 chars).
3. Optionally update the new deadline.
4. Save — banner appears on the public notice page.

### Withdraw
Requires a reason ≥8 chars. Backend returns HTTP 400 with a clear message otherwise. Withdrawal is capped at 3 per notice.

## Chapter 4 · Tender Builder

Compose a full 30-page tender using orderable sections + annexures + forms. Master templates ship for GFR 2017 QCBS 70/30. Every save creates a rolling snapshot (max 20) so you can revert.

### Clone a master into a draft
1. Left column → pick a Kind (Tender / RFP / RFQ).
2. Click a master row → **Clone**. A `Draft YYYY-MM-DD` copy appears.
3. Fill the Header (Basic Details, Cover, Fee & EMD, Critical Dates, Authority).
4. Fill each section body using the rich editor (bold / italic / lists / block-quote).

### Bulk attach section files
Drag many files onto the bulk uploader — filenames like `annex-VIII_bank.pdf` auto-match to Annexure VIII (longer codes win, so it never mis-attaches to Annexure V).

### AI draft menu
Each section has a ✨ menu — tone (formal / plain / strict) × length (short / medium / long). Sections with existing content show a red/green word diff before overwriting.

### Version history
⟲ *History* opens the drawer. Restore is itself snapshotted (undoable).

### Export
Print (browser dialog) OR Download PDF (WeasyPrint, EN / RU / KK label pack, DRAFT watermark until published).

## Chapter 5 · Bidding Ops

Every submitted bid flows through the multi-role pipeline: **EMD → Escrow → Admin flag → Certifier → Legal → Accounting → Committee**.

### Statuses
Statuses read left to right. A stuck bid usually means the previous role hasn't cleared it — check the audit log.

### Assign certifier
Once a bid is *admin_flagged*, click **Assign** — pick a certifier from the drop-down, set date + location, save. An inspection record is created and the certifier is notified.

### Form a committee
Only one open committee per tender. Chair must be one of the picked members. Quorum ≤ #members. External invitees receive an accept-link email.

### Reject / Withdraw
Both require a note. Audit log preserves the reason.

## Chapter 6 · Reverse Auctions

Live reverse-auction room with masked identities, auto-bid, price floor, and anti-snipe extension.

### Create a draft auction
Admin → **Live Auctions** → *+ New auction*. Draft auctions do NOT expose the public bidder link — the panel shows an explanatory hint instead.

### Go live
Set the min-decrement + hard price floor + anti-snipe seconds. Publish. The public `/vendor/auction/:aid` room polls every 2s and masks bidders as Bidder A/B/C…

### Participant validation
Backend blocks duplicate vendor entries + non-registered emails with HTTP 400.

## Chapter 7 · Escrow (EMD)

Joint escrow accounts operated by one PMC officer + one escrow-institution officer. Dual signature required for every release.

### Create an account
Admin → **Escrow** → *+ Account*. Enter the two named officers (must be different logins). Status starts as *pending*.

### Transactions & signing
Every EMD instrument is a transaction. Each side clicks **Sign**. Release only fires after BOTH sign — otherwise HTTP 409.

### Aging report
Stakeholder Reports → Escrow surfaces aging days per pending transaction + an *SLA breach* flag once >7 days.

## Chapter 8 · Evaluation

Committee scoring with per-criterion weights. Rubric is set per notice.

### Score a bid
Committee member → **Evaluation** → pick bid. Enter score per criterion; the panel shows the weighted total live.

### Conflict of interest
COI declaration is required. `evaluations.submit_score` returns 400 if COI is missing.

## Chapter 9 · Awards & POs

Awarding a bid drafts three PDFs: Purchase Order (`PMC-PO-YYYY-#####`), SLA, Contract. All three ship with a diagonal DRAFT watermark until countersigned.

### Regenerate
**Regenerate** now shows a confirmation dialog + timestamped toast. Every regeneration is pushed into `bid.award_regenerations[]`.

### Download
Admin, vendor, and any authorised staff can download the three PDFs from **Awards** → *bid row* → *⬇ PDF*.

## Chapter 10 · DocuSign

JWT Grant integration to sandbox / prod DocuSign. Ships envelopes from any Award PDF or Bid acknowledgement.

### Consent flow
First run shows a *Grant DocuSign consent* button. Click, sign the DocuSign page, come back.

### Envelope delivery modes
*Embedded* → in-app iframe with a one-time signing URL. *Email* → DocuSign emails the signer a hosted signing link.

### Authoritative envelope
The Envelope Log now flags the authoritative envelope per (bid, sub_kind): status *completed* wins, break ties by most recent created_at.

## Chapter 11 · BOQ & Contracts

Bill of Quantities templates + Contract-award workflow.

### BOQ template
Import an Excel with columns `Sl.No | Description | Unit | Quantity | Unit Rate | Remarks`. Vendors quote against the template.

### Contract
Only awarded bids can spawn a contract. Contract ref is auto `PMC-CON-YYYY-####`.

### Export & versions
*Contracts-Export* endpoints: filter by status/vendor/query, download `contracts-export.csv`, view per-contract version timeline (creation + milestone completions + variation orders).

## Chapter 12 · Engagements (Quotes)

Public / Vendor purchase pages fire a *Request quote* — every request lands here as an engagement.

### State machine
`quote_requested → quoted → invoiced → paid`. Alternate branch: `cancelled` (now requires a reason ≥5 chars).

### Aging summary
GET `/api/v1/engagements/aging/summary` returns receivable age buckets (0-7 / 8-30 / 31-60 / 61+ days) for dashboards.

### Invoice
Set quoted amount + currency → **Invoice**. Stripe checkout session is created; buyer gets a pay-link.

## Chapter 13 · Vendor Intel

Bulk vendor risk register with WL/BL flags + anonymised entries.

### Legend
**BL** = Blacklisted · **WL** = Watch-list · **—** = anonymised entry (imported without an identity).

## Chapter 14 · Portal Branding

Tenant-level branding: logo + primary & accent colours + favicon + rolling logo history.

### Change colours
PATCH `/api/v1/branding/{tenant_id}/theme` with `primary_color` + `accent_color` (both `#RRGGBB`) + `favicon_data_url`. Frontend live-previews the change before you save.

### Logo history
The tenant document keeps the last 10 logos in `logo_history[]`. GET `/api/v1/branding/{tenant_id}/logo-history` to fetch.

## Chapter 15 · Masters & Permissions

Permission Matrix + hierarchy Levels. This is the single source of truth for what each role can do.

### Grant a permission
Masters → **Permissions** → edit row → tick the checkbox → save. Every mutation is audited.

### Reviewer drafts (Bug #5)
reviewer.create=True on notices — sub-admins can save drafts without a 403.

## Chapter 16 · Governance

The governance folder holds the guardrails audited by the QA team.

### G1 — Escrow dual-sig
Same login cannot sign both sides — HTTP 400 'must be different people'.

### G2 — COI cross-check
`evaluations.submit_score` blocks with 400 if no COI declaration.

### G3 — Access control unification (Wave G2)
Permissions Matrix + hierarchy Level consolidation is planned.

### G4 — Stakeholder Reports (rebuilt in v3.2)
New **Stakeholder Reports** tab: Tenders / Awards / Escrow / SLA — each with CSV download. Escrow surfaces aging + SLA breaches; SLA tab shows milestone hit-rate.

### G5 — Draft auction public link
Hidden when status='draft'.

## Chapter 17 · Reports & Snapshots

*Reports* tab exposes the Asked-vs-Delivered stakeholder brief in .xlsx / .docx / .pdf plus the platform flowchart in .svg / .pdf. *Stakeholder Reports* tab exposes the four operational reports above.

### Snapshot to disk
Admins can hit *Snapshot to disk* — writes 9 files into `/app/docs/reports/` so they land in the next git push.

## Chapter 18 · Audit & Notifications

Every substantive action produces an `audit_log` entry. `NotificationBell` in the top-right polls for new notifications every 30s.

### Global ErrorBoundary
React `<ErrorBoundary/>` wraps every route. If a panel blows up, the user gets a recoverable panel with a *Reload* button instead of a white screen.

## Chapter 19 · Change log — v3.2

What actually changed in this release.

### Backend
1. New router `stakeholder_reports` (G4 rebuild).
2. New router `dashboard_drill` (AI Anomaly + Pipeline drill-through).
3. New router `branding_theme` (primary/accent colour + favicon + logo history).
4. New router `envelope_authoritative` (DocuSign log flags most-recent completed envelope).
5. New router `contracts_export` (filter + CSV + version timeline).
6. `engagements.cancel` now requires reason ≥5 chars; `/aging/summary` endpoint added.

### Frontend
1. New `StakeholderReportsPanel` (G4).
2. Notices panel: search + status filter + template-linked-only toggle.
3. Wave A–D 17 bugs, Bug #5 sub-admin drafts, Bucket A UX wins already shipped in v14/v16.

### Docs
1. Observations Response **v4** — every session fix marked FIXED.
2. Trainee Handbook **v3.2** — every module chapter.

---
### Guardrails
- AI is advisory.
- Every mutation audited.
- Escrow dual-signature.
- Drafts hide public links.
- ErrorBoundary wraps every route.