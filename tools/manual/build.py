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
         ("Session security note", "TLS 1.3 + Emergent audit log — cite this in security reviews.")],
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
p("**AI** — Emergent LLM Universal Key routed through the integration proxy. "
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
(OUT / "PMC_v46m_Master_Training_Manual.md").write_text(md_text)

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

doc.save(OUT / "PMC_v46m_Master_Training_Manual.docx")

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
    "<b>AI</b> — Emergent LLM Universal Key routed through the integration proxy. Used for DPR ingestion (map-reduce), AI Fill All, anomaly detection and the admin copilot. v46l lifts the 800 KB cap and adds an async worker.",
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

body_parts.append("<h1>25 · Sign-off</h1><p>This manual is versioned under <code>/app/deliverables/v46_manual/build/</code>. Regenerate via <code>python3 /app/tools/manual/build.py</code>. Re-capture via <code>python3 /app/tools/manual/capture.py</code> after every material release.</p>")

pdf_html = f"""<!doctype html><html><head><meta charset='utf-8'/>
<title>PMC v46m Master Training Manual</title>
<style>
@page {{ size: A4; margin: 20mm 16mm 22mm 16mm;
  @top-right {{ content: "PMC v46m Master Manual"; font: 8.5pt Georgia; color: #94a3b8; }}
  @bottom-left {{ content: "{esc(BANNER)}"; font: 8.5pt Georgia; color: #64748b; }}
  @bottom-right {{ content: "Page " counter(page) " / " counter(pages); font: 8.5pt Georgia; color: #64748b; }}
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
.cover {{ text-align: center; padding: 90pt 0 20pt; }}
.cover .title {{ font-size: 34pt; letter-spacing: -0.5pt; color: #0B132B; }}
.cover .sub {{ font-size: 14pt; color: #64748b; margin-top: 10pt; }}
.cover .banner {{ display:inline-block; margin-top: 60pt; padding: 6pt 14pt; background: #fef3c7; border: 0.5pt solid #D4AF37; color: #78350f; font-size: 9pt; letter-spacing: .12em; text-transform: uppercase; }}
</style></head><body>
<div class="cover">
  <div class="title">PMC Managers · v46m</div>
  <div class="title">Master Training Manual</div>
  <div class="sub">End-to-end operator handbook · every screen · every field · every workflow</div>
  <div class="banner">{esc(BANNER)}</div>
</div>
{"".join(body_parts)}
</body></html>"""

pdf_html_path = OUT / "PMC_v46m_Master_Training_Manual.html"
pdf_html_path.write_text(pdf_html)

from weasyprint import HTML
HTML(string=pdf_html, base_url=str(ROOT)).write_pdf(
    str(OUT / "PMC_v46m_Master_Training_Manual.pdf"))

sizes = {f.name: f.stat().st_size for f in OUT.iterdir() if f.is_file()}
print("Manual built:")
for k, v in sorted(sizes.items()):
    print(f"  {k:>48s}  {v/1024:8.1f} KB")
