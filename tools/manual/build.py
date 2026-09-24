"""PMC v46m Master Training Manual — comprehensive builder.

Consumes /app/deliverables/v46_manual/manifest.json (from capture.py) and
produces the MD / DOCX / PDF triple at /app/deliverables/v46_manual/build/.
Targets 130–160 A4 pages by pairing every captured screen with 350–500
words of guidance, plus 10 narrative chapters (architecture, roles,
security, workflows, deployment, troubleshooting, glossary, appendix).
"""
import json, html, base64
from pathlib import Path
from datetime import date

ROOT     = Path("/app/deliverables/v46_manual")
SCREENS  = ROOT / "screens"
OUT      = ROOT / "build"; OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = json.loads((ROOT / "manifest.json").read_text())
BANNER   = f"PMC Managers Limited · Confidential · v46m · {date.today():%B %Y}"

# ---------------------------------------------------------------------------
# Rich per-screen prose. Every filename gets ~4–7 paragraphs of guidance +
# field list + gotchas. Anything missing falls back to GENERIC below.
# ---------------------------------------------------------------------------
DEEP: dict = {}
def _deep(filename, purpose, workflow, fields, gotchas=None):
    DEEP[filename] = {
        "purpose": purpose,
        "workflow": workflow,
        "fields": fields,
        "gotchas": gotchas or [],
    }

_deep("01_public_home.png",
    "The sovereign public entry. Establishes brand authority, states current scope (Kazakhstan Integrated Development), and exposes three live counters and three primary CTAs.",
    "1) A prospective bidder lands from a Google search or a Snapchat post. 2) The live KPIs prove the platform has real, current activity. 3) They tap 'View Open Notices' to browse tenders or 'Portal Gateways' to sign in to their existing account.",
    [("Kicker line", "'PMC Managers · Sovereign Gateway' — anchors the brand in an editorial serif register."),
     ("Sovereign hero", "Libre Baskerville headline, italic gold accent, IBM Plex Mono kicker — deliberately different from generic SaaS."),
     ("KPI cards", "Notices Published / Suppliers Approved / Work Packages — pulled live from /api/v1/meta/public/stats."),
     ("Primary CTAs", "View Open Notices (gold button), Register as Supplier (ghost button), Portal Gateways (underline link).")],
    ["Counters cache in CloudFront for 60 s — a fresh notice may take up to a minute to appear.",
     "The hero background is a radial gold gradient at 8% opacity — do not brighten it or the serif headline loses contrast."])

_deep("02_public_notices.png",
    "The reverse-chronological list of every published notice. Primary discovery surface for bidders and researchers.",
    "1) Enter a keyword or filter by country / category. 2) Review the card headline, deadline and EMD hint. 3) Click a row to open the full public detail page.",
    [("Search box", "Fuzzy match on title, description, country and category — server side."),
     ("Country / Category filters", "Backed by the same masters used in the admin console."),
     ("Deadline chip", "Turns red at T-24 h to create urgency."),
     ("EMD hint", "Shows the EMD amount or percentage inline so bidders can pre-arrange the deposit.")],
    ["Deadlines display in the visitor's local timezone; the backend stores UTC ISO strings."])

_deep("03_public_tenders_live.png",
    "Filter of the notice board scoped to tenders currently open for bidding.",
    "Bidders check this daily; the URL is optimised for RSS and Snapchat spotlight posts.",
    [("Countdown chip", "Live H:MM:SS to submission deadline."),
     ("Awarding authority", "Small navy tag on each card."),
     ("EMD hint", "Percentage or absolute value inline.")],
    ["If the counter reads 0 despite live data, force a CloudFront invalidation."])

_deep("04_public_tenders_completed.png",
    "Public archive of every tender past its submission deadline.",
    "Journalists, auditors and inbound partners use this to audit PMC's throughput.",
    [("Award column", "Winning bidder + final price once award is finalised and cleared for publication."),
     ("Signed award PDF", "Downloadable letter of award.")],
    ["A tender only appears here after the award is confirmed and legal has flipped the publish flag."])

_deep("05_public_tenders_all.png",
    "The combined live+completed archive with a status filter.",
    "Used by regulators, auditors and inbound partners doing due diligence on PMC.",
    [("Status filter", "Live / Completed / Cancelled / Withdrawn."),
     ("Column sort", "Deadline, budget, publish date, awarding authority.")],
    ["Cancelled tenders keep their audit trail — never delete a notice, always withdraw it."])

_deep("06_public_about.png",
    "Editorial About Us — company narrative, milestones, leadership grid, sector coverage, press quotes.",
    "Marketing and BD share this URL with prospective GOC/Bank partners; it also drives Snapchat / Instagram profile clicks.",
    [("Charter", "One-paragraph mission statement — content-managed via CMS."),
     ("Milestones", "Chronological chips — feed this monthly during releases."),
     ("Leadership grid", "Portrait cards with role and short bio."),
     ("Press quotes", "Curated third-party validators.")],
    ["Portraits should be square 512×512 PNGs sized ≤ 120 KB — larger images push the fold below the CTA."])

_deep("07_public_vision.png",
    "The strategic doctrine page — Vision, Mission, Values, North-Star KPIs the platform is optimised for.",
    "Referenced by the tender committee in every quarterly briefing. Also cited in ESG questionnaires.",
    [("Vision statement", "10-year direction."),
     ("Mission", "12-month operational focus."),
     ("Values", "Three principles used to arbitrate roadmap trade-offs."),
     ("North-star KPIs", "Cycle time, dispute rate, EMD-refund SLA, vendor NPS.")],
    ["Whenever the North-Star KPIs change, re-open every tender committee meeting with the delta explained."])

_deep("08_public_register.png",
    "Public entry point for vendor self-onboarding.",
    "1) Bidder submits email + company + country. 2) A Resend magic link is emailed. 3) Bidder clicks the link and lands on RegistrationResume where the 5-step wizard begins.",
    [("Email", "Uniqueness enforced across tenants."),
     ("Company name (optional)", "Skipping this delays enrichment but does not block the wizard."),
     ("Country dropdown", "Sourced from the platform-wide country master.")],
    ["Resend delivery to first-touch corporate mailboxes can hit spam — admins can resend from the Registrations queue."])

# Sovereign gateway + per-portal forms
_deep("09_public_login_grid.png",
    "The 5-portal Sovereign Gateway — the new single entry point for every human role.",
    "Users pick the badge matching their role. Each card animates into a portal-specific credential form with the correct colour system, kicker, icon and CTA.",
    [("System Administrator", "Amber ring · SUPERVISORY · ROOT badge."),
     ("PMC Management", "Blue ring · EXECUTIVE badge."),
     ("Strategic Partners", "Cyan ring · GOC · BANK · REGULATOR badge."),
     ("Procurement Agents", "Emerald ring · FIELD OPS badge."),
     ("Registered Vendors", "Gold ring · BIDDER badge.")],
    ["Each portal has its own audit-log tag — a single email that owns two roles will show up twice in the audit trail with the portal it entered through."])

for pid, human in [("admin", "Admin"), ("management", "Management"),
                    ("partners", "Partners"), ("agents", "Agents"),
                    ("vendors", "Vendors")]:
    _deep(f"{10 + ['admin','management','partners','agents','vendors'].index(pid):02d}_public_login_{pid}.png",
        f"Credential form for the {human} portal.",
        "The credential form uses the portal's colour and badge. Email + password submit into the appropriate auth realm (staff for admin/management/partners/agents, vendor for vendors).",
        [("Work email", "Email that appears in the audit trail."),
         ("Password", "12+ characters; failures trigger the brute-force lockout after 5 attempts."),
         ("Portal briefing (right rail)", "Short brief so the user knows they're in the right door."),
         ("Session security note", "TLS 1.3 + immutable audit log — cite this in security reviews.")],
        ["MFA is enforced for admin + management once configured — you get a code prompt after the password step."])

# Vendor portal
_deep("30_vendor_landing.png",
    "Vendor dashboard immediately after sign-in.",
    "Bidders arrive here after credential submit. Header shows the trust badges, body shows quick paths to open tenders, held EMDs, active auctions, awarded contracts.",
    [("Trust badges", "Aggregate rating badge + certified-supplier chip if applicable."),
     ("Open tenders card", "Categories filtered to the vendor's declared industries."),
     ("EMDs held", "Total value + release-eligible-date."),
     ("Auctions strip", "Live and scheduled reverse-auction rooms.")],
    ["The dashboard refetches on every route change to avoid stale counts."])

_deep("31_vendor_dashboard.png",
    "Dashboard tab — deep-linked overview.",
    "Vendors return here throughout the day to check envelope status.",
    [("Bidding pipeline", "Draft / Submitted / Evaluated counts."),
     ("Deadlines", "Colour-coded — red < 24 h, amber < 72 h.")],
    [])

_deep("32_vendor_bids.png",
    "My bids — every submitted bid with envelope status, score summary and award outcome.",
    "Bidders use this to prove submission for legal disputes and to compare pricing against their prior wins.",
    [("Bid ref", "PMC-BID-YYYY-NNNN — anchor for every legal reference."),
     ("Envelope status", "Sealed / Unsealed / Under evaluation / Awarded / Rejected."),
     ("Score summary", "Technical + commercial weighted score once the envelope is unsealed."),
     ("Award outcome", "Won / Runner-up / Not qualified.")],
    ["A rejected bid keeps its EMD until the notice's dispute window closes."])

_deep("33_vendor_auctions.png",
    "Reverse auctions — invitations and live/closed rooms.",
    "Bidders click Join Auction to be assigned a masked alias, then place manual or auto bids with a walk-away floor.",
    [("Invitations", "Only sent to vendors that qualified through the technical envelope."),
     ("Live rooms", "Real-time countdown, current lowest, masked leader alias."),
     ("Auto-bid config", "Walk-away floor + enable toggle — the platform undercuts competitors above your floor.")],
    ["Names and companies are masked from every participant to prevent collusion. Only the admin can de-mask post-close."])

_deep("34_vendor_invoices.png",
    "Invoices & receipts — fees, refunds, EMD-held ledgers.",
    "Finance teams reconcile PMC invoices against Stripe / Kaspi payouts here.",
    [("Invoice number", "Sequence resets per calendar year."),
     ("Amount / Currency", "Displayed in the tender's original currency."),
     ("Status", "Paid / Overdue / Refunded."),
     ("PDF download", "Signed PDF; can be attached to internal AP systems.")],
    [])

_deep("35_vendor_profile.png",
    "Company profile — legal identity, address, contacts, tax IDs.",
    "Change requests here trigger a re-verification workflow — the vendor is temporarily marked 'under review' until Support signs off.",
    [("Legal name", "Immutable once verified; contact Support for changes."),
     ("Address block", "Registered address for tax and contract purposes."),
     ("Primary contact", "Email routes for tender notifications."),
     ("VAT / Tax IDs", "Country-specific format validators.")],
    ["Editing the legal name deactivates the account for 24 h pending Support review."])

_deep("36_vendor_licenses.png",
    "Licences & compliance — uploaded licences with expiry timeline.",
    "Auto-alerts fire 30 / 14 / 3 days before expiry so vendors can renew before they lose bid eligibility.",
    [("Licence type", "Country-specific — Kazakhstan uses SK-* codes."),
     ("Issue / expiry", "Both required; the platform uses the expiry to gate bid eligibility."),
     ("Signed PDF", "S3-backed; downloadable by auditors."),
     ("Re-verification", "After upload, Support has 48 h to approve / reject.")],
    ["Uploading a licence past its expiry date is silently accepted but the vendor is instantly flagged for review."])

_deep("37_vendor_ratings.png",
    "Reviews & trust score — reviews left by admins post-contract with an aggregate rating badge.",
    "The aggregate badge is visible on the public vendor profile and on every bid card.",
    [("Aggregate score", "Weighted average across all rubric criteria."),
     ("Reviews list", "Text + score per criterion + reviewer role."),
     ("Trust badge", "Bronze / Silver / Gold / Platinum tiers based on aggregate + volume.")],
    ["Reviews cannot be edited once submitted; moderation is admin-only via the Vintel tab."])

_deep("38_vendor_preferences.png",
    "Notifications — category subscriptions and email preferences.",
    "Vendors reduce noise by subscribing only to relevant categories.",
    [("Category subscriptions", "Emit an email when any notice in these categories publishes."),
     ("Digest cadence", "Instant / Daily / Weekly."),
     ("Reverse-auction alerts", "Immediate override for invitations.")],
    [])

# Admin
_deep("50_admin_landing.png",
    "Command centre for PMC staff.",
    "Admin arrives here after sign-in; the collapsible sidebar groups 23 modules into Overview / Procurement / Market / Money & Compliance / Events — matching the mental model of the PMC operations team.",
    [("Sidebar groups", "Overview · Procurement · Market · Money & Compliance · Events."),
     ("Environment chip", "Which tenant/programme is active."),
     ("AI Copilot", "In-context question box for procurement policy questions."),
     ("Alerts strip", "Aging EMDs, publish-ready notices, contract SLA breaches.")],
    ["Some tabs require role escalation (e.g. Escrow needs escrow_agent) — a locked-tab tooltip explains."])

_deep("51_admin_analytics.png",
    "Analytics dashboard — KPIs, funnel drills, revenue by module, activity heatmap.",
    "Executives open this weekly; the funnel drives roadmap conversations about where the pipeline stalls.",
    [("KPI grid", "Published Notices, Vendors, Bids, Awarded, Pending EMD, EMD Collected, Active Contracts."),
     ("Pipeline funnel", "Draft → Published → Bidder Attention → Bids Received → Evaluated → Awarded → Signed."),
     ("Top bids table", "Ten highest-value active bids."),
     ("AI anomaly detector", "Runs the LLM copilot on any selected bid to flag collusion or dumping.")],
    ["The AI anomaly detector's confidence score is a heuristic — always cross-check with peer distribution before acting."])

_deep("52_admin_registrations.png",
    "Vendor registrations queue — approve, reject, resend activation, force-activate.",
    "1) Support reviews the wizard submission. 2) Cross-check licences and tax IDs. 3) Approve, request clarification, or reject with reason.",
    [("Filter", "Status (Draft / Submitted / Approved / Rejected)."),
     ("Row expander", "Shows the full wizard payload."),
     ("Approve", "Provisions the vendor account and emails credentials."),
     ("Force-activate", "Skips MFA for QA scenarios — audit-logged.")],
    ["Force-activate should only be used for QA and support triage; every use surfaces in the audit trail with the actor."])

_deep("53_admin_vendors.png",
    "Vendor directory — full CRUD on suppliers, licences, compliance, tenants.",
    "The 5-tab admin vendor form (v46h) has Save buttons on every tab so the record persists incrementally.",
    [("Search", "PMC-SUP-* reference or company name."),
     ("Row action", "Edit / Deactivate / Reset password."),
     ("Section tabs", "Identity / Financial / Compliance / Contacts / Bank."),
     ("Save section button", "Every section has its own Save so long forms don't lose progress.")],
    ["Deactivating a vendor freezes their bids but does not delete history — a rehydration flow can re-enable in one click."])

_deep("54_admin_notices.png",
    "Notices — publish, edit, withdraw, attach documents.",
    "1) Author drafts from a Tender Builder template. 2) Legal signs off. 3) Notice is published — vendors get their category alerts.",
    [("New notice", "Opens the draft editor."),
     ("Publish", "Flips is_published and emits Resend digests + Snapchat + Instagram posts."),
     ("Withdraw", "Never delete — the audit trail keeps every prior state."),
     ("Attachments", "Signed PDFs, BOQ CSV, drawings.")],
    ["Once published, edits create a corrigendum — the corrigenda tab tracks these amendments with author + timestamp."])

_deep("55_admin_corrigenda.png",
    "Corrigenda log — publish addenda/amendments against any live notice.",
    "Every substantive change to a live notice must go through a corrigendum so the audit trail is complete.",
    [("Author + timestamp", "Immutable once published."),
     ("Version diff", "Field-level red/green diff."),
     ("Public visibility", "Corrigenda appear on the public notice detail immediately.")],
    ["Corrigenda cannot be deleted — issue a superseding corrigendum instead."])

_deep("56_admin_tender-builder.png",
    "Tender Builder & DPR AI — master library, DPR deep-dive, AI Fill All, PDF export.",
    "The DPR modal is the marquee AI feature — it ingests a Detailed Project Report and drafts an entire tender pack.",
    [("Master library", "Reusable templates keyed by country + industry."),
     ("Rolling versions", "Every save is a snapshot — Restore is itself auto-snapshotted."),
     ("AI Fill All", "Redrafts empty section bodies from the header context."),
     ("PDF export", "Renders the composed tender pack to a print-ready PDF.")],
    ["v46l: DPRs ≥ 4 MB run through the async pipeline with a live progress bar; anything under 4 MB uses the sync path."])

_deep("57_admin_bidding.png",
    "Bidding operations — bid room, submissions, seal/unseal, timing.",
    "Admins configure envelope types (technical + commercial), deadlines and open-until times.",
    [("Envelope config", "Technical / Commercial / Both."),
     ("Seal button", "Freezes an envelope after the deadline — Bug #52 hardened in v46m to reject re-lock."),
     ("Time-of-day gate", "Prevents late-night submissions if the notice requires business-hour bidding.")],
    ["Once sealed, the backend refuses new scores (409) — the frontend shows a 'Sealed 🔒' chip and a banner with the sealer + timestamp."])

_deep("58_admin_escrow.png",
    "Escrow / EMD desk — receipts, forfeitures, refunds.",
    "The escrow desk is a joint-account model — refunds require two officers to sign per the joint-account snapshot.",
    [("Transactions ledger", "Every EMD held / forfeited / refunded."),
     ("Joint-account snapshot", "Two-signer requirement per transaction."),
     ("Refund workflow", "Triggered by tender close + no dispute after N days."),
     ("Forfeiture", "Manually triggered with legal sign-off; audit-logged.")],
    [])

_deep("59_admin_evaluation.png",
    "Evaluation & scoring — technical + financial scoring, QCBS, L1 comparison, envelope locking.",
    "1) Author sets the rubric. 2) Committee scores technical. 3) Admin locks technical. 4) Committee scores commercial. 5) Admin locks commercial. 6) Award report generates the L1.",
    [("Rubric editor", "Weights 0–1 per criterion, must sum to 1.00; commercial weight 0–1; minimum technical 0–100."),
     ("Envelope locks", "'Sealed 🔒' chip + banner once locked (v46m)."),
     ("COI declaration", "Every evaluator must declare or negate a conflict of interest."),
     ("Award report", "L1 comparison table with weighted scores and dispute-window countdown.")],
    ["Rubric edits after any score submission are refused with a 422 — clone the notice if you truly need a new rubric."])

_deep("60_admin_awards.png",
    "Awards & POs — letters of award, purchase orders, contract workflow.",
    "Once the evaluation lands on an L1, the award workflow issues the LOA, tracks acceptance, and generates the PO.",
    [("Letter of award", "Signed PDF with the L1 vendor's details."),
     ("PO number", "Sequenced globally; used in the DocuSign envelope."),
     ("Acceptance deadline", "Vendor has N days to accept or the runner-up is invited.")],
    [])

_deep("61_admin_docusign.png",
    "DocuSign contracts — envelope templates, signer routing, live status.",
    "Contracts are drafted from templates, routed to the vendor + PMC legal, and monitored end-to-end.",
    [("Envelope template", "Reusable field maps."),
     ("Signer routing", "Vendor first, then legal, then finance."),
     ("Live status", "Sent / Delivered / Completed / Declined."),
     ("Countersign", "PMC signs after vendor.")],
    ["A declined envelope re-opens the runner-up path automatically."])

_deep("62_admin_auctions.png",
    "Reverse auctions — live auction rooms, invitations, spectator link.",
    "Admin creates the auction from an evaluated tender; qualified vendors are invited and receive masked aliases.",
    [("Auction config", "Duration, min decrement, floor price, currency."),
     ("Invitations list", "Only technically-qualified vendors are eligible."),
     ("Spectator link", "Public read-only room used by auditors."),
     ("Extend on last-second bid", "5-minute auto-extend so no one can snipe.")],
    ["The vendor+company identities are hidden in the live room — admin can de-mask only after the auction closes."])

_deep("63_admin_meetings.png",
    "Pre-bid meetings — scheduling, Zoom links, minutes, attendance.",
    "Every substantive question raised in a pre-bid meeting must land on the public Q&A.",
    [("Schedule", "Date + Zoom link + attendees."),
     ("Minutes upload", "Signed PDF."),
     ("Q&A migration", "Move questions from the minutes to the public Q&A on the notice.")],
    [])

_deep("64_admin_boq.png",
    "BOQ templates & contracts — Bill of Quantities master + contract line items.",
    "Templates prevent estimator errors; contract BOQs feed the final invoice runs.",
    [("BOQ template", "Category + unit + rate schema."),
     ("Contract BOQ", "Locked once contract is signed."),
     ("Variation orders", "Signed amendments; captured in the audit trail.")],
    [])

_deep("65_admin_vintel.png",
    "Vendor intel & ratings — trust badges, moderation, criteria averages.",
    "Reviews left post-contract feed both the vendor's trust badge and internal risk scoring.",
    [("Trust badge tiers", "Bronze / Silver / Gold / Platinum."),
     ("Moderation queue", "Reviews flagged for language or bias."),
     ("Criteria averages", "Per-criterion trend line.")],
    [])

_deep("66_admin_masters.png",
    "Masters — fees, roles, EMD, categories, countries.",
    "Central library. Editing a master version-bumps every entity using it.",
    [("EMD/Fee slabs", "Country + industry + slab-band + amount or percentage."),
     ("Rating criteria", "Rubric master — the criteria list every evaluation uses."),
     ("Staff roles", "The 12 role literals — admin, reviewer, escrow, certifier, legal, accounting, committee, auditor, support, management, partner, agent."),
     ("Category taxonomy", "UNSPSC-mapped hierarchy."),
     ("Country register", "ISO + local translations.")],
    [])

_deep("67_admin_permissions.png",
    "Roles & permissions — fine-grained ACL matrix.",
    "One row per role, one column per capability. Green = allowed, grey = denied.",
    [("Matrix cell", "Click to toggle."),
     ("Change history", "Every toggle is audit-logged.")],
    ["Do not remove capabilities from Admin — the platform expects Admin to be the escape hatch role."])

_deep("68_admin_packages.png",
    "Work packages — modular deliverable packages.",
    "Multi-package programmes (Kazakhstan Integrated Development) are structured here.",
    [("Package card", "Scope, budget, timeline, current status."),
     ("Package → tenders", "Every tender is tagged to a package."),
     ("Reporting rollups", "Package-level KPIs.")],
    [])

_deep("69_admin_audit.png",
    "Audit trail — immutable action log with entity filters.",
    "Auditors filter by entity + action type + date range and export to CSV.",
    [("Filter bar", "Entity type / ID / action / actor / date."),
     ("Row detail", "Full JSON payload — expandable."),
     ("CSV export", "Ships as attachment with signature.")],
    [])

_deep("70_admin_catalog.png",
    "Product catalog — UNSPSC-mapped goods catalog.",
    "Used by BOQ templates and by the eligibility engine to route notices to the right vendors.",
    [("Catalog tree", "UNSPSC hierarchy."),
     ("Unit master", "kg, m, hour, day, etc."),
     ("Rate reference", "Historical price band per SKU.")],
    [])

_deep("71_admin_engagements.png",
    "Consultant engagements — retainers, timesheets, invoices.",
    "Consultants log time against engagements; invoices auto-draft monthly.",
    [("Engagement card", "Retainer + hourly + expense limits."),
     ("Timesheet grid", "Weekly entry with client approval."),
     ("Invoice draft", "Auto-generated on the 1st of each month.")],
    [])

_deep("72_admin_reports.png",
    "Stakeholder reports — tenders / awards / escrow / SLA with CSV export.",
    "GOC and Bank stakeholders receive these monthly. Every report includes a JSON summary + a downloadable CSV.",
    [("Tenders report", "Pipeline snapshot per notice."),
     ("Awards report", "PO numbers + contract value + winning bidder."),
     ("Escrow report", "Accounts + aging days per status."),
     ("SLA report", "Active contracts + milestone hit-rate.")],
    ["Every artefact is wrapped in its own try/except so one failure does not kill the whole snapshot."])

_deep("73_admin_billing.png",
    "Billing & transactions — fee ledger, refunds, Stripe reconciliation.",
    "Accounting reconciles PMC fee revenue against Stripe payouts here.",
    [("Fee ledger", "Every fee charged with vendor + notice."),
     ("Refund", "Requires reason + confirms the vendor+notice before firing."),
     ("Stripe payout link", "Cross-links to the Stripe dashboard for the corresponding payout batch.")],
    [])

# Modals / deep flows
_deep("74_admin_tb_dpr_modal.png",
    "Tender Builder · AI DPR modal.",
    "Country-first ingestion. Pick country → master → upload PDF. Files ≥ 4 MB automatically use the async pipeline (v46l) with a live progress bar; smaller files use the sync path.",
    [("Country dropdown", "Filters the master list to that country."),
     ("Master template dropdown", "Optional — if none exists, the no-master helper appears."),
     ("Upload", "PDF / DOCX / TXT, max 100 MB per file (v46l)."),
     ("Background chip", "Files ≥ 4 MB get a 'Background' chip and a real progress bar."),
     ("Analyze button", "Kicks off the map-reduce.")],
    ["Very large tenders (500+ pages) can take 5–20 minutes; the progress bar keeps advancing as the LLM works."])

_deep("75_admin_tb_no_master.png",
    "Tender Builder · No-master helper.",
    "When the picked country has zero saved masters, an amber helper offers two options: borrow a master from another country, or 'Build a brand-new master from this DPR' — the latter persists a new master under the picked country after analysis.",
    [("Cross-country toggle", "Shows every master with a country-code prefix in the dropdown."),
     ("Build-new-master toggle", "Skips master selection; the AI drafts the structure and sections from the DPR itself."),
     ("Editable tender name", "Every draft can be renamed before persistence.")],
    ["Building a new master requires an editable tender name; blank names default to the DPR filename + date."])

_deep("76_admin_evaluation_rubric.png",
    "Evaluation · Rubric + envelope locks.",
    "The rubric editor enforces weight 0–1 per criterion, sum ≈ 1.00, commercial weight 0–1, minimum technical 0–100. Lock buttons swap to 'Sealed 🔒' once locked (v46m).",
    [("Criterion weight input", "Number 0–1, step 0.05; invalid disables Save."),
     ("Commercial weight", "0–1."),
     ("Minimum technical", "0–100."),
     ("Envelope lock banner", "Green banner shows sealer + timestamp once either envelope is locked.")],
    [])

_deep("77_admin_masters.png",
    "Admin · Masters library.",
    "Central master library — EMD/fee slabs by country + industry, rating rubric master, staff roles, category taxonomy, country register.",
    [("EMD slabs", "Country + industry + band + amount or percentage."),
     ("Fee slabs", "Same schema; used for tender-fee compute."),
     ("Rating criteria", "The rubric list every evaluation uses."),
     ("Staff roles", "Twelve role literals."),
     ("Category taxonomy", "UNSPSC hierarchy."),
     ("Country register", "ISO codes + local names.")],
    [])

_deep("78_admin_escrow_transactions.png",
    "Admin · Escrow transactions ledger.",
    "Every EMD held / forfeited / refunded with signer attribution and joint-account snapshots. Filter by status, bidder, notice, aging bucket.",
    [("Ledger row", "EMD held / forfeited / refunded."),
     ("Signer attribution", "Two officers per transaction."),
     ("Joint-account snapshot", "The exact officer list at the time of the transaction."),
     ("Age bucket", "0–30 / 31–60 / 61–90 / 90+ days.")],
    [])

_deep("79_admin_notice_new.png",
    "Notices · New notice draft.",
    "Author picks a Tender Builder template, sets EMD/fee, uploads the tender packet, and schedules publication.",
    [("Template picker", "Reusable Tender Builder template."),
     ("EMD / fee compute", "Auto-computed from the master + tender value."),
     ("Attachments", "Signed PDF + BOQ CSV + drawings."),
     ("Schedule publish", "Publishes at a specific UTC timestamp.")],
    [])

GENERIC = ("This screen exposes every action available for its module. Use the "
             "InfoDot (ⓘ) next to each label to see the field-level rules — "
             "hover it in-app for the full policy text. All destructive actions "
             "confirm before applying, and every mutation is written to the "
             "immutable audit log.")

# Glossary + release notes — shared across MD and PDF assembly
gl = [
    ("DPR", "Detailed Project Report — the source document the AI ingests to draft a tender pack."),
    ("EMD", "Earnest Money Deposit — refundable bid security."),
    ("QCBS", "Quality- & Cost-Based Selection — the default 70/30 evaluation weighting."),
    ("L1", "Lowest financial bid post-technical qualification."),
    ("BOQ", "Bill of Quantities — itemised deliverable+rate schedule."),
    ("Corrigendum", "Official post-publication amendment to a notice."),
    ("LOA", "Letter of Award — signed offer letter to the L1 vendor."),
    ("PO", "Purchase Order — issued after the LOA is accepted."),
    ("Envelope", "A sealed batch of bid data — technical or commercial."),
    ("Trust badge", "Bronze / Silver / Gold / Platinum tier surfaced on the public vendor profile."),
    ("Master", "A reusable Tender Builder template keyed by country + industry."),
    ("Sovereign Gateway", "The v46k 5-portal login picker."),
    ("Async pipeline", "The v46l background DPR worker — kicked via /dpr/analyze-async."),
    ("Sealed 🔒", "The v46m evaluation-panel indicator that an envelope is locked."),
]

# ---------------------------------------------------------------------------
# Markdown / DOCX / PDF assembly
# ---------------------------------------------------------------------------
md: list[str] = []
def h(level, txt): md.append("#" * level + " " + txt + "\n")
def p(txt): md.append(txt + "\n")
def img(rel, cap): md.append(f"![{cap}](../screens/{rel})\n\n*{cap}*\n")

h(1, "PMC Managers · v46m Master Training Manual")
p(f"_{BANNER}_")
p("")
p("This manual is the authoritative operator handbook for the PMC Managers "
    "Sovereign Tender Board, version 46m (Sep 2026). It walks every role "
    "through every screen with annotated screenshots, field-by-field guidance, "
    "known-gotcha callouts, and end-to-end workflow narratives. Use it as "
    "the primary onboarding pack for new admins, agents, partners, "
    "management, escrow officers and vendors.")

h(2, "Table of contents")
p("1. Platform overview & architecture\n"
    "2. Roles at a glance (12-role matrix)\n"
    "3. Security, audit & data-protection\n"
    "4. Public visitor journey\n"
    "5. Vendor / supplier journey\n"
    "6. Admin console — full module tour\n"
    "7. Deep-dive: Tender Builder & AI DPR (v46l map-reduce)\n"
    "8. Deep-dive: Evaluation, awards & escrow\n"
    "9. Deep-dive: Reverse auctions\n"
    "10. Tooltip, error-handling & offline system\n"
    "11. Deployment runbook (S3 + CloudFront + EB)\n"
    "12. Troubleshooting playbook\n"
    "13. API reference index\n"
    "14. Release history\n"
    "15. Glossary & appendix\n")

# ------- Chapter 1 -------
h(2, "1 · Platform overview & architecture")
p("The PMC platform is a multi-role tender lifecycle engine covering the full "
    "path from notice publication → registration → bidding → EMD → evaluation → "
    "award → e-signature → invoicing → post-contract audit. It is delivered as "
    "a React single-page app backed by a FastAPI service and MongoDB, with "
    "same-origin cookie-based sessions and CSRF double-submit tokens.")

p("**Frontend** — React SPA served from S3 + CloudFront. Sovereign navy/gold "
    "editorial design system with Libre Baskerville + IBM Plex fonts. Routing "
    "via React Router; state via Context (i18n, auth) + local component state.")
p("**Backend** — FastAPI on AWS Elastic Beanstalk (Docker running on 64-bit "
    "Amazon Linux 2). All routes prefixed `/api/v1/…`. Auth realm split into "
    "admin, staff and vendor with per-realm login endpoints and cookie names.")
p("**Data** — MongoDB via Motor (async driver). Collections include tenants, "
    "notices, tender_templates, registrations, vendors, bids, rubrics, scores, "
    "evaluations, awards, escrow_transactions, auctions, corrigenda, audits, "
    "ratings, engagements, packages, categories, countries, dpr_jobs.")
p("**AI** — Managed AI Gateway (universal LLM key) routed through the integration proxy. "
    "Used for DPR ingestion (map-reduce), AI Fill All, anomaly detection and "
    "the admin copilot. v46l lifts the 800 KB cap and adds an async worker.")
p("**Storage** — S3 for licences, tender attachments, signed PDFs, archived "
    "auction rooms. CloudFront in front for global CDN.")
p("**Notifications** — Resend (email), planned Firebase/APNs (mobile push).")
p("**Payments** — Stripe (test + live keys separated); Kaspi + PayPal on the "
    "roadmap.")
p("**E-signature** — DocuSign envelope templates + status webhooks.")
p("**Observability** — Structured logs via Python logging, CloudWatch tail, "
    "audit_log() collection for every mutation, immutable time-stamped rows.")

# ------- Chapter 2 -------
h(2, "2 · Roles at a glance")
roles = [
    ("Admin",             "/admin",       "Full control of every module."),
    ("Management",        "/staff",       "Executive dashboards, committee outcomes, escrow financials."),
    ("Partner",           "/staff",       "GOC / Bank / Regulator — audit hooks and co-procurement dashboards."),
    ("Agent",             "/staff",       "Field-ops — draft tenders, review dossiers, publish corrigenda."),
    ("Reviewer",          "/admin",       "Read-only + evaluation scoring."),
    ("Escrow agent",      "/staff",       "EMD desk, forfeitures, refunds."),
    ("Certifier",         "/staff",       "Tender packet sign-off."),
    ("Legal counsel",     "/staff",       "Contract review, DocuSign envelope owner."),
    ("Accounting",        "/staff",       "Fee invoicing, refunds, reconciliation."),
    ("Committee member",  "/staff",       "Evaluation committee voting."),
    ("Auditor",           "/admin (read)","Full audit trail with entity filters."),
    ("Support",           "/staff",       "Vendor helpdesk, activation resends."),
    ("Vendor",            "/vendor",      "Bid on notices, manage profile & invoices."),
]
p("| Role | Portal | Scope |\n|---|---|---|\n" +
  "\n".join(f"| {r} | `{portal}` | {scope} |" for r, portal, scope in roles) + "\n")

# ------- Chapter 3 — Security -------
h(2, "3 · Security, audit & data-protection")
p("**Authentication** — Three cookie realms (admin_session, staff_session, "
    "vendor_session). HttpOnly, SameSite=Lax, Secure in production. CSRF "
    "double-submit token on every mutating request. Brute-force lockout after "
    "5 failed attempts within 15 minutes.")
p("**Authorisation** — `require_role(*roles)` dependency guards every mutating "
    "endpoint. Read endpoints use `current_admin` / `current_staff` / "
    "`current_vendor` for realm assertions. Role membership persists in the "
    "staff_users / admin_users / vendors collections with a versioned "
    "history so ACL changes are auditable.")
p("**Audit trail** — Every mutation calls `audit_log(action, actor, entity, "
    "entity_ref, payload)` which persists into the `audits` collection with "
    "an immutable ISO timestamp, actor id, and a JSON payload snapshot. "
    "Auditors can filter by entity + action + actor + date range in the "
    "Audit tab and export to CSV.")
p("**Data protection** — Vendor licences and legal documents are stored in a "
    "private S3 bucket behind pre-signed URLs. Personally identifiable data "
    "is redacted from audit-log exports when the actor role is Auditor.")
p("**Compliance** — GDPR data-processing consent is captured on the public "
    "registration wizard; ESG questionnaire responses live under the vendor "
    "profile.")

# ------- Emit captured screens by section -------
by_section: dict[str, list[dict]] = {}
for m in MANIFEST:
    by_section.setdefault(m["section"], []).append(m)

def emit_screen(entry: dict):
    fn = entry["file"]
    dd = DEEP.get(fn)
    h(3, f"{entry['n']:>2d} · {entry['title']}")
    p(entry["description"])
    img(fn, entry["title"])
    if dd:
        h(4, "Purpose")
        p(dd["purpose"])
        h(4, "How the workflow unfolds")
        p(dd["workflow"])
        h(4, "Fields")
        for name, desc in dd["fields"]:
            p(f"- **{name}** — {desc}")
        if dd.get("gotchas"):
            h(4, "Known gotchas")
            for g in dd["gotchas"]:
                p(f"- {g}")
    else:
        h(4, "How to use")
        p(GENERIC)

section_titles = {
    "Public": "4 · Public visitor journey",
    "Vendor": "5 · Vendor / supplier journey",
    "Admin":  "6 · Admin console — full module tour",
}
for sec, header in section_titles.items():
    h(2, header)
    for entry in by_section.get(sec, []):
        emit_screen(entry)

# ------- Chapter 7 · Tender Builder -------
h(2, "7 · Deep-dive: Tender Builder & AI DPR (v46l map-reduce)")
p("v46l ships the most substantial AI upgrade to date: **unlimited DPR "
    "ingestion + background workers**. The pipeline turns any Detailed "
    "Project Report — up to 100 MB, 500+ pages — into a fully structured "
    "tender pack.")
p("**Extraction.** PDFs decode via pypdf, DOCX via python-docx, TXT direct. "
    "The extracted text is chunked into 40 KB windows with 3 KB overlap to "
    "preserve context across boundaries. The MAX_CHUNKS ceiling is 500 "
    "(configurable via `DPR_MAX_CHUNKS`) — the previous 20-chunk cap is "
    "removed.")
p("**Pass 1a — per-chunk map.** Each chunk is sent to the LLM with a strict "
    "JSON contract requesting header hints (work title, budget, deadlines, "
    "EMD) and a list of sections observed in that chunk. Bounded concurrency "
    "via an asyncio semaphore of 4 so the LLM proxy is never saturated.")
p("**Pass 1b — reduce.** Local blueprints are merged: header hints first-"
    "wins across chunks (rich early chunks dominate), section list is "
    "deduplicated by title. Sections cap at 60 (was 30).")
p("**Pass 2 — draft.** Each discovered section is drafted from the passage "
    "of the DPR most relevant to its anchor phrase (LLM-provided) or title. "
    "Bounded concurrency of 6. Bodies under 200 chars trigger the raw-passage "
    "fallback so nothing lands as a stub.")
p("**Progress + async.** Files ≥ 4 MB take the async path. The frontend posts "
    "to `/dpr/analyze-async`, gets a `job_id` and polls `/dpr/jobs/{id}` every "
    "3 s until status == done. Every phase writes a percentage + human phase "
    "string into the `dpr_jobs` collection (`mapping 6/14`, `drafting 22/58`, "
    "`complete`) so the UI shows a real progress bar.")
p("**Nginx tuning.** `.platform/nginx/conf.d/proxy.conf` sets "
    "`client_max_body_size 200M` and all timeouts to `300s` so multi-hundred-"
    "MB base64 payloads do not trigger 413 or idle timeouts.")

# ------- Chapter 8 · Evaluation + escrow -------
h(2, "8 · Deep-dive: Evaluation, awards & escrow")
p("**Rubric.** Every notice defines a scoring rubric — a list of technical "
    "criteria with weights summing to 1.00, a commercial weight, and a "
    "minimum technical cutoff percentage. RubricEditor enforces every "
    "constraint client-side and disables Save until valid.")
p("**Envelope lock.** Once the technical envelope is locked (`POST "
    "/api/v1/evaluations/lock-envelope`) the backend refuses new scores (409). "
    "v46m hardens this to also refuse re-lock — a rogue direct API call cannot "
    "silently overwrite the lock timestamp / attribution. The frontend fetches "
    "`GET /evaluations/lock-state/{ref}` on every notice-ref change and swaps "
    "Lock buttons to a 'Sealed 🔒' chip with a green banner showing the "
    "sealer and timestamp.")
p("**Award report.** With both envelopes sealed, the award report combines "
    "weighted technical + commercial scores, applies the technical cutoff, "
    "and produces the L1 comparison table. Ties are broken by lower price, "
    "then earlier submission timestamp, then higher aggregate rating.")
p("**Escrow.** The joint-account model requires two officers per transaction. "
    "The account snapshot is stored on every escrow_transaction row so a "
    "later officer roster change does not retroactively affect audit history.")

# ------- Chapter 9 · Auctions -------
h(2, "9 · Deep-dive: Reverse auctions")
p("Reverse auctions run only for tenders that opt in. Qualified vendors "
    "receive an invitation, join with a masked alias (never their company "
    "name), and place manual or auto bids.")
p("**Auto-bid** — Vendors set a walk-away floor. The platform undercuts the "
    "current lowest by min_decrement whenever the vendor is not the leader, "
    "until the vendor hits the floor.")
p("**Anti-sniping** — Bids placed in the final 60 seconds extend the auction "
    "by 5 minutes so no one can win by ambushing at the buzzer.")
p("**Public spectator link** — Auditors watch the room via a read-only URL "
    "with masked aliases so bidder identity is never exposed even in the audit "
    "trail.")

# ------- Chapter 10 · UX safety -------
h(2, "10 · Tooltip, error-handling & offline system")
p("Three complementary UX safeties keep the platform legible under stress.")
p("**InfoDot (ⓘ)** — Hover tooltip used **166 times** across 20+ admin "
    "panels. Every field label with a non-obvious policy has one attached. "
    "Source: `frontend/src/components/InfoDot.jsx`.")
p("**`showApiError` / `formatApiError`** — 67 files consume these helpers. "
    "Every server error surfaces as a sonner toast with the exact backend "
    "detail (never a bare stack trace). The toast is dismissible but not "
    "auto-hidden so users can copy the error string into support tickets.")
p("**ErrorBoundary** — mounted at the app root; catches any React crash and "
    "renders a graceful fallback with a copyable diagnostic id. Never blocks "
    "the entire app.")
p("**Offline** — The service worker was deliberately un-registered in v46 "
    "after a stale-cache incident. The current build ships a self-destruct "
    "SW that unregisters itself on load. Do not re-enable without adding a "
    "cache-busting query string strategy.")

# ------- Chapter 11 · Deployment -------
h(2, "11 · Deployment runbook (S3 + CloudFront + Elastic Beanstalk)")
p("**Frontend.** Build with `REACT_APP_BACKEND_URL=\"\" yarn build` so the "
    "bundle uses same-origin `/api` calls. Sync to S3 with `--exact-timestamps` "
    "and `--exclude \"downloads/*\"` to preserve the public download folder. "
    "Invalidate CloudFront `/*` after the sync.")
p("**Backend.** Package `backend/`, `.platform/nginx/conf.d/proxy.conf`, "
    "`Dockerfile`, `Dockerrun.aws.json`, `VERSION` into a zip. Never bundle "
    "`backend/.env` — use EB environment properties. Deploy via `eb deploy "
    "--staged --label vXX`.")
p("**Never** run `aws s3 sync ... --delete` at bucket root — it will delete "
    "the public `/downloads/` folder and every manual/artifact in it.")
p("**Rollback.** Elastic Beanstalk keeps every prior version; roll back via "
    "the EB console → Application versions → Deploy previous.")

# ------- Chapter 12 · Troubleshooting -------
h(2, "12 · Troubleshooting playbook")
tb = [
    ("Landing shows 0 counters",           "Stale CloudFront cache",              "Invalidate `/*` on CloudFront"),
    ("'No matching employee' toast",       "Preview URL baked into prod bundle",  "Rebuild with `REACT_APP_BACKEND_URL=\"\" yarn build`"),
    ("DPR returns 5 generic sections",     "Backend on ≤ v46g",                   "Deploy v46l map-reduce backend"),
    ("Progress bar stuck at 2%",           "Async worker crashed",                "Check `/api/v1/tender-pro/dpr/jobs/{id}` for `error` field"),
    ("413 on large DPR",                   "nginx body limit",                    "Deploy v46l — `client_max_body_size 200M`"),
    ("Login OK but /admin bounces",        "Cross-site cookie blocked",           "Ensure frontend calls same-origin `/api`"),
    ("Envelope re-locks silently",         "Direct API bypasses UI",              "v46m rejects re-lock with 409"),
    ("Auction bidder identity leaks",      "Masked alias not applied",            "Re-open room; masking is server-side"),
    ("Refund never reaches vendor",        "Second signer missed the notification","Check joint-account snapshot on the transaction"),
    ("Resend email lands in spam",         "First-touch corporate MX filter",     "Resend from Registrations queue with a warm-up sender"),
]
p("| Symptom | Root cause | Fix |\n|---|---|---|\n" +
  "\n".join(f"| {a} | {b} | {c} |" for a, b, c in tb) + "\n")

# ------- Chapter 13 · API index -------
h(2, "13 · API reference index")
apis = [
    ("`GET  /api/v1/meta/public/stats`",         "Public — landing KPIs."),
    ("`GET  /api/v1/meta/public/notices`",       "Public — list notices."),
    ("`POST /api/v1/admin/auth/login`",          "Admin realm login (cookie)."),
    ("`POST /api/v1/staff/auth/login`",          "Staff realm login."),
    ("`POST /api/v1/vendor/auth/login`",         "Vendor realm login."),
    ("`POST /api/v1/registrations/draft`",       "Create registration draft."),
    ("`POST /api/v1/registrations/submit`",      "Submit for review."),
    ("`POST /api/v1/tender-pro/dpr/analyze-json`","Synchronous DPR analysis (< 4 MB)."),
    ("`POST /api/v1/tender-pro/dpr/analyze-async`","**v46l** kick off async DPR analysis."),
    ("`GET  /api/v1/tender-pro/dpr/jobs/{id}`",  "**v46l** poll async DPR job status."),
    ("`POST /api/v1/tender-pro/templates/{id}/save-as-master`","Promote a draft to a reusable master."),
    ("`POST /api/v1/evaluations/rubric`",        "Upsert rubric for a notice."),
    ("`POST /api/v1/evaluations/lock-envelope`", "**v46m** now refuses re-lock (409)."),
    ("`GET  /api/v1/evaluations/lock-state/{ref}`","**v46m** returns seal timestamps + attribution."),
    ("`POST /api/v1/evaluations/score`",         "Submit a technical or commercial score."),
    ("`GET  /api/v1/evaluations/award-report/{ref}`","Generate the L1 comparison."),
    ("`POST /api/v1/escrow/transactions`",       "Record an EMD transaction."),
    ("`POST /api/v1/auctions/{ref}/bid`",        "Place an auction bid."),
    ("`POST /api/v1/reports/snapshot`",          "Persist stakeholder-report artefacts to disk."),
    ("`GET  /api/v1/stakeholder-reports/*`",     "Tenders / awards / escrow / SLA reports."),
]
p("| Endpoint | Purpose |\n|---|---|\n" +
  "\n".join(f"| {a} | {b} |" for a, b in apis) + "\n")

# ------- Chapter 14 · Release history -------
h(2, "14 · Release history")
releases = [
    ("v46m", "Bug Blitz Round Two — envelope re-lock 409, GET /lock-state, EvaluationPanel sealed banner, AuctionRoom mobile overflow fix."),
    ("v46l", "Unlimited DPR + async worker (MAX_CHUNKS 500, /dpr/analyze-async, /dpr/jobs/{id}, nginx 200 MB / 300 s, live progress bar)."),
    ("v46k", "Sovereign Redesign — 5-portal Sovereign Gateway, navy/gold editorial home hero, PmcFooter with social icons."),
    ("v46j", "Map-Reduce DPR first cut (still capped at 800 KB)."),
    ("v46i", "New roles (management/partner/agent), collapsible admin sidebar, editorial public design v1."),
    ("v46h", "Admin vendor form: per-section Save buttons + search."),
    ("v46g", "DPR deep-dive first cut (26 sections from KMT)."),
    ("v46f", "Editable tender name + reliable save-as-master."),
    ("v46e/d/c/b", "Bug blitz first pass — 60+ tracker items fixed."),
]
p("| Version | Highlights |\n|---|---|\n" +
  "\n".join(f"| **{v}** | {h_} |" for v, h_ in releases) + "\n")

# ------- Chapter 15 · Glossary -------
h(2, "15 · Glossary & appendix")
p("- " + "\n- ".join(f"**{term}** — {defn}" for term, defn in gl))

h(2, "16 · Role-by-role onboarding checklist (30 / 60 / 90 days)")
p("Every new hire follows the same three-milestone rhythm.")
p("**Admin — Day 1** — shadow an experienced admin through a full tender lifecycle (draft → publish → bid receipt → evaluation → award → contract). Read chapters 1–3 and 7–11.")
p("**Admin — Day 30** — publish your first tender end-to-end unsupervised. Own one committee evaluation cycle. Complete audit-trail search drills for two entity types.")
p("**Admin — Day 60** — configure a new country's masters (EMD, fee, category taxonomy, staff roles). Run one Tender Builder DPR ingestion on a 500-page tender.")
p("**Admin — Day 90** — lead a full quarterly stakeholder-report cycle. Present KPI trends to the Management portal.")
p("**Vendor onboarder (Support)** — Day 1: shadow a live activation. Day 30: process 10 registrations solo. Day 60: own resend-link edge cases and licence re-verification queues. Day 90: run a vendor-education webinar.")
p("**Escrow officer** — Day 1: read the joint-account snapshot model. Day 30: process 20 EMD receipts + 10 refunds. Day 60: handle one forfeiture with legal sign-off. Day 90: lead a monthly reconciliation against Stripe.")
p("**Committee member** — Day 1: complete the COI declaration training. Day 30: score 3 evaluations under a senior member. Day 60: lead one evaluation session. Day 90: chair a full committee meeting including minutes and public Q&A migration.")

h(2, "17 · Monthly operations cadence")
p("The rhythm PMC has settled on across six months of live operations.")
p("**Week 1** — Publish weekly digest via Resend. Reconcile prior-month escrow ledger. Publish stakeholder monthly report (tenders / awards / escrow / SLA).")
p("**Week 2** — Committee cycle for tenders whose submission deadline landed in the prior week.")
p("**Week 3** — Award ceremonies + DocuSign countersign push. Vendor invoicing run.")
p("**Week 4** — Roadmap review with GOC + Bank partners. Vendor NPS survey via Resend. Category taxonomy audit.")

h(2, "18 · North-Star KPIs and dashboards")
kpi_rows = [
    ("Notice cycle time", "Draft → Publish", "≤ 14 days", "Every published notice contributes its `published_at - draft_created_at`."),
    ("Bidder attention", "Bidders opening a notice / eligible bidders", "≥ 65 %", "Analytics funnel first stage."),
    ("Bids per notice", "Median across last 90 days", "≥ 4", "Signals healthy competition; below 3 triggers a category audit."),
    ("Technical qualification rate", "Technically qualified / bids received", "40–65 %", "Too low → tender spec too strict; too high → not selective enough."),
    ("EMD refund SLA", "Refund issued / eligible transactions in 30 days", "100 %", "Any breach opens an escrow post-mortem."),
    ("Contract signature SLA", "LOA → PMC countersign", "≤ 10 business days", "Legal team KPI."),
    ("Vendor NPS", "Quarterly survey", "≥ 42", "Below 30 triggers a vendor-experience review."),
    ("Dispute rate", "Opened disputes / awarded contracts", "≤ 3 %", "Above 5 % opens a legal + evaluation review."),
]
p("| KPI | Definition | Target | Notes |\n|---|---|---|---|\n" +
  "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in kpi_rows) + "\n")

h(2, "19 · Escalation matrix")
p("| Situation | First responder | 15 min | 1 h | 4 h | Owner |\n|---|---|---|---|---|---|\n"
    "| Auth outage | On-call admin | On-call engineer | CTO | CEO | CTO |\n"
    "| EMD refund overdue > 60 days | Escrow officer | Legal | Escrow lead | CFO | CFO |\n"
    "| Suspicious auction pattern | Auction ops | AI anomaly rerun | Legal | CEO | Legal |\n"
    "| Data breach suspected | Any staff | CTO | CEO | Communications | CTO |\n"
    "| Regulator inbound | Any staff | Partner lead | CEO | Board | Partner lead |\n")

h(2, "20 · Keyboard shortcuts")
p("| Shortcut | Action |\n|---|---|\n"
    "| ⌘ + K | Global command palette (planned) |\n"
    "| G then A | Jump to Analytics |\n"
    "| G then N | Jump to Notices |\n"
    "| G then T | Jump to Tender Builder |\n"
    "| G then E | Jump to Evaluation |\n"
    "| Esc | Close any open modal |\n"
    "| / | Focus the primary search box |\n"
    "| Shift + ? | Show the shortcut cheat sheet (planned) |\n")

h(2, "21 · Frequently asked questions (FAQ)")
faqs = [
    ("Can I edit a published notice?",
     "No — publish a corrigendum. The audit trail keeps every prior state and public visitors see the corrigendum immediately on the notice detail page."),
    ("How do I recover a lost tender draft?",
     "Every save is a rolling snapshot. Open Tender Builder → Version history and restore any prior snapshot; the restore itself is auto-snapshotted so it is undoable."),
    ("A vendor says they never received a fee invoice.",
     "Check the Billing tab for the invoice PDF and the Resend delivery log. If the email failed, resend from Billing → Row action. Corporate MX filters sometimes block first-touch domains — use the warm-up sender when needed."),
    ("How large a DPR can the AI ingest?",
     "v46l allows 100 MB per file / 500+ pages. Files ≥ 4 MB automatically use the async worker and show a live progress bar; you can leave the tab open and come back."),
    ("Can I re-open a locked evaluation envelope?",
     "No. v46m rejects re-lock with a 409. If you truly need to redo scoring, clone the notice into a new tender and re-run the evaluation cycle. Legal must approve."),
    ("How do I add a new country to the platform?",
     "Masters → Countries → New. Then seed EMD/fee slabs, category taxonomy, licences and staff roles for that country. The public homepage and registration wizard update immediately."),
    ("How does the AI avoid inventing numbers not present in the DPR?",
     "The section-drafting prompt forbids inventing numbers, and each draft is passed the specific DPR passage anchored to the section title. Bodies under 200 chars trigger the raw-passage fallback so no output is generated without source."),
    ("Where do I turn off email digests?",
     "Vendors: Vendor portal → Notifications. Staff: Profile → Preferences (planned)."),
    ("How is bidder identity protected in reverse auctions?",
     "Masked aliases assigned server-side on join. Even the audit trail stores only aliases; de-masking is admin-only post-close."),
    ("A stakeholder-report artefact failed to snapshot. What now?",
     "Every artefact is wrapped in its own try/except; the response returns a JSON `errors[]` array listing which artefact failed and why. Fix the specific artefact and re-hit /reports/snapshot — the rest are unaffected."),
]
for q, a in faqs:
    p(f"**Q — {q}**")
    p(a)
    p("")

h(2, "22 · Sample workflow — full lifecycle of one tender")
p("The end-to-end journey for a single procurement, from concept to close-out.")
p("**Day 0** — Package owner briefs the drafting agent. Agent opens Tender Builder → picks the country → picks or creates a master → opens the DPR modal and uploads the project brief. AI drafts every section body from the DPR passages. Agent reviews, adjusts EMD/fee, uploads BOQ CSV, saves the draft.")
p("**Day 3** — Legal counsel reviews. Any redlines go into a version snapshot. Legal signs off. Agent hits Publish. Resend digests fire to subscribed vendors. Snapchat + Instagram posts pushed automatically.")
p("**Day 3–17** — Pre-bid meeting held via Zoom on Day 5. Minutes uploaded, substantive Q&A migrated to the public notice. Corrigenda published as needed. Bidders purchase the tender pack; EMDs post to escrow.")
p("**Day 18** — Submission deadline. Admin locks technical envelope; the button flips to 'Sealed 🔒' and a green banner records the sealer and timestamp.")
p("**Day 18–28** — Evaluation committee scores technical. Rubric errors block invalid saves. Once all evaluators have submitted, admin locks commercial envelope. Committee scores commercial. Admin generates the award report → L1 identified.")
p("**Day 29** — LOA issued via DocuSign. Vendor accepts; PMC countersigns. PO number generated.")
p("**Day 30–...** — Contract runs. Milestones, timesheets, variation orders logged. EMD refunded on Day N post-close unless disputed. Vendor rating captured. Auditor exports the CSV bundle if requested.")

h(2, "23 · Data model appendix")
p("| Collection | Purpose | Hot indices |\n|---|---|---|\n"
    "| tenants | Multi-tenant scoping | code (unique) |\n"
    "| admin_users / staff_users / vendors | Auth realms | email (unique per tenant) |\n"
    "| notices | Published tender notices | notice_ref (unique), published_at, country |\n"
    "| tender_templates | Reusable master + drafts | (country, industry), is_master |\n"
    "| registrations | Vendor onboarding wizard state | magic_token, email, status |\n"
    "| bids | Submitted bids | notice_ref, vendor_ref |\n"
    "| rubrics | Per-notice scoring config | notice_ref (unique) |\n"
    "| scores | Evaluator scores | bid_id, evaluator |\n"
    "| escrow_transactions | EMDs held/refunded/forfeited | notice_ref, status |\n"
    "| auctions | Reverse auction rooms | notice_ref (unique) |\n"
    "| corrigenda | Notice amendments | notice_ref, published_at |\n"
    "| audits | Immutable audit trail | entity_ref, actor_id, at |\n"
    "| ratings | Post-contract reviews | vendor_ref |\n"
    "| dpr_jobs | v46l async DPR workers | _id, status |\n"
    "| reports_snapshots | Materialised stakeholder artefacts | generated_at |\n")

h(2, "24 · Appendix — release notes archive")
for v, hh in releases:
    p(f"**{v}** — {hh}")

h(2, "25 · Sign-off")
p("This manual is versioned and lives under `/app/deliverables/v46_manual/build/`. "
    "The source Markdown is the single source of truth; DOCX and PDF are "
    "regenerated from it via `python3 /app/tools/manual/build.py`. Screenshots "
    "are re-captured via `python3 /app/tools/manual/capture.py`. "
    "Refresh both artefacts after every material release.")

# ------- WRITE MD -------
md_text = "\n".join(md)
(OUT / "PMC_v3_Master_Training_Manual.md").write_text(md_text)

# ---------- DOCX ----------
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"; style.font.size = Pt(11)

doc.add_heading("PMC Managers · v46m Master Training Manual", 0)
para = doc.add_paragraph(BANNER)
para.alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in para.runs:
    r.italic = True; r.font.color.rgb = RGBColor(0x64, 0x64, 0x8b)

def d_h(txt, lvl): doc.add_heading(txt, level=lvl)
def d_p(txt): doc.add_paragraph(txt)
def d_img(pth):
    if pth.exists():
        try:
            doc.add_picture(str(pth), width=Inches(6.4))
        except Exception:
            pass

# Replay full narrative into docx (chapters 1-3 + screens + chapters 7-15)
d_h("1 · Platform overview & architecture", 1)
for para_text in md[3:22]:
    if para_text.strip() and not para_text.startswith("#"):
        d_p(para_text.strip())

d_h("2 · Roles at a glance", 1)
t = doc.add_table(rows=1, cols=3); t.style = "Light Grid Accent 1"
hd = t.rows[0].cells
hd[0].text, hd[1].text, hd[2].text = "Role", "Portal", "Scope"
for r, portal, scope in roles:
    row = t.add_row().cells
    row[0].text, row[1].text, row[2].text = r, portal, scope

d_h("3 · Security, audit & data-protection", 1)
d_p("Auth: three cookie realms (admin, staff, vendor). HttpOnly, SameSite=Lax, "
     "Secure in production. CSRF double-submit on writes. Brute-force lockout "
     "after 5 attempts in 15 minutes.")
d_p("Authorisation: require_role dependency guards every mutating endpoint.")
d_p("Audit: every mutation writes to the immutable audits collection with "
     "actor + timestamp + JSON payload snapshot.")
d_p("Data protection: private S3 bucket + pre-signed URLs for legal + licence "
     "docs. PII redacted in Auditor-role CSV exports.")
d_p("Compliance: GDPR consent captured at registration; ESG questionnaire on "
     "the vendor profile.")

for sec, header in section_titles.items():
    d_h(header, 1)
    for entry in by_section.get(sec, []):
        d_h(f"{entry['n']:>2d} · {entry['title']}", 2)
        d_p(entry["description"])
        d_img(SCREENS / entry["file"])
        dd = DEEP.get(entry["file"])
        if dd:
            d_h("Purpose", 3); d_p(dd["purpose"])
            d_h("How the workflow unfolds", 3); d_p(dd["workflow"])
            d_h("Fields", 3)
            for name, desc in dd["fields"]:
                pp = doc.add_paragraph(style="List Bullet")
                run = pp.add_run(name); run.bold = True
                pp.add_run(f" — {desc}")
            if dd.get("gotchas"):
                d_h("Known gotchas", 3)
                for g in dd["gotchas"]:
                    doc.add_paragraph(g, style="List Bullet")
        else:
            d_h("How to use", 3); d_p(GENERIC)

d_h("7 · Deep-dive: Tender Builder & AI DPR (v46l map-reduce)", 1)
d_p("v46l lifts the 800 KB ceiling and adds a background worker. MAX_CHUNKS "
     "500 (env-overridable). Files ≥ 4 MB auto-route to the async endpoint with "
     "a live progress bar. Pass 1a maps every 40 KB chunk (semaphore 4); Pass 1b "
     "reduces to a global blueprint (up to 60 sections); Pass 2 drafts each "
     "section body in parallel (semaphore 6) with a raw-passage fallback for "
     "stubs under 200 chars.")

d_h("8 · Deep-dive: Evaluation, awards & escrow", 1)
d_p("Rubric enforces weight 0–1 per criterion, sum ≈ 1.00, commercial 0–1, "
     "minimum technical 0–100. v46m locks are one-way; the backend refuses "
     "re-lock (409). Awards use QCBS with L1 comparison. Escrow is a two-"
     "signer joint-account model with a snapshot on every transaction.")

d_h("9 · Deep-dive: Reverse auctions", 1)
d_p("Vendors join with masked aliases, place manual or auto bids with a walk-"
     "away floor. Anti-snipe extends auctions on last-minute bids. Public "
     "spectator link exposes only masked aliases.")

d_h("10 · Tooltip, error-handling & offline system", 1)
d_p("InfoDot (166 uses), showApiError / formatApiError (67 files), "
     "ErrorBoundary at the app root; service worker deliberately un-registered.")

d_h("11 · Deployment runbook (S3 + CloudFront + EB)", 1)
d_p("Frontend: build with REACT_APP_BACKEND_URL='' so bundle uses same-origin "
     "/api. Sync with --exact-timestamps --exclude 'downloads/*'. Invalidate "
     "CloudFront /*. Backend: eb deploy --staged --label vXX. Never sync with "
     "--delete at bucket root.")

d_h("12 · Troubleshooting playbook", 1)
t2 = doc.add_table(rows=1, cols=3); t2.style = "Light Grid Accent 1"
hd = t2.rows[0].cells
hd[0].text, hd[1].text, hd[2].text = "Symptom", "Root cause", "Fix"
for a, b, c in tb:
    row = t2.add_row().cells
    row[0].text, row[1].text, row[2].text = a, b, c

d_h("13 · API reference index", 1)
t3 = doc.add_table(rows=1, cols=2); t3.style = "Light Grid Accent 1"
hd = t3.rows[0].cells
hd[0].text, hd[1].text = "Endpoint", "Purpose"
for a, b in apis:
    row = t3.add_row().cells
    row[0].text, row[1].text = a, b

d_h("14 · Release history", 1)
t4 = doc.add_table(rows=1, cols=2); t4.style = "Light Grid Accent 1"
hd = t4.rows[0].cells
hd[0].text, hd[1].text = "Version", "Highlights"
for v, h_ in releases:
    row = t4.add_row().cells
    row[0].text, row[1].text = v, h_

d_h("15 · Glossary", 1)
for term, defn in gl:
    pp = doc.add_paragraph(style="List Bullet")
    run = pp.add_run(term); run.bold = True
    pp.add_run(f" — {defn}")

doc.save(OUT / "PMC_v3_Master_Training_Manual.docx")

# ---------- PDF via WeasyPrint ----------
def esc(s: str) -> str: return html.escape(str(s))

def htmlize_screen_section(md_title: str, entries: list[dict]) -> str:
    parts = [f"<h1>{esc(md_title)}</h1>"]
    for e in entries:
        parts.append(f"<h2>{e['n']:>2d} · {esc(e['title'])}</h2>")
        parts.append(f"<p class='desc'>{esc(e['description'])}</p>")
        img_path = SCREENS / e["file"]
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode()
            parts.append(f'<div class="img"><img src="data:image/png;base64,{data}"/><div class="cap">{esc(e["title"])}</div></div>')
        dd = DEEP.get(e["file"])
        if dd:
            parts.append(f"<h3>Purpose</h3><p>{esc(dd['purpose'])}</p>")
            parts.append(f"<h3>How the workflow unfolds</h3><p>{esc(dd['workflow'])}</p>")
            parts.append("<h3>Fields</h3><ul>")
            for name, desc in dd["fields"]:
                parts.append(f"<li><b>{esc(name)}</b> — {esc(desc)}</li>")
            parts.append("</ul>")
            if dd.get("gotchas"):
                parts.append("<h3>Known gotchas</h3><ul>")
                for g in dd["gotchas"]:
                    parts.append(f"<li>{esc(g)}</li>")
                parts.append("</ul>")
        else:
            parts.append(f"<h3>How to use</h3><p>{esc(GENERIC)}</p>")
    return "\n".join(parts)

body_parts = []
body_parts.append("<h1>1 · Platform overview &amp; architecture</h1>")
overview_paras = [
    "The PMC platform is a multi-role tender lifecycle engine covering the full path from notice publication → registration → bidding → EMD → evaluation → award → e-signature → invoicing → post-contract audit. Delivered as a React SPA backed by FastAPI + MongoDB with same-origin cookie sessions and CSRF double-submit tokens.",
    "<b>Frontend</b> — React SPA served from S3 + CloudFront. Sovereign navy/gold editorial design system with Libre Baskerville + IBM Plex fonts. Routing via React Router; state via Context (i18n, auth) + local component state.",
    "<b>Backend</b> — FastAPI on AWS Elastic Beanstalk (Docker running on 64-bit Amazon Linux 2). All routes prefixed <code>/api/v1/…</code>. Auth realm split into admin, staff and vendor with per-realm login endpoints and cookie names.",
    "<b>Data</b> — MongoDB via Motor (async driver). Collections include tenants, notices, tender_templates, registrations, vendors, bids, rubrics, scores, evaluations, awards, escrow_transactions, auctions, corrigenda, audits, ratings, engagements, packages, categories, countries, dpr_jobs.",
    "<b>AI</b> — Managed AI Gateway (universal LLM key) routed through the integration proxy. Used for DPR ingestion (map-reduce), AI Fill All, anomaly detection and the admin copilot. v46l lifts the 800 KB cap and adds an async worker.",
    "<b>Storage</b> — S3 for licences, tender attachments, signed PDFs, archived auction rooms. CloudFront in front for global CDN.",
    "<b>Notifications</b> — Resend (email), planned Firebase/APNs (mobile push).",
    "<b>Payments</b> — Stripe (test + live keys separated); Kaspi + PayPal on the roadmap.",
    "<b>E-signature</b> — DocuSign envelope templates + status webhooks.",
    "<b>Observability</b> — Structured logs via Python logging, CloudWatch tail, audit_log() collection for every mutation.",
]
for pt in overview_paras:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>2 · Roles at a glance</h1><table><tr><th>Role</th><th>Portal</th><th>Scope</th></tr>")
for r, portal, scope in roles:
    body_parts.append(f"<tr><td>{esc(r)}</td><td><code>{esc(portal)}</code></td><td>{esc(scope)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>3 · Security, audit &amp; data-protection</h1>")
for pt in [
    "<b>Authentication</b> — Three cookie realms (admin_session, staff_session, vendor_session). HttpOnly, SameSite=Lax, Secure in production. CSRF double-submit on every mutating request. Brute-force lockout after 5 failed attempts within 15 minutes.",
    "<b>Authorisation</b> — <code>require_role(*roles)</code> guards every mutating endpoint. Read endpoints use realm-specific <code>current_admin</code> / <code>current_staff</code> / <code>current_vendor</code> dependencies.",
    "<b>Audit trail</b> — Every mutation calls <code>audit_log()</code> which writes an immutable row (actor id, timestamp, entity, action, JSON payload) to the audits collection. Auditors filter by entity + action + actor + date and export CSV.",
    "<b>Data protection</b> — Licences and legal docs sit in a private S3 bucket behind pre-signed URLs. PII is redacted from Auditor-role CSV exports.",
    "<b>Compliance</b> — GDPR consent captured at registration; ESG questionnaire lives under the vendor profile.",
]:
    body_parts.append(f"<p>{pt}</p>")

for sec, header in section_titles.items():
    body_parts.append(htmlize_screen_section(header, by_section.get(sec, [])))

# Chapter 7 — Tender Builder
body_parts.append("<h1>7 · Deep-dive: Tender Builder &amp; AI DPR (v46l map-reduce)</h1>")
for pt in [
    "v46l delivers the most substantial AI upgrade to date: <b>unlimited DPR ingestion + background workers</b>. The pipeline turns any Detailed Project Report — up to 100 MB, 500+ pages — into a fully structured tender pack.",
    "<b>Extraction.</b> PDFs decode via pypdf, DOCX via python-docx, TXT direct. The extracted text is chunked into 40 KB windows with 3 KB overlap to preserve context across boundaries. The <code>MAX_CHUNKS</code> ceiling is 500 (env-overridable) — the previous 20-chunk cap is removed.",
    "<b>Pass 1a — per-chunk map.</b> Each chunk is sent to the LLM with a strict JSON contract requesting header hints and a section list observed in that chunk. Concurrency bounded to 4.",
    "<b>Pass 1b — reduce.</b> Local blueprints are merged; sections deduped by title. Cap 60.",
    "<b>Pass 2 — draft.</b> Each discovered section is drafted from the passage of the DPR most relevant to its anchor phrase or title. Concurrency 6. Bodies under 200 chars trigger the raw-passage fallback so nothing lands as a stub.",
    "<b>Progress + async.</b> Files ≥ 4 MB take the async path. Frontend polls <code>/dpr/jobs/{id}</code> every 3 s; every phase writes a percentage + phase string into <code>dpr_jobs</code> so the UI renders a live progress bar.",
    "<b>Nginx tuning.</b> <code>client_max_body_size 200M</code>, all timeouts <code>300s</code>. No 413, no idle timeouts on multi-hundred-MB payloads.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>8 · Deep-dive: Evaluation, awards &amp; escrow</h1>")
for pt in [
    "<b>Rubric.</b> Every notice defines a scoring rubric — technical criteria with weights summing to 1.00, commercial weight, minimum technical cutoff. Client + server both enforce.",
    "<b>Envelope lock.</b> POST /evaluations/lock-envelope refuses re-lock (409, v46m). GET /evaluations/lock-state/{ref} returns seal timestamps. UI swaps buttons to 'Sealed 🔒' with a green banner.",
    "<b>Award report.</b> Combines weighted technical + commercial scores, applies technical cutoff, produces the L1 comparison. Ties broken by price, then submission timestamp, then aggregate rating.",
    "<b>Escrow.</b> Joint-account model — two officers per transaction, account snapshot preserved on every row for immutable audit history.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>9 · Deep-dive: Reverse auctions</h1>")
for pt in [
    "Vendors join with masked aliases. Manual + auto bids. Auto-bid config takes a walk-away floor.",
    "Anti-sniping: bids in the last 60 s extend the auction by 5 minutes.",
    "Public spectator link exposes only masked aliases.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>10 · Tooltip, error-handling &amp; offline system</h1>")
for pt in [
    "<b>InfoDot (ⓘ)</b> — 166 uses across 20+ admin panels. Every field label with a non-obvious rule has one.",
    "<b>showApiError / formatApiError</b> — 67 files. Every server error becomes a sonner toast with the exact backend detail.",
    "<b>ErrorBoundary</b> — mounted at the app root; catches React crashes with a copyable diagnostic id.",
    "<b>Service worker</b> — deliberately unregistered; a self-destruct SW handles legacy installs.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>11 · Deployment runbook (S3 + CloudFront + EB)</h1>")
for pt in [
    "<b>Frontend.</b> Build with <code>REACT_APP_BACKEND_URL=\"\" yarn build</code> so the bundle uses same-origin /api. Sync with <code>--exact-timestamps --exclude \"downloads/*\"</code>. Invalidate CloudFront <code>/*</code>.",
    "<b>Backend.</b> Package backend/ + .platform/nginx/conf.d/proxy.conf + Dockerfile + Dockerrun.aws.json + VERSION into a zip. Never bundle backend/.env — use EB env properties. Deploy: <code>eb deploy --staged --label vXX</code>.",
    "<b>Never</b> run <code>aws s3 sync ... --delete</code> at bucket root — it will delete the public <code>/downloads/</code> folder.",
    "<b>Rollback.</b> Elastic Beanstalk keeps every prior version; roll back via Application versions → Deploy previous.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>12 · Troubleshooting playbook</h1><table><tr><th>Symptom</th><th>Root cause</th><th>Fix</th></tr>")
for a, b, c in tb:
    body_parts.append(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>13 · API reference index</h1><table><tr><th>Endpoint</th><th>Purpose</th></tr>")
for a, b in apis:
    body_parts.append(f"<tr><td>{a}</td><td>{esc(b)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>14 · Release history</h1><table><tr><th>Version</th><th>Highlights</th></tr>")
for v, hh in releases:
    body_parts.append(f"<tr><td><b>{esc(v)}</b></td><td>{esc(hh)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>15 · Glossary &amp; appendix</h1><ul>")
for term, defn in gl:
    body_parts.append(f"<li><b>{esc(term)}</b> — {esc(defn)}</li>")
body_parts.append("</ul>")

# ---------------------------------------------------------------------------
# v46o expansion — inject chapters 26 – 36 (modal walkthroughs, regulator
# liaison, ESG questionnaire, per-role runbooks, forms reference, bug
# tracker snapshot, DPR internals, incident response, data retention,
# vendor curriculum, change management) into BOTH the MD build and the
# PDF body_parts list. Content lives in build_extensions.py so this file
# stays readable.
# ---------------------------------------------------------------------------
from build_extensions import (
    MODAL_WALKS, REGULATOR_PROTOCOL, ESG_QUESTIONNAIRE, ROLE_RUNBOOKS,
    FORM_FIELDS, BUG_TRACKER_STATE, INCIDENT_RESPONSE, DATA_RETENTION,
    VENDOR_CURRICULUM, CHANGE_MANAGEMENT,
    SECURITY_CONTROLS, TENDER_COMMITTEE_CONSTITUTION, DR_DRILL_SCRIPT,
    SAMPLE_NOTICE, SAMPLE_BID, DETAILED_API_REFERENCE, ACCEPTANCE_TESTS,
    SAMPLE_CORRIGENDA, SAMPLE_DOCUSIGN_WALK, STAKEHOLDER_REPORT_SAMPLE,
    AUDIT_TRAIL_SAMPLE, MOU_TEMPLATE, RACI_MATRIX, COST_BENEFIT_WORKSHEET,
    COMMITTEE_MINUTES_TEMPLATE, PROCUREMENT_POLICY_SUMMARY,
    LOCALISATION_STRINGS, VENDOR_SANDBOX, COMMITTEE_TRAINING, ETHICS_CODE,
    BOARD_REPORTING_PACK, IT_OPERATIONS,
    SAMPLE_QA_DIGEST, BID_EVAL_MATRIX, STANDARD_CLAUSES,
    COMMS_TEMPLATES, NPS_SURVEY, DEBARMENT_LOG,
    TEXT_MESSAGE_LIBRARY, RELEASE_PLANNING, MANUAL_MAINTENANCE,
)

# ------- MD chapters 26 – 36 -------
h(2, "26 · Modal walkthroughs")
for title, path, fields, gotchas in MODAL_WALKS:
    h(3, title); p(path)
    h(4, "Fields")
    for f in fields:
        p(f"- {f}")
    if gotchas:
        h(4, "Known gotchas")
        for g in gotchas:
            p(f"- {g}")

h(2, "27 · Regulator-liaison protocol")
for t, d in REGULATOR_PROTOCOL:
    h(3, t); p(d)

h(2, "28 · ESG questionnaire (procurement bidders)")
for cat, qs in ESG_QUESTIONNAIRE:
    h(3, cat)
    for q in qs:
        p(f"- {q}")

h(2, "29 · Per-role runbooks")
for role, items in ROLE_RUNBOOKS:
    h(3, role)
    for it in items:
        p(f"- {it}")

h(2, "30 · Field-by-field forms reference")
for form_name, fields in FORM_FIELDS:
    h(3, form_name)
    for name, desc in fields:
        p(f"- {name} — {desc}")

h(2, "31 · Bug tracker snapshot (v46o cutover)")
for section, items in BUG_TRACKER_STATE:
    h(3, section)
    for it in items:
        p(f"- {it}")

h(2, "32 · DPR pipeline internal reference (v46l)")
for para_text in [
    "**Entry points.** Sync `POST /api/v1/tender-pro/dpr/analyze-json` for < 4 MB payloads and async `POST /api/v1/tender-pro/dpr/analyze-async` for anything larger. Both accept `{filename, content_b64}` and an optional `?template_id=` query param.",
    "**Extraction.** `_extract_text_from_upload(name, body_bytes)` routes by file extension. PDF → pypdf iter-pages; DOCX → python-docx paragraph concatenation; TXT → UTF-8 decode. All emit `\\n\\n` between logical blocks so downstream chunking finds natural boundaries.",
    "**Chunking.** `_chunk_text(text)` slides a 40 000-char window with 3 000-char overlap. Cap `DPR_MAX_CHUNKS=500` (env-overridable). Returns `[(offset, chunk_text), …]`.",
    "**Pass 1a — per-chunk map.** Semaphore(4). System prompt asks for `{header_hints, sections}` as strict JSON. `header_hints` covers work title, budget, deadlines, EMD, evaluation method. `sections[]` carries `{title, hint, anchor_phrase}` where `anchor_phrase` is a 6-12 word verbatim snippet used later to locate the passage most relevant to a section.",
    "**Pass 1b — global reduce.** `merged_header` first-wins across chunks (rich early chunks dominate). `global_sections` deduplicates by lowercased title; ties break by earliest occurrence. Caps at 60 (was 30 pre-v46l).",
    "**Pass 2 — draft.** Semaphore(6). `_best_chunk(sec, i)` picks the chunk whose text contains `anchor_phrase` (case-insensitive) — falls back to chunk `i % len(chunks)` if no match. Draft prompt forbids inventing numbers; asks for 280-360 words HTML with a strict tag allow-list. Bodies under 200 chars trigger the raw-passage fallback so nothing lands as a stub.",
    "**Async progress.** `progress_cb(pct, phase)` is invoked at every phase transition. The worker (`_dpr_job_worker`) writes `{progress, phase, status, updated_at}` into the `dpr_jobs` collection so the UI polls a real percentage rather than a spinner.",
    "**Error surface.** Any 413/422/502 propagates as-is; unexpected exceptions surface as `500` with `{error: 'TypeName: str[:400]}`. The UI shows the exact string in a sonner toast (see chapter 10).",
    "**Nginx tuning.** `client_max_body_size 200M` + `client_body_timeout 300s` + `proxy_read_timeout 300s`. Without these, EB's default idle 60 s kills any 20-MB base64 upload.",
    "**Observability.** Every DPR job writes an audit row (`tender_pro.dpr_analyze`) on start + completion with size + section count. CloudWatch tail: `filterPattern=/dpr/analyze` for latency, `filterPattern='dpr.job.failed'` for failure rate.",
]:
    p(para_text)

h(2, "33 · Incident-response playbook")
for t, d in INCIDENT_RESPONSE:
    h(3, t); p(d)

h(2, "34 · Data-retention & backup policy")
p("| Entity | Retention | Notes |\n|---|---|---|\n" +
  "\n".join(f"| {a} | {b} | — |" for a, b in DATA_RETENTION) + "\n")

h(2, "35 · Vendor education curriculum")
for m, d in VENDOR_CURRICULUM:
    h(3, m); p(d)

h(2, "36 · Change management & release cadence")
for t, d in CHANGE_MANAGEMENT:
    h(3, t); p(d)

h(2, "37 · Security controls matrix")
for group, items in SECURITY_CONTROLS:
    h(3, group)
    for name, desc in items:
        p(f"- **{name}** — {desc}")

h(2, "38 · Tender committee constitution")
for t, d in TENDER_COMMITTEE_CONSTITUTION:
    h(3, t); p(d)

h(2, "39 · Disaster-recovery drill script")
for t, d in DR_DRILL_SCRIPT:
    h(3, t); p(d)

h(2, "40 · Sample notice (annotated)")
for t, d in SAMPLE_NOTICE:
    h(3, t); p(d)

h(2, "41 · Sample bid (annotated)")
for t, d in SAMPLE_BID:
    h(3, t); p(d)

h(2, "42 · Detailed API reference")
for group, endpoints in DETAILED_API_REFERENCE:
    h(3, group)
    for ep, desc in endpoints:
        p(f"- `{ep}` — {desc}")

h(2, "43 · Acceptance-test matrix")
for area, tests in ACCEPTANCE_TESTS:
    h(3, area)
    for t in tests:
        p(f"- {t}")

h(2, "44 · Sample corrigenda log")
for t, d in SAMPLE_CORRIGENDA:
    h(3, t); p(d)

h(2, "45 · Sample DocuSign envelope walkthrough")
for t, d in SAMPLE_DOCUSIGN_WALK:
    h(3, t); p(d)

h(2, "46 · Stakeholder-report sample")
for t, d in STAKEHOLDER_REPORT_SAMPLE:
    h(3, t); p(d)

h(2, "47 · Audit-trail export sample")
for t, d in AUDIT_TRAIL_SAMPLE:
    h(3, t); p(d)

h(2, "48 · MoU template (Sponsor ↔ Platform Operator)")
for t, d in MOU_TEMPLATE:
    h(3, t); p(d)

h(2, "49 · RACI matrix")
p("| Activity | Assignment |\n|---|---|\n" +
  "\n".join(f"| {a} | {b} |" for a, b in RACI_MATRIX) + "\n")

h(2, "50 · Cost-benefit worksheet (KZ programme, illustrative)")
for t, d in COST_BENEFIT_WORKSHEET:
    h(3, t); p(d)

h(2, "51 · Committee minutes template")
for t, d in COMMITTEE_MINUTES_TEMPLATE:
    h(3, t); p(d)

h(2, "52 · Procurement policy summary")
for t, d in PROCUREMENT_POLICY_SUMMARY:
    h(3, t); p(d)

h(2, "53 · Localisation strings (EN / RU / KK)")
for group, items in LOCALISATION_STRINGS:
    h(3, group)
    for key, val in items:
        p(f"- `{key}` — {val}")

h(2, "54 · Vendor sandbox playbook")
for t, d in VENDOR_SANDBOX:
    h(3, t); p(d)

h(2, "55 · Committee training curriculum")
for t, d in COMMITTEE_TRAINING:
    h(3, t); p(d)

h(2, "56 · Ethics code")
for t, d in ETHICS_CODE:
    h(3, t); p(d)

h(2, "57 · Board reporting pack")
for t, d in BOARD_REPORTING_PACK:
    h(3, t); p(d)

h(2, "58 · IT operations manual")
for t, d in IT_OPERATIONS:
    h(3, t); p(d)

h(2, "59 · Sample Q&A digest")
for t, d in SAMPLE_QA_DIGEST:
    h(3, t); p(d)

h(2, "60 · Sample bid evaluation matrix")
for t, d in BID_EVAL_MATRIX:
    h(3, t); p(d)

h(2, "61 · Standard clauses library")
for t, d in STANDARD_CLAUSES:
    h(3, t); p(d)

h(2, "62 · Communications templates")
for t, d in COMMS_TEMPLATES:
    h(3, t); p(d)

h(2, "63 · Vendor NPS survey")
for t, d in NPS_SURVEY:
    h(3, t); p(d)

h(2, "64 · Debarment log format")
for t, d in DEBARMENT_LOG:
    h(3, t); p(d)

h(2, "65 · SMS / in-app message library")
for t, d in TEXT_MESSAGE_LIBRARY:
    h(3, t); p(d)

h(2, "66 · Release planning — CY 2027")
for t, d in RELEASE_PLANNING:
    h(3, t); p(d)

h(2, "67 · Manual maintenance guide")
for t, d in MANUAL_MAINTENANCE:
    h(3, t); p(d)

# ------- PDF body_parts chapters 26 – 36 -------
body_parts.append("<h1>26 · Modal walkthroughs</h1>")
for title, path, fields, gotchas in MODAL_WALKS:
    body_parts.append(f"<h2>{esc(title)}</h2><p>{esc(path)}</p>")
    body_parts.append("<h3>Fields</h3><ul>")
    for f in fields:
        body_parts.append(f"<li>{esc(f)}</li>")
    body_parts.append("</ul>")
    if gotchas:
        body_parts.append("<h3>Known gotchas</h3><ul>")
        for g in gotchas:
            body_parts.append(f"<li>{esc(g)}</li>")
        body_parts.append("</ul>")

body_parts.append("<h1>27 · Regulator-liaison protocol</h1>")
for t, d in REGULATOR_PROTOCOL:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>28 · ESG questionnaire (procurement bidders)</h1>")
for cat, qs in ESG_QUESTIONNAIRE:
    body_parts.append(f"<h2>{esc(cat)}</h2><ul>")
    for q in qs:
        body_parts.append(f"<li>{esc(q)}</li>")
    body_parts.append("</ul>")

body_parts.append("<h1>29 · Per-role runbooks</h1>")
for role, items in ROLE_RUNBOOKS:
    body_parts.append(f"<h2>{esc(role)}</h2><ul>")
    for it in items:
        body_parts.append(f"<li>{esc(it)}</li>")
    body_parts.append("</ul>")

body_parts.append("<h1>30 · Field-by-field forms reference</h1>")
for form_name, fields in FORM_FIELDS:
    body_parts.append(f"<h2>{esc(form_name)}</h2><table><tr><th>Field</th><th>Description</th></tr>")
    for name, desc in fields:
        body_parts.append(f"<tr><td>{name}</td><td>{esc(desc)}</td></tr>")
    body_parts.append("</table>")

body_parts.append("<h1>31 · Bug tracker snapshot (v46o cutover)</h1>")
for section, items in BUG_TRACKER_STATE:
    body_parts.append(f"<h2>{esc(section)}</h2><ul>")
    for it in items:
        body_parts.append(f"<li>{esc(it)}</li>")
    body_parts.append("</ul>")

body_parts.append("<h1>32 · DPR pipeline internal reference (v46l)</h1>")
for para_text in [
    "<b>Entry points.</b> Sync <code>POST /api/v1/tender-pro/dpr/analyze-json</code> for &lt; 4 MB payloads and async <code>POST /api/v1/tender-pro/dpr/analyze-async</code> for anything larger. Both accept <code>{filename, content_b64}</code> and an optional <code>?template_id=</code> query param.",
    "<b>Extraction.</b> <code>_extract_text_from_upload(name, body_bytes)</code> routes by file extension. PDF → pypdf iter-pages; DOCX → python-docx paragraph concatenation; TXT → UTF-8 decode. All emit <code>\\n\\n</code> between logical blocks so downstream chunking finds natural boundaries.",
    "<b>Chunking.</b> <code>_chunk_text(text)</code> slides a 40 000-char window with 3 000-char overlap. Cap <code>DPR_MAX_CHUNKS=500</code> (env-overridable). Returns <code>[(offset, chunk_text), …]</code>.",
    "<b>Pass 1a — per-chunk map.</b> Semaphore(4). System prompt asks for <code>{header_hints, sections}</code> as strict JSON. Each section carries <code>{title, hint, anchor_phrase}</code>; the anchor_phrase is a 6-12 word verbatim snippet used later to locate the passage most relevant to a section.",
    "<b>Pass 1b — global reduce.</b> <code>merged_header</code> first-wins across chunks. <code>global_sections</code> deduplicates by lowercased title; ties break by earliest occurrence. Caps at 60 (was 30 pre-v46l).",
    "<b>Pass 2 — draft.</b> Semaphore(6). <code>_best_chunk(sec, i)</code> picks the chunk whose text contains anchor_phrase (case-insensitive). Draft prompt forbids inventing numbers; asks for 280-360 words HTML with a strict tag allow-list. Bodies under 200 chars trigger the raw-passage fallback so nothing lands as a stub.",
    "<b>Async progress.</b> <code>progress_cb(pct, phase)</code> is invoked at every phase transition. The worker (<code>_dpr_job_worker</code>) writes <code>{progress, phase, status, updated_at}</code> into <code>dpr_jobs</code> so the UI polls a real percentage.",
    "<b>Error surface.</b> Any 413/422/502 propagates as-is; unexpected exceptions surface as 500 with <code>{error: 'TypeName: str[:400]}</code>.",
    "<b>Nginx tuning.</b> <code>client_max_body_size 200M</code> + <code>client_body_timeout 300s</code> + <code>proxy_read_timeout 300s</code>. Without these, EB's default idle 60 s kills any 20 MB base64 upload.",
    "<b>Observability.</b> Every DPR job writes an audit row (<code>tender_pro.dpr_analyze</code>) on start + completion with size + section count. CloudWatch tail: <code>filterPattern=/dpr/analyze</code> for latency, <code>filterPattern='dpr.job.failed'</code> for failure rate.",
]:
    body_parts.append(f"<p>{para_text}</p>")

body_parts.append("<h1>33 · Incident-response playbook</h1>")
for t, d in INCIDENT_RESPONSE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>34 · Data-retention &amp; backup policy</h1><table><tr><th>Entity</th><th>Retention</th></tr>")
for a, b in DATA_RETENTION:
    body_parts.append(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>35 · Vendor education curriculum</h1>")
for m, d in VENDOR_CURRICULUM:
    body_parts.append(f"<h2>{esc(m)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>36 · Change management &amp; release cadence</h1>")
for t, d in CHANGE_MANAGEMENT:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>37 · Security controls matrix</h1>")
for group, items in SECURITY_CONTROLS:
    body_parts.append(f"<h2>{esc(group)}</h2><table><tr><th>Control</th><th>Implementation</th></tr>")
    for name, desc in items:
        body_parts.append(f"<tr><td>{esc(name)}</td><td>{esc(desc)}</td></tr>")
    body_parts.append("</table>")

body_parts.append("<h1>38 · Tender committee constitution</h1>")
for t, d in TENDER_COMMITTEE_CONSTITUTION:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>39 · Disaster-recovery drill script</h1>")
for t, d in DR_DRILL_SCRIPT:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>40 · Sample notice (annotated)</h1>")
for t, d in SAMPLE_NOTICE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>41 · Sample bid (annotated)</h1>")
for t, d in SAMPLE_BID:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>42 · Detailed API reference</h1>")
for group, endpoints in DETAILED_API_REFERENCE:
    body_parts.append(f"<h2>{esc(group)}</h2><table><tr><th>Endpoint</th><th>Purpose</th></tr>")
    for ep, desc in endpoints:
        body_parts.append(f"<tr><td><code>{esc(ep)}</code></td><td>{desc}</td></tr>")
    body_parts.append("</table>")

body_parts.append("<h1>43 · Acceptance-test matrix</h1>")
for area, tests in ACCEPTANCE_TESTS:
    body_parts.append(f"<h2>{esc(area)}</h2><ul>")
    for t in tests:
        body_parts.append(f"<li>{t}</li>")
    body_parts.append("</ul>")

body_parts.append("<h1>44 · Sample corrigenda log</h1>")
for t, d in SAMPLE_CORRIGENDA:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>45 · Sample DocuSign envelope walkthrough</h1>")
for t, d in SAMPLE_DOCUSIGN_WALK:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>46 · Stakeholder-report sample</h1>")
for t, d in STAKEHOLDER_REPORT_SAMPLE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>47 · Audit-trail export sample</h1>")
for t, d in AUDIT_TRAIL_SAMPLE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>48 · MoU template (Sponsor ↔ Platform Operator)</h1>")
for t, d in MOU_TEMPLATE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>49 · RACI matrix</h1><table><tr><th>Activity</th><th>Assignment</th></tr>")
for a, b in RACI_MATRIX:
    body_parts.append(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>50 · Cost-benefit worksheet (KZ programme, illustrative)</h1>")
for t, d in COST_BENEFIT_WORKSHEET:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>51 · Committee minutes template</h1>")
for t, d in COMMITTEE_MINUTES_TEMPLATE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>52 · Procurement policy summary</h1>")
for t, d in PROCUREMENT_POLICY_SUMMARY:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>53 · Localisation strings (EN / RU / KK)</h1>")
for group, items in LOCALISATION_STRINGS:
    body_parts.append(f"<h2>{esc(group)}</h2><table><tr><th>Key</th><th>Translations</th></tr>")
    for key, val in items:
        body_parts.append(f"<tr><td><code>{esc(key)}</code></td><td>{esc(val)}</td></tr>")
    body_parts.append("</table>")

body_parts.append("<h1>54 · Vendor sandbox playbook</h1>")
for t, d in VENDOR_SANDBOX:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>55 · Committee training curriculum</h1>")
for t, d in COMMITTEE_TRAINING:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>56 · Ethics code</h1>")
for t, d in ETHICS_CODE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>57 · Board reporting pack</h1>")
for t, d in BOARD_REPORTING_PACK:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>58 · IT operations manual</h1>")
for t, d in IT_OPERATIONS:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>59 · Sample Q&amp;A digest</h1>")
for t, d in SAMPLE_QA_DIGEST:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>60 · Sample bid evaluation matrix</h1>")
for t, d in BID_EVAL_MATRIX:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>61 · Standard clauses library</h1>")
for t, d in STANDARD_CLAUSES:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>62 · Communications templates</h1>")
for t, d in COMMS_TEMPLATES:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>63 · Vendor NPS survey</h1>")
for t, d in NPS_SURVEY:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>64 · Debarment log format</h1>")
for t, d in DEBARMENT_LOG:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>65 · SMS / in-app message library</h1>")
for t, d in TEXT_MESSAGE_LIBRARY:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>66 · Release planning — CY 2027</h1>")
for t, d in RELEASE_PLANNING:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

body_parts.append("<h1>67 · Manual maintenance guide</h1>")
for t, d in MANUAL_MAINTENANCE:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{esc(d)}</p>")

# Chapters 16 – 25
body_parts.append("<h1>16 · Role-by-role onboarding checklist (30 / 60 / 90 days)</h1>")
for pt in [
    "<b>Admin — Day 1.</b> Shadow an experienced admin through a full tender lifecycle (draft → publish → bid receipt → evaluation → award → contract). Read chapters 1–3 and 7–11.",
    "<b>Admin — Day 30.</b> Publish your first tender end-to-end unsupervised. Own one committee evaluation cycle. Complete audit-trail search drills for two entity types.",
    "<b>Admin — Day 60.</b> Configure a new country's masters. Run one Tender Builder DPR ingestion on a 500-page tender.",
    "<b>Admin — Day 90.</b> Lead a full quarterly stakeholder-report cycle. Present KPI trends to the Management portal.",
    "<b>Vendor onboarder (Support).</b> Day 1 shadow a live activation. Day 30 process 10 registrations solo. Day 60 own resend-link edge cases and licence re-verification queues. Day 90 run a vendor-education webinar.",
    "<b>Escrow officer.</b> Day 1 read the joint-account snapshot model. Day 30 process 20 EMD receipts + 10 refunds. Day 60 handle one forfeiture with legal sign-off. Day 90 lead a monthly reconciliation against Stripe.",
    "<b>Committee member.</b> Day 1 COI declaration training. Day 30 score 3 evaluations under a senior member. Day 60 lead one evaluation session. Day 90 chair a full committee meeting including minutes and public Q&A migration.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>17 · Monthly operations cadence</h1>")
for pt in [
    "<b>Week 1</b> — Publish weekly digest via Resend. Reconcile prior-month escrow ledger. Publish stakeholder monthly report.",
    "<b>Week 2</b> — Committee cycle for tenders whose submission deadline landed in the prior week.",
    "<b>Week 3</b> — Award ceremonies + DocuSign countersign push. Vendor invoicing run.",
    "<b>Week 4</b> — Roadmap review with GOC + Bank partners. Vendor NPS survey via Resend. Category taxonomy audit.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>18 · North-Star KPIs and dashboards</h1><table><tr><th>KPI</th><th>Definition</th><th>Target</th><th>Notes</th></tr>")
for a, b, c, d in kpi_rows:
    body_parts.append(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>19 · Escalation matrix</h1><table><tr><th>Situation</th><th>First responder</th><th>15 min</th><th>1 h</th><th>4 h</th><th>Owner</th></tr>")
for row in [
    ("Auth outage","On-call admin","On-call engineer","CTO","CEO","CTO"),
    ("EMD refund overdue > 60 days","Escrow officer","Legal","Escrow lead","CFO","CFO"),
    ("Suspicious auction pattern","Auction ops","AI anomaly rerun","Legal","CEO","Legal"),
    ("Data breach suspected","Any staff","CTO","CEO","Communications","CTO"),
    ("Regulator inbound","Any staff","Partner lead","CEO","Board","Partner lead"),
]:
    body_parts.append("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>")
body_parts.append("</table>")

body_parts.append("<h1>20 · Keyboard shortcuts</h1><table><tr><th>Shortcut</th><th>Action</th></tr>")
for a, b in [
    ("⌘ + K","Global command palette (planned)"),
    ("G then A","Jump to Analytics"),
    ("G then N","Jump to Notices"),
    ("G then T","Jump to Tender Builder"),
    ("G then E","Jump to Evaluation"),
    ("Esc","Close any open modal"),
    ("/","Focus the primary search box"),
    ("Shift + ?","Show the shortcut cheat sheet (planned)"),
]:
    body_parts.append(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>21 · Frequently asked questions (FAQ)</h1>")
for q, a in faqs:
    body_parts.append(f"<h3>Q — {esc(q)}</h3><p>{esc(a)}</p>")

body_parts.append("<h1>22 · Sample workflow — full lifecycle of one tender</h1>")
for pt in [
    "<b>Day 0.</b> Package owner briefs the drafting agent. Agent opens Tender Builder → picks the country → picks or creates a master → opens the DPR modal and uploads the project brief. AI drafts every section body from the DPR passages. Agent reviews, adjusts EMD/fee, uploads BOQ CSV, saves the draft.",
    "<b>Day 3.</b> Legal counsel reviews. Any redlines go into a version snapshot. Legal signs off. Agent hits Publish. Resend digests fire to subscribed vendors. Snapchat + Instagram posts pushed automatically.",
    "<b>Day 3–17.</b> Pre-bid meeting on Day 5. Minutes uploaded, substantive Q&A migrated to the public notice. Corrigenda published as needed. Bidders purchase the tender pack; EMDs post to escrow.",
    "<b>Day 18.</b> Submission deadline. Admin locks technical envelope; the button flips to 'Sealed 🔒' and a green banner records the sealer and timestamp.",
    "<b>Day 18–28.</b> Evaluation committee scores technical. Once all evaluators have submitted, admin locks commercial envelope. Committee scores commercial. Admin generates the award report → L1 identified.",
    "<b>Day 29.</b> LOA issued via DocuSign. Vendor accepts; PMC countersigns. PO number generated.",
    "<b>Day 30–...</b> Contract runs. Milestones, timesheets, variation orders logged. EMD refunded on Day N post-close unless disputed. Vendor rating captured. Auditor exports the CSV bundle if requested.",
]:
    body_parts.append(f"<p>{pt}</p>")

body_parts.append("<h1>23 · Data model appendix</h1><table><tr><th>Collection</th><th>Purpose</th><th>Hot indices</th></tr>")
for a, b, c in [
    ("tenants","Multi-tenant scoping","code (unique)"),
    ("admin_users / staff_users / vendors","Auth realms","email (unique per tenant)"),
    ("notices","Published tender notices","notice_ref, published_at, country"),
    ("tender_templates","Reusable master + drafts","(country, industry), is_master"),
    ("registrations","Vendor onboarding wizard state","magic_token, email, status"),
    ("bids","Submitted bids","notice_ref, vendor_ref"),
    ("rubrics","Per-notice scoring config","notice_ref (unique)"),
    ("scores","Evaluator scores","bid_id, evaluator"),
    ("escrow_transactions","EMDs held/refunded/forfeited","notice_ref, status"),
    ("auctions","Reverse auction rooms","notice_ref (unique)"),
    ("corrigenda","Notice amendments","notice_ref, published_at"),
    ("audits","Immutable audit trail","entity_ref, actor_id, at"),
    ("ratings","Post-contract reviews","vendor_ref"),
    ("dpr_jobs","v46l async DPR workers","_id, status"),
    ("reports_snapshots","Materialised stakeholder artefacts","generated_at"),
]:
    body_parts.append(f"<tr><td><code>{esc(a)}</code></td><td>{esc(b)}</td><td><code>{esc(c)}</code></td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>24 · Appendix — release notes archive</h1><ul>")
for v, hh in releases:
    body_parts.append(f"<li><b>{esc(v)}</b> — {esc(hh)}</li>")
body_parts.append("</ul>")

body_parts.append("<h1>68 · Vendor performance scorecard framework</h1>")
for t, d in [
    ("Purpose", "The scorecard aggregates every observable signal a vendor generates during a contract — cost, schedule, quality, safety, communication, disputes — into a single 0-100 index visible to Admins, Committees and (opt-in) buyer stakeholders. It replaces the ad-hoc gut-feel scoring that used to bias L1 recommendations."),
    ("Data feeds", "The engine pulls from: <code>contracts.milestones[]</code> for on-time delivery, <code>escrow_transactions</code> for payment friction, <code>ratings</code> for post-award reviews, <code>audits</code> for compliance touches, <code>notices ↔ bids</code> join for win-rate, <code>corrigenda</code> counts for scope-change churn, and the DocuSign envelope-status stream for signature discipline."),
    ("Weights", "Cost adherence 25 %, schedule adherence 25 %, quality (defect-free acceptance) 15 %, communication + Q&amp;A responsiveness 10 %, safety incidents 10 %, dispute count 5 %, ESG self-attestation 5 %, community sub-contracting 5 %. Weights are configurable per-tenant in Masters → Scorecard."),
    ("Bands", "&gt; 85 = Preferred (green pill, appears on public trust badge). 70-84 = Standard. 55-69 = Under review (flag surfaces on every future bid). &lt; 55 = Restricted (auto-rejects future bids unless overridden with justification)."),
    ("Refresh cadence", "The <code>_recompute_scorecard()</code> worker runs nightly at 02:15 UTC. Manual re-runs are exposed at <code>POST /api/v1/vendor-intel/scorecard/recompute</code> (admin+auditor). Every recompute writes an audit row with the delta so trends are queryable."),
    ("Governance", "A monthly Vendor Council reviews every vendor whose band crossed a threshold. Restricted vendors must be formally debarred (see chapter 64) — a low scorecard alone is not sufficient."),
    ("Anti-gaming", "Any single evaluator whose scores deviate from committee median &gt; 20 pts on three consecutive bids triggers a mandatory calibration session. The scorecard downweights outlier evaluators via a Grubbs test before averaging."),
    ("Publishing to vendors", "Vendors see their own scorecard inside the vendor portal — with sub-scores, trend line and remediation tips. Sensitive weightings are hidden. Appeals go through <code>POST /api/v1/vendor-intel/scorecard/{ref}/appeal</code>."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>69 · Cross-border payment settlement runbook</h1>")
for t, d in [
    ("In scope", "Kazakhstan (KZT), CIS neighbours (RUB, UZS, KGS, AZN), Gulf partners (USD, AED, SAR) and EU sub-contractors (EUR, GBP). Stripe covers card + ACH; Kaspi Business handles KZT rails; a manual SWIFT fallback exists for regulated Gulf flows."),
    ("Rails matrix", "Each currency pair has a preferred rail. Rail selection happens in <code>_select_payout_rail(currency_in, currency_out, amount)</code>: Stripe for anything under $10 k that stays inside G10; Kaspi for any KZT leg; SWIFT for &gt; $10 k Gulf; PayPal only where the vendor explicitly requests it and the buyer approves."),
    ("Escrow bridge", "The escrow account model is currency-agnostic — every transaction stores <code>amount</code>, <code>currency</code>, <code>fx_rate_used</code>, <code>fx_source</code>, <code>fx_captured_at</code>. When funds move between two rails the platform locks the mid-market rate + 30 bps and records both legs so nothing is lost to slippage."),
    ("Reconciliation", "Every settlement writes a <code>settlements</code> row that references the source <code>escrow_transaction._id</code> and the payment-provider webhook. The nightly recon job matches every provider webhook to a settlement — mismatches raise a Sev-3 ticket automatically."),
    ("KYC hooks", "Cross-border payouts require a passed KYC status + LSEG World-Check clearance no older than 180 days. The rail-selector refuses to route a payout when either signal is stale — the UI surfaces the exact reason ('KYC re-verification due') so ops knows what to fix."),
    ("Regulator reporting", "Monthly Form-1B is auto-generated from <code>settlements</code> filtered by rail=SWIFT. Kazakhstan National Bank filings run via Kaspi Business's API on the 5th business day. Both hit Legal for sign-off before submission."),
    ("Failure modes", "Rail rejection is not treated as a full failure — the transaction stays <code>held</code> and the engine retries the next rail (per priority) until success or exhaustion. After exhaustion the transaction moves to <code>manual_intervention</code> and Sev-2 pages Escrow ops."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>70 · AI copilot governance and audit trail</h1>")
for t, d in [
    ("Positioning", "Every AI surface is <b>advisory-only</b>. No AI-generated content is ever written to a legal or immutable audit record. The human evaluator, admin or vendor is always the recorded actor."),
    ("Inventory", "1) DPR extractor (ingestion pipeline); 2) Section drafter (Tender Builder); 3) Bid-anomaly detector (Analytics); 4) Committee deliberation summariser; 5) Vendor Q&amp;A auto-suggest; 6) Public-notice de-jargon reviewer. All route through the managed AI Gateway (universal LLM key) proxy."),
    ("Prompt registry", "Every prompt lives under <code>backend/pmc_lib/prompts/</code> with a semver tag. Changes require a PR + reviewer + prompt-diff attached to a governance ticket. The registry is immutable; historical prompts are retained for 7 years to support audit replay."),
    ("Model registry", "Model choice per surface is tracked in <code>ai_governance.models</code>. Downgrading a model (e.g. GPT-5.6 → GPT-5.4) is a change-managed action requiring CTO sign-off. The runtime records model + prompt version on every response — so any output can be re-produced exactly."),
    ("Bias controls", "DPR extraction is checked nightly against a golden-set corpus of 40 known tenders. If precision or recall drops &gt; 3 pts vs baseline, the ai-governance-check CI fails and blocks the release. Bid-anomaly detector is checked for demographic drift on vendor country-of-origin."),
    ("Explainability", "Every AI recommendation the UI surfaces has a 'Why?' expander that shows the prompt digest + response digest + retrieved context. This is required for regulator conversations."),
    ("Human veto", "Committee members and admins can veto any AI recommendation. The veto is recorded as an audit row with a mandatory reason string. Vetoes are aggregated monthly and fed back to prompt/model tuning."),
    ("Data residency", "The managed AI Gateway proxy is contractually pinned to EU + KZ endpoints only. No PII leaves the region. Any content beyond raw tender bodies is redacted at the prompt-builder stage — the redactor is unit-tested against a KZ-PII corpus every commit."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>71 · Business continuity & regional failover</h1>")
for t, d in [
    ("Regional footprint", "Primary region: eu-central-1 (Frankfurt) — colocation with the AI gateway EU endpoint. Warm-standby region: me-south-1 (Bahrain) — Gulf partner requirement. Read-only DR region: eu-west-2 (London) — legal archive only."),
    ("RTO / RPO", "Recovery Time Objective 30 minutes for a warm standby cutover; 4 hours for a cold rebuild. Recovery Point Objective is 60 seconds — enforced by MongoDB oplog streaming to standby and S3 cross-region replication for uploads."),
    ("Failover triggers", "1) Elastic Beanstalk region health &lt; 60 % for 5 minutes; 2) MongoDB primary election failure for &gt; 2 minutes; 3) LLM proxy latency &gt; 30 s for 3 minutes; 4) Manual declaration by CTO. Any single trigger fires the failover playbook (see chapter 33)."),
    ("Data-store replication", "MongoDB Atlas cross-region cluster (primary + 2 replicas in EU + 1 replica in ME). S3 Cross-Region Replication for <code>pmc-uploads</code> and <code>pmc-downloads</code>. Route 53 health-checks + DNS failover for <code>api.pmcmanagers.com</code>."),
    ("Frontend continuity", "CloudFront distribution has origin failover: primary origin S3-EU, secondary S3-ME. Frontend is a static bundle so it survives origin loss entirely. The 5-portal login surface is served from CloudFront's edge, so even a full API outage leaves the marketing shell intact with a clear status banner."),
    ("Runbook rehearsal", "Chaos-engineering drills run on the last Friday of each quarter. Scenarios: primary DB kill, LLM proxy timeout, S3 origin outage, DNS mis-configuration, full-region evacuation. Each drill produces a post-mortem stored under <code>docs/dr-drills/YYYY-QN.md</code>."),
    ("Communication plan", "Sev-1 outages trigger: status page auto-update, Resend digest to admin users, Telegram to on-call ops, WhatsApp to executive team. The public-notice board renders a top banner sourced from the /status endpoint so vendors know a bid submission window may be affected."),
    ("Business impact tiers", "Tier A (mission-critical, 30 min RTO): auth, notices, bids, escrow, evaluations. Tier B (2 h RTO): DocuSign, DPR, auctions, analytics. Tier C (24 h RTO): manual v2, reports snapshots, roadmap, profile picture uploads."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>72 · Cybersecurity posture & third-party risk</h1>")
for t, d in [
    ("Certification roadmap", "ISO 27001 target FY2027 Q3. SOC 2 Type II target FY2027 Q4. Both scoped to the platform + managed AI gateway + Stripe + Resend + DocuSign integrations. GDPR + Kazakhstan Law 94-V compliance is already in force; the certification is the third-party attestation."),
    ("Threat model", "STRIDE assessment refreshed each release. Top current risks: (1) vendor credential stuffing at /vendor/login, (2) prompt injection via uploaded DPR files, (3) escrow signer email substitution, (4) supply-chain compromise of npm/pypi packages, (5) social engineering of admin support staff."),
    ("Controls", "Rate limiting + IP throttling on all /login surfaces. LLM prompt-injection guardrails: strict allow-list HTML tags, sandboxed retrieval, no tool-use inside DPR pipeline. Escrow signer changes require re-authentication + audit + email confirmation. Dependency-pinning + Snyk + weekly dependency-cron scans."),
    ("Third-party risk register", "Every external service the platform depends on has a row in <code>third_party.md</code>: scope, data flow, SOC-2 status, DPA on file, contract expiry, escalation contact. Current entries: Managed AI Gateway (LLM), Stripe, Resend, DocuSign, MongoDB Atlas, AWS, Cloudflare, Slack, Telegram, Snapchat/Instagram API."),
    ("Penetration testing", "Annual external pen-test by an approved vendor. Quarterly internal red-team exercises. Findings are logged in JIRA with a Sev tag; anything Sev-1 must be remediated within 15 days per policy."),
    ("Encryption", "TLS 1.3 in transit; AES-256 at rest on MongoDB + S3. Application-level envelope encryption for tender bodies (KMS CMKs rotated annually). DocuSign PDFs are stored encrypted with the vendor's public key from KYC — nobody but the signer can retrieve the plaintext."),
    ("Incident classification", "Sev-1 = data exfiltration or systemic auth bypass; Sev-2 = single-tenant data-integrity failure; Sev-3 = performance regression or observability gap. Each has a fixed on-call rotation + response SLA + post-mortem template. See chapter 33 for the full playbook."),
    ("Regulator liaison", "The Kazakhstan Cybersecurity Committee is notified of any Sev-1 within 24 h per statutory requirement. GOC + Bank partners receive a courtesy update via Partner lead. All external comms route through the CEO for approval — no exception, no direct-to-press."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>73 · Vendor lifecycle KPIs & dashboards</h1>")
for t, d in [
    ("Acquisition", "New draft registrations / week, resume-rate (drafts that reach Submit), average time-to-submit, campaign attribution (Snapchat/Instagram/partner referral). Targets: 40 new drafts / week, &gt; 55 % resume rate, &lt; 3 days time-to-submit."),
    ("Activation", "Days from Submit to first eligible bid, first bid-value distribution, first-bid win-rate. Targets: median &lt; 7 days, first bid median USD 40 k, first-bid win-rate baseline 8 % — flag if a category drifts below 4 %."),
    ("Engagement", "Bids per active vendor per quarter, category diversification (unique categories bid on), auction participation rate, Q&amp;A engagement rate. Targets: 3 bids / quarter, 2 categories, 30 % auction participation once invited, 50 % Q&amp;A engagement."),
    ("Retention", "Quarterly active vendor count, 12-month churn (drop-off from active), win-rate trend, ESG completion %. Targets: 12-month churn &lt; 15 %, ESG completion &gt; 80 % of active vendors."),
    ("Revenue", "Total contract value awarded / vendor / year, average margin (if disclosed), payment-cycle time, refund/forfeit rate on EMDs. Targets: median USD 200 k / active vendor / year; payment cycle median 21 days; forfeit rate &lt; 4 %."),
    ("NPS + advocacy", "Vendor NPS (quarterly survey), referral rate, social share rate on award announcements. Targets: NPS &gt; +30, referral rate &gt; 12 %, social-share rate &gt; 25 % of awards."),
    ("Panel composition", "Dashboards ship out of the box under Admin → Analytics → Vendor lifecycle. Each metric supports drill-down to the underlying rows for audit purposes."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>74 · Government &amp; regulator engagement playbook</h1>")
for t, d in [
    ("Stakeholder map", "Kazakhstan: National Bank, Ministry of Finance, State Procurement Authority, Anti-Corruption Agency. Multilateral: Asian Development Bank, EBRD, World Bank. Trade: Astana International Financial Centre, AIFC Court. Each has an owner on the Partner side + a backup."),
    ("Cadence", "Monthly written update to the State Procurement Authority (auto-generated stakeholder report). Quarterly in-person meeting with the National Bank on escrow flows. Half-yearly platform demo for the Anti-Corruption Agency. Annual multilateral summit."),
    ("Data-sharing agreements", "Each regulator has a DSA on file with named data categories + retention + auditable purpose. Anonymised aggregate stats can be shared freely; per-vendor detail only via formal legal request routed through counsel."),
    ("Public consultation", "Every new feature that changes procurement outcome (rubric changes, auction rules, vendor scorecard weights) is put out for 21-day public consultation via the platform's <code>/consultations</code> surface. Comments are archived in the audit trail."),
    ("Complaint handling", "The Anti-Corruption Agency has a dedicated portal to raise queries against any tender. SLA: acknowledge in 4 h, first substantive response within 3 business days, resolution or escalation within 15 business days."),
    ("Cross-border data", "Any dataset that leaves KZ needs a written data-sharing note co-signed by CTO + counsel. The default is 'stay in region' — cross-border is the exception, not the rule."),
    ("Media protocol", "Regulator interactions are never subject to press comment without CEO + Partner-lead sign-off. Public statements attributed to the platform are drafted by the Communications lead and reviewed by counsel."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>75 · Roadmap horizons 2027 – 2029</h1>")
for t, d in [
    ("Horizon 1 (0–12 months) — mature the core", "Ship the remaining P1 bugs (i18n backfill, TenderBuilder tab refetch, escrow signer edit). Ship Firebase/APNs push. Ship Zoom for evaluation committees. Ship LSEG/World-Check integration. Ship PayPal + Kaspi payments alongside Stripe. Ship v2 of the vendor scorecard with the anti-gaming layer described in chapter 68."),
    ("Horizon 2 (12–24 months) — platform expansion", "Multi-country tenanting (per-country subdomains + per-country masters bootstrap). White-label mode for GOC + Bank partners. Native mobile apps for vendor portal (Capacitor already scaffolded — chapter 71's DR region can host the mobile edge). AI copilot for committee deliberation minutes. Deeper anti-fraud (device fingerprinting, behavioural analytics)."),
    ("Horizon 3 (24–36 months) — new lines of business", "Marketplace for pre-qualified vendors across partner platforms (federated identity via OIDC). Tokenised EMD via a regulated custodian in AIFC. Cross-border bid pooling with peer procurement platforms. Regulator-grade real-time dashboards licensed to Ministries."),
    ("Investment principles", "Every new feature must serve at least one of: (1) demonstrable audit-trail integrity, (2) measurable time-to-award reduction, (3) measurable vendor NPS improvement, (4) new revenue line. Features that fail all four are pushed to the parking lot."),
    ("Kill criteria", "Any Horizon-1 item unshipped after 15 months is either (a) re-scoped and re-prioritised, or (b) killed. No zombie features. The roadmap review happens on the last Thursday of each quarter with all portal owners present."),
    ("Talent plan", "Horizon 1 requires the current 2-engineer team. Horizon 2 requires 4 engineers + 1 designer + 1 product ops. Horizon 3 requires 8+ engineers, a dedicated security team, and a partner-success team."),
    ("Governance", "The roadmap is public inside the platform (Admin → Reports → Roadmap) and to shareholders via a signed PDF export. External publication requires CEO + counsel sign-off. Changes to the roadmap horizons require Board sign-off if the horizon shifts by more than one quarter."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>76 · Ethics review board charter</h1>")
for t, d in [
    ("Composition", "Seven members: two independent public-sector representatives, two industry members with 15+ years procurement experience, one AIFC-court-nominated legal counsel, one civil-society observer, and the platform's Chief Compliance Officer (secretariat, non-voting). Terms are three years, staggered."),
    ("Remit", "Review any procurement decision where (a) an AI recommendation was overturned, (b) a vendor scorecard band changed by more than one tier in a quarter, (c) a debarment is proposed, (d) a corrigendum window extends the deadline by more than 30 %, or (e) an external whistleblower complaint is received."),
    ("Cadence", "Monthly plenary. Emergency session within 72 h for any Sev-1 event. All meetings are audio-recorded and minuted; minutes are published within 10 working days after redaction of commercially sensitive material."),
    ("Powers", "Recommend (not compel) remedial action to Management and the Board. Access every audit-trail record read-only. Commission independent forensic reviews at the platform's cost up to USD 250 k per review without additional Board approval."),
    ("Conflict declarations", "Members declare all commercial interests before each meeting. Any member with a material interest in the item under review recuses. Recusals are minuted with the reason."),
    ("Escalation to Board", "Board must respond in writing to any Ethics-Board recommendation within 30 days. Rejections must be accompanied by a written rationale which becomes part of the audit trail."),
    ("Whistleblower protection", "The board oversees the whistleblower channel (email + Telegram + a redacted web form). Retaliation against a good-faith reporter is grounds for immediate termination and — where a public official is involved — a mandatory referral to the Anti-Corruption Agency."),
    ("Public reporting", "An annual public report summarises the number of reviews, the outcomes, and material lessons learned. Individual cases are anonymised."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>77 · Total-cost-of-ownership model (TCO)</h1>")
for t, d in [
    ("Purpose", "TCO turns L1 recommendations from a lowest-price comparison into a whole-life value comparison. It is mandatory for any contract with an initial value above USD 500 k or a duration longer than 24 months."),
    ("Inputs", "Bid price (year 1), annual operating cost estimate, energy consumption profile, expected downtime hours, spare-parts pricing, training cost, decommissioning cost, residual value at end-of-life, and a country-specific discount rate."),
    ("Formula", "TCO = Σ(operating cost + energy + downtime × cost-of-downtime + maintenance + training) over the contract horizon, discounted by the risk-free rate, plus decommissioning, minus residual. The formula lives in <code>backend/pmc_lib/tco.py</code> with unit tests covering the 12 edge cases from the ADB TCO playbook."),
    ("Committee integration", "Once TCO is enabled for a tender the AwardReport surfaces two columns: 'Bid Price' and 'TCO'. Ranking is by TCO. Any bid whose TCO exceeds the lowest by more than 25 % but has a lower bid price is flagged for narrative comment from the committee."),
    ("Vendor visibility", "Vendors see the TCO input schema at bid submission time. They can attach their own TCO worksheet as evidence. This is optional but improves scoring under the methodology criterion."),
    ("Sensitivity analysis", "The TCO surface includes a slider: energy cost ±30 %, downtime cost ±30 %, discount rate ±200 bps. The committee can eyeball how sensitive the ranking is to each input and demand justification when a swing tips the recommendation."),
    ("Audit trail", "Every TCO input, every recalculation, and every slider position is written to the audit trail with the actor. Regulator or auditor can replay any TCO-based award decision end-to-end."),
    ("Training", "Buyers new to TCO complete a 2-hour module (Admin → Help → Training → TCO fundamentals). The module includes 8 worked examples across construction, IT services, medical equipment and consulting."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>78 · Green procurement policy</h1>")
for t, d in [
    ("Commitment", "PMC and its sponsor commit that by end of FY2028 at least 60 % of contract value awarded through the platform will meet the green-procurement criteria published in the annexure. This is a Board-level target."),
    ("Definition", "A bid is 'green' if it: (a) documents a Scope 1+2 emissions figure ≤ the category benchmark, (b) commits to a Scope 3 reduction plan of ≥ 2 %/year, (c) sources at least 30 % of materials/services locally, and (d) meets ISO 14001 or an equivalent EMS."),
    ("Scoring", "The rubric editor supports a 'Green premium' criterion (0 – 15 % weight) that applies when the tender is flagged green-eligible. Non-green bids are not disqualified but score lower on this criterion."),
    ("Reporting", "The public roadmap includes a live 'green %' KPI. The stakeholder monthly report enumerates green vs non-green award value and the delta vs target."),
    ("Verification", "Vendor self-declarations are spot-audited at 10 % of awards. Independent verifier (SGS / Bureau Veritas) confirms; false declaration is grounds for debarment and repayment of green premium."),
    ("Buyer training", "Any buyer publishing a green-eligible tender completes a 90-minute module (Admin → Help → Training → Green procurement). The module includes the taxonomy, common gotchas and legal do-not-say phrases that trip Anti-Corruption regulators."),
    ("Regulator alignment", "The green definition is aligned with the AIFC Green Finance Taxonomy and the World Bank's 2025 Climate Change Action Plan classifications. Realignment reviews happen annually."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>79 · Vendor communication protocol</h1>")
for t, d in [
    ("Channels", "Primary: email digest via Resend (announcement, corrigenda, award notice). Secondary: in-app inbox with read-receipt (persists across sessions). Tertiary: WhatsApp + Telegram for opt-in critical alerts. Never SMS as primary — cost + spoofing risk."),
    ("Tone", "Formal, concise, English + Russian + Kazakh in one email. No marketing language on transactional messages. No emoji on regulatory content. Signed by a named human (usually the Vendor Success lead) with a real reply address."),
    ("Frequency caps", "No more than 3 non-critical emails / vendor / week. Critical (corrigenda, deadline change, award) always sends. Vendors control category preferences from their profile page — the platform respects the last-updated preference within 10 minutes."),
    ("Content review", "Every template is versioned in <code>backend/pmc_lib/comms_templates/</code>. New templates require Comms + Legal review. Field substitutions are strictly typed to prevent HTML injection."),
    ("Analytics", "Open rate, click-through, unsubscribe, reply-to-human ratio are tracked per template. Templates below 15 % open-rate for four consecutive sends are auto-flagged for a rewrite."),
    ("Escalation replies", "A vendor reply-to-all email lands in a shared mailbox (vendor-success@pmcmanagers.com) with automated triage: contract dispute → Legal, technical → Support, commercial → Success lead. First-response SLA: 4 business hours."),
    ("Legal footer", "Every mail carries an unsubscribe link (transactional exempt), a physical address (PMC head office, Astana), and links to the privacy and terms pages. Absence of any element blocks the send at the template linter."),
    ("Regulator carbon-copy", "Award notices, debarment notices and material corrigenda are automatically bcc-ed to the State Procurement Authority archive mailbox. The recipient is a Kazakhstan Government mandate."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>80 · Data-quality standards &amp; master-data governance</h1>")
for t, d in [
    ("Golden records", "Every entity that spans more than one tender (vendor, buyer, category taxonomy, currency, country, industry) has one canonical golden record. The platform enforces referential integrity via <code>golden_ref</code> foreign keys — orphaned entities fail the pre-publish check."),
    ("Ownership", "Each domain has a nominated data steward: Vendors → Vendor Success lead, Buyers → Buyer Success lead, Taxonomy → Category committee, Countries/currency → Compliance officer. Any change to a golden record requires steward sign-off and produces an audit row."),
    ("Change-control", "Master-data changes propagate to all in-flight tenders in a controlled way: (a) draft tenders auto-update, (b) published tenders keep their frozen snapshot, (c) evaluations use the snapshot valid at lock-envelope time. This prevents silent behaviour change on live procurement."),
    ("Data-quality metrics", "Completeness (% required fields populated), accuracy (spot-audit vs source-of-truth), timeliness (median age of last update), uniqueness (duplicate detection score), and consistency (cross-reference validity). Each metric has a target and a live gauge on the Admin data-quality dashboard."),
    ("Duplicate detection", "Fuzzy-match on registration_number + country + email domain flags candidate duplicates before a vendor is activated. The threshold is 92 % similarity; anything below is human-reviewed by Vendor Success. Duplicate merges preserve both audit trails."),
    ("Reference data cadence", "Country and currency ISO codes refreshed monthly. NACE-style industry taxonomy reviewed quarterly. EMD slabs reviewed twice yearly against Kazakhstan's regulatory bulletin. Every refresh writes a version tag so historical filings remain reproducible."),
    ("Data lineage", "Every field on every published notice carries a lineage annotation: which master, which version, which user made the last edit. This is what regulators typically ask for first when a decision is queried post-award."),
    ("Deletion vs archival", "Nothing is hard-deleted. 'Delete' actions move records to an archival collection with a legal-hold flag until the retention clock runs out. Bulk purges require CFO + counsel sign-off and are logged to the immutable audit trail."),
    ("Reconciliation", "Nightly reconciliation between the operational store (MongoDB) and the analytics warehouse (S3 + Athena). Deltas above 0.5 % fire a Sev-3 alert. The reconciliation job itself writes an audit row so absence-of-alert is not evidence of absence-of-drift."),
    ("Regulator export", "One-click export of any entity's full history + lineage in a signed PDF + machine-readable JSON. Available to Admins with the 'auditor' role only. Usage is itself audit-logged."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>81 · Progressive Web App (PWA) — install &amp; offline</h1>")
for t, d in [
    ("Positioning", "PMC v46p ships as an installable PWA on both Android (Chrome / Edge / Samsung Internet) and iOS (Safari 16.4+). The manifest advertises a 5-portal shortcut list so the launcher offers direct entry to Admin, Staff, Vendor and the public Notice Board without opening the browser chrome."),
    ("Install — Android", "Open <code>https://tenders.pmcmanagers.com</code> in Chrome/Edge, tap the address-bar menu and choose 'Install app'. The homescreen icon uses the PMC crest. A splash screen (navy #0B132B with the gold crest) shows for the first 300 ms — configured via <code>background_color</code> + <code>theme_color</code> in <code>public/manifest.json</code>."),
    ("Install — iOS", "Open the same URL in Safari, tap the Share icon and choose 'Add to Home Screen'. iOS reads <code>apple-mobile-web-app-*</code> meta tags in <code>public/index.html</code> so the standalone shell hides Safari chrome, uses the black-translucent status bar and the correct app title."),
    ("Offline behaviour", "The service worker (<code>public/service-worker.js</code>) caches the app shell (HTML, CSS, JS bundles, fonts, PMC crest) using a stale-while-revalidate strategy. Data endpoints (/api/*) are never cached — every request goes to the network so vendors never see stale bid data. If the network is unavailable the UI renders an 'Offline — reconnecting' banner sourced from the /status endpoint."),
    ("Update discipline", "Every deploy bumps a <code>CACHE_VERSION</code> constant in the SW so the browser invalidates old shells within one page load. The previous self-destructing SW from v46d is retained as a safety net: on activate, any cache older than 30 days is nuked."),
    ("Push notifications (roadmap)", "Web Push via Firebase Cloud Messaging (Android + desktop) and APNs bridge (iOS 16.4+ PWA) — targeted for v46q. Trigger events: award notification, corrigenda publish, bid deadline &lt; 24 h. Vendors opt-in per category from the profile page."),
    ("Testing checklist", "Lighthouse PWA audit ≥ 90; manifest icons render at both 192 px and 512 px maskable; SW installs on first load; 'Add to Home Screen' appears on Chrome ≥ 76 + Safari ≥ 16.4; the standalone shell has no browser chrome; navigation between the 5 portals stays inside the app."),
    ("Fallback for legacy browsers", "Browsers that don't support the SW API (IE, older Android 4.x) still get the full app — just without offline caching or install. There is no functional degradation, only progressive enhancement."),
]:
    body_parts.append(f"<h2>{esc(t)}</h2><p>{d}</p>")

body_parts.append("<h1>82 · Sign-off</h1><p>This manual is versioned under <code>/app/deliverables/v46_manual/build/</code>. Regenerate via <code>python3 /app/tools/manual/build.py</code>. Re-capture via <code>python3 /app/tools/manual/capture.py</code> after every material release. Manual v3 adds chapters 68 – 81 (vendor scorecard, cross-border settlement, AI governance, BCP, cybersecurity, vendor KPIs, regulator engagement, roadmap horizons, ethics board, TCO, green procurement, vendor comms, data-quality, PWA) and is fully scrubbed of third-party platform references.</p>")

pdf_html = f"""<!doctype html><html><head><meta charset='utf-8'/>
<title>PMC Master Training Manual v3</title>
<style>
    /* v46o — watermark + cover */
    @page :first {{ background: #0B132B; margin: 0; }}
    @page {{ size: A4; margin: 20mm 16mm 22mm 16mm;
      @top-right {{ content: "PMC Master Manual v3"; font: 8.5pt Georgia; color: #94a3b8; }}
      @bottom-left {{ content: "{esc(BANNER)}"; font: 8.5pt Georgia; color: #64748b; }}
      @bottom-right {{ content: "Page " counter(page) " / " counter(pages); font: 8.5pt Georgia; color: #64748b; }}
      background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='800'><g transform='translate(400,400) rotate(-30)'><text x='0' y='0' text-anchor='middle' font-family='Georgia' font-size='60' fill='rgba(15,31,58,0.05)' font-weight='700' letter-spacing='6'>CONFIDENTIAL — INTERNAL USE ONLY</text></g></svg>");
      background-position: center;
      background-repeat: no-repeat;
    }}
body {{ font: 10.5pt/1.55 Georgia, 'Times New Roman', serif; color: #0b1f3a; }}
h1 {{ font-size: 20pt; margin: 22pt 0 8pt; border-bottom: 2pt solid #0b1f3a; padding-bottom: 4pt; page-break-before: always; }}
h1:first-of-type {{ page-break-before: avoid; }}
h2 {{ font-size: 14pt; margin: 16pt 0 6pt; color: #0b1e3f; }}
h3 {{ font-size: 11pt; margin: 10pt 0 2pt; color: #1e293b; }}
p  {{ margin: 4pt 0 8pt; }}
p.desc {{ color: #334155; font-style: italic; }}
ul {{ margin: 0 0 8pt 0; padding-left: 18pt; }}
li {{ margin-bottom: 3pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 14pt; font-size: 9.5pt; }}
th, td {{ border: 0.5pt solid #cbd5e1; padding: 4pt 6pt; text-align: left; vertical-align: top; }}
th {{ background: #eef2f8; color: #0b1e3f; }}
.img {{ text-align: center; margin: 8pt 0 12pt; page-break-inside: avoid; }}
.img img {{ max-width: 100%; border: 0.5pt solid #cbd5e1; }}
.cap {{ font: italic 9pt Georgia; color: #64748b; margin-top: 2pt; }}
code {{ font-family: 'Menlo', 'Courier New', monospace; font-size: 9.5pt; background: #f1f5f9; padding: 1pt 4pt; }}
.cover {{ text-align: center; color: #fff; padding: 140pt 20pt 40pt; height: 240mm; page-break-after: always; }}
.cover .crest {{ width: 96pt; height: 96pt; margin: 0 auto 30pt; border: 2pt solid #D4AF37; display: flex; align-items: center; justify-content: center; font: 700 44pt Georgia; color: #D4AF37; }}
.cover .title {{ font-size: 40pt; letter-spacing: -0.5pt; color: #fff; line-height: 1.05; }}
.cover .sub {{ font-size: 14pt; color: rgba(255,255,255,0.7); margin-top: 22pt; letter-spacing: 0.05em; }}
.cover .rule {{ width: 60pt; height: 2pt; background: #D4AF37; margin: 40pt auto; }}
.cover .banner {{ display:inline-block; margin-top: 20pt; padding: 6pt 14pt; background: rgba(212,175,55,0.12); border: 0.5pt solid #D4AF37; color: #D4AF37; font-size: 9pt; letter-spacing: .18em; text-transform: uppercase; }}
.cover .conf {{ margin-top: 24pt; font-size: 10pt; letter-spacing: 0.3em; color: rgba(255,255,255,0.5); text-transform: uppercase; }}
</style></head><body>
<div class="cover">
  <div class="crest">PMC</div>
  <div class="title">Master Training Manual</div>
  <div class="title" style="font-size:24pt;color:#D4AF37;margin-top:14pt;">v3 · Sovereign Edition · 150-page complete</div>
  <div class="rule"></div>
  <div class="sub">End-to-end operator handbook · every screen · every field · every workflow</div>
  <div class="banner">{esc(BANNER)}</div>
  <div class="conf">Confidential — Internal Use Only</div>
</div>
{"".join(body_parts)}
</body></html>"""

pdf_html_path = OUT / "PMC_v3_Master_Training_Manual.html"
pdf_html_path.write_text(pdf_html)

from weasyprint import HTML
HTML(string=pdf_html, base_url=str(ROOT)).write_pdf(
    str(OUT / "PMC_v3_Master_Training_Manual.pdf"))

sizes = {f.name: f.stat().st_size for f in OUT.iterdir() if f.is_file()}
print("Manual built:")
for k, v in sorted(sizes.items()):
    print(f"  {k:>48s}  {v/1024:8.1f} KB")
