"""Build the SINGLE definitive training manual for PMC Managers v2.

Supersedes every prior manual (v1..v3.2 handbook + Screenshot Manual v1 +
observation-response docs).

For each logical module in the portal, ships FOUR consumer-specific tracks:

  1. Overview      — one-paragraph story of what the module does + who uses it
  2. Operations    — "how to use" step-by-step for trainee ops staff
  3. QA            — numbered test cases with expected outcomes + data-testids
  4. Management    — governance controls, KPIs, and reports for exec / audit

+ inline screenshot from /app/deliverables/manual_screenshots/ (where available)
+ change-log + guardrails page at the end.

Outputs:
  /app/deliverables/PMC_Master_Training_Manual_v1.docx
  /app/deliverables/PMC_Master_Training_Manual_v1.pdf  (via libreoffice --headless)
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SCREENSHOT_DIR = Path("/app/deliverables/manual_screenshots")
OUT_DOCX = Path("/app/deliverables/PMC_Master_Training_Manual_v1.docx")
OUT_PDF = Path("/app/deliverables/PMC_Master_Training_Manual_v1.pdf")

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY_SOFT = RGBColor(0x5B, 0x7B, 0xA1)
GREY = RGBColor(0x64, 0x74, 0x8B)
EMERALD = RGBColor(0x06, 0x5F, 0x46)
AMBER = RGBColor(0x92, 0x40, 0x0E)

TITLE = "PMC Managers v2 — Master Training Manual"
SUBTITLE = "Definitive edition · v1 · Operations · QA · Management"
GENERATED = datetime.utcnow().strftime("%B %d, %Y")

# --- Track colour badges ------------------------------------------------------
TRACK_STYLE = {
    "OPS":  ("#0B4F6C", "OPERATIONS TEAM · HOW TO USE"),
    "QA":   ("#7F1D1D", "QA TEAM · TEST CASES"),
    "MGMT": ("#065F46", "MANAGEMENT · GOVERNANCE · KPIs"),
}


# ============ CHAPTER CONTENT =================================================
# Each chapter dict has:
#   title, purpose, users, overview, image (filename in manifest, optional),
#   ops (list of steps), qa (list of {step, expected, testid}),
#   mgmt (list of bullets), fields (optional table rows: [name, type, note])
CHAPTERS = [
    {
        "title": "Access, Roles & Login",
        "purpose": "Understand who logs in as what and where they land.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "05_admin-login-page.png",
        "overview": (
            "PMC Managers v2 is a multi-tenant global tender platform. Every user "
            "authenticates through the same URL and lands on the console that matches "
            "their role. Cookies are HTTPOnly + CSRF double-submit for admin; vendor "
            "and public flows use short-lived resume tokens sent by email."
        ),
        "ops": [
            "Admins go to https://www.pmcmanagers.com/admin/login and enter their PMC email + password.",
            "Vendors register from the public site https://www.pmcmanagers.com/register — no admin approval needed to start a draft.",
            "Support / Auditor accounts are read-only; they see every tab but cannot mutate.",
            "If you see a 403 toast on any screen, check Masters → Permissions for your role's matrix row.",
            "Session cookies expire after 12 h of inactivity — save drafts frequently.",
        ],
        "qa": [
            {"step": "Login with wrong password 5×", "expected": "6th attempt returns HTTP 429 with lockout timer", "testid": "admin-login-submit"},
            {"step": "Login with correct credentials", "expected": "Redirects to /admin within 1 s; me endpoint returns 200 with role", "testid": "admin-login-submit"},
            {"step": "Reload page after login", "expected": "Session persists via HTTPOnly cookie; no re-auth needed", "testid": "admin-topbar"},
        ],
        "mgmt": [
            "Nine role types shipped: Admin, Reviewer, Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor.",
            "Access-control merges Permissions Matrix + Hierarchy Level via GET /api/v1/permissions/effective/{role} (single source of truth).",
            "Level 0 = Admin (full write) → Level 3 = Support/Auditor (read-only).",
            "Every login is logged to `audit_log` — actor, IP, user-agent, timestamp.",
        ],
    },
    {
        "title": "Public Notice Board",
        "purpose": "External entry-point where bidders discover open tenders.",
        "users": ["Ops", "Mgmt"],
        "image": "02_public-tender-board.png",
        "overview": (
            "Public list of every published notice across every tenant. Filters by "
            "type (tender/RFP/RFQ), country, and category. Deep-links to the notice "
            "detail page with document downloads + QA thread + register-to-bid CTA."
        ),
        "ops": [
            "Vendors browse notices without login.",
            "Clicking a card opens the notice detail: description, deadline, downloads, corrigenda list.",
            "The 'Register interest' CTA takes vendors to /register with the notice pre-filled.",
        ],
        "qa": [
            {"step": "Load /notices with no filters", "expected": "Only notices where is_published=true render", "testid": "public-notice-card"},
            {"step": "Filter by country", "expected": "List narrows within 300ms; count updates", "testid": "public-notice-filter-country"},
            {"step": "Click a notice card", "expected": "Detail page renders; downloads work; QA thread loads", "testid": "public-notice-card"},
        ],
        "mgmt": [
            "Draft notices are never surfaced publicly.",
            "Every notice has: budget_amount (validated ≥ 0), budget_currency, delivery_country, submission_deadline.",
            "KPI: median time-to-first-bid per notice — surfaced in Stakeholder Reports / Tenders.",
        ],
    },
    {
        "title": "Vendor Registration & KYC",
        "purpose": "5-section wizard that captures identity, structure, financials, docs, references.",
        "users": ["Ops", "QA"],
        "image": "03_vendor-registration-—-start.png",
        "overview": (
            "Vendors self-register through the 5-section wizard (A Identity, B Structure, "
            "C Financials, D Documents, E References). As soon as any field is filled, a "
            "silent draft is created + a resume-link is emailed. Vendors can pause and come "
            "back to /register/status with the resume token."
        ),
        "ops": [
            "Section A: company name, contact, email, phone, country (all required).",
            "Sections B-D can be paused — the resume link is sent after Section A.",
            "Section E supports up to 3 references; each reference generates its own reachback email once approved.",
            "Nudge Stale Drafts (admin) — sends a follow-up mail to any draft untouched for 14 days.",
        ],
        "qa": [
            {"step": "Fill Section A and close the tab", "expected": "Resume email arrives within 30s; token is a URL-safe 24-char string", "testid": "reg-section-a"},
            {"step": "Paste an invalid resume token at /register/status", "expected": "Toast: 'Token invalid or expired — request a new resume link…' (Bug 7 fix)", "testid": "status-token"},
            {"step": "Upload a 15 MB PDF to the KYC slot", "expected": "Upload progresses; if server limit is 10 MB, backend returns HTTP 413 with clear message", "testid": "reg-upload-kyc"},
        ],
        "mgmt": [
            "GDPR-compliant: KYC docs stored server-side with tenant-scoped ACL.",
            "KPI: draft-to-submitted conversion rate — surfaced in Stakeholder Reports / Vendors funnel.",
            "Rejected registrations get a reason ≥5 chars logged to audit; rejection email carries the reason.",
        ],
    },
    {
        "title": "Registrations Admin",
        "purpose": "Review incoming vendors, approve / reject / clarify with reason.",
        "users": ["Ops", "Mgmt"],
        "image": "07_registrations.png",
        "overview": (
            "Admin-side triage of every submitted vendor registration. Sorted oldest-first "
            "by default so the daily workflow chews through the pipeline. Every action "
            "requires a reason capture and is logged to audit."
        ),
        "ops": [
            "Sort by 'Submitted date' (default, oldest first) to work the queue.",
            "Click a row → review each section → Approve / Reject / Request Clarification.",
            "Reject or Clarify require a reason ≥5 chars — surfaced to the vendor in the outbound email.",
            "Bulk Invite CSV supports pre-loading known vendors; sample CSV downloadable from the modal.",
        ],
        "qa": [
            {"step": "Approve a vendor with a valid PAN doc", "expected": "vendor doc created + welcome email sent; row moves to 'Approved' tab", "testid": "reg-row-approve"},
            {"step": "Nudge Stale Drafts", "expected": "Three-branch toast: 'no drafts' / 'none stale' / 'n emails sent'", "testid": "reg-nudge-stale"},
            {"step": "Upload malformed CSV to Bulk Invite", "expected": "Backend returns per-row error array; other rows still succeed", "testid": "vendors-bulk-invite-csv"},
        ],
        "mgmt": [
            "Aging report: rows show submission date; daily digest highlights >30-day drafts.",
            "Every approval is a matrix action (create) — restricted per role.",
            "KPI: median approval turnaround per tenant, exposed in Stakeholder Reports.",
        ],
    },
    {
        "title": "Notices Admin",
        "purpose": "Create, publish, filter and manage every tender / RFP / RFQ.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "09_notices.png",
        "overview": (
            "The single source of truth for a live tender. Notices link to a Tender Builder "
            "template, drive the public notice board, and gate every downstream flow (bids, "
            "escrow, awards). Reviewers save drafts; only Master Admin publishes."
        ),
        "ops": [
            "'+ New notice' opens the wizard: Title, Description, Category, Country, Deadline.",
            "Pick a Tender Builder template to prefill; toggle 'Publish immediately' (Master Admin only).",
            "Use the filter bar: search by title/ref, filter by status (any/published/draft/expired), toggle 'Template-linked only'.",
            "Corrigenda re-notify bidders — you cannot delete a published notice, you must issue a corrigendum.",
        ],
        "qa": [
            {"step": "Publish a notice with budget_amount = -1", "expected": "HTTP 400 (NoticeIn validates ge=0) — Bug 4 fix", "testid": "notices-form-submit"},
            {"step": "Filter by 'Template-linked only'", "expected": "List narrows to notices with tender_template_id set", "testid": "notices-filter-template-only"},
            {"step": "Reviewer saves a draft notice", "expected": "HTTP 200; reviewer.create=True (Bug #5 fix); no 'undefined' toast", "testid": "notices-form-submit"},
        ],
        "mgmt": [
            "Every publish is audited with actor + tenant + notice_ref.",
            "Budget currency defaults to tenant primary currency but supports any ISO 4217 code.",
            "KPI: notices-published-per-month, average time from creation to publish.",
        ],
    },
    {
        "title": "Corrigenda",
        "purpose": "Formal amendments to published tenders — every change is auditable.",
        "users": ["Ops", "Mgmt"],
        "image": None,  # No dedicated screenshot; part of notices flow
        "overview": (
            "Corrigenda re-open the bidder window after a tender is public. Every corrigendum "
            "has an auto-number (`PMC-COR-YYYY-####`), a mandatory reason ≥8 chars, and can "
            "reset the submission deadline. Withdrawal is capped at 3 per notice."
        ),
        "ops": [
            "'+ New corrigendum' from Notices detail → describe the amendment.",
            "Optionally push a new deadline — bidders are notified.",
            "Withdraw requires a reason ≥8 chars.",
        ],
        "qa": [
            {"step": "Withdraw with a 3-char reason", "expected": "HTTP 400 'reason must be at least 8 characters'", "testid": "corrigenda-withdraw"},
            {"step": "Create 4th corrigendum on a notice with 3 already", "expected": "HTTP 400 'withdrawal capped at 3 per notice'", "testid": "corrigenda-create"},
            {"step": "Publish corrigendum", "expected": "audit_log entry with reason + all bidders receive email notif", "testid": "corrigenda-publish"},
        ],
        "mgmt": [
            "Legal-grade audit: reason text is preserved on the notice record + audit log.",
            "Corrigenda count is a red-flag KPI — high count on one notice indicates poor initial drafting.",
        ],
    },
    {
        "title": "Tender Builder",
        "purpose": "Compose 30-page tenders from orderable sections + annexures.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "11_tender-builder.png",
        "overview": (
            "Master templates ship for GFR 2017 QCBS 70/30. Clone a master into a draft, "
            "fill each section with the rich editor, attach annexures via drag-drop, "
            "preview + export via WeasyPrint. Every save is snapshotted (max 20 rolling)."
        ),
        "ops": [
            "Left column → pick a Kind (Tender / RFP / RFQ). Switching Kind resets the right pane (Bug 31c fix).",
            "Click a master → Clone → draft appears under 'Draft YYYY-MM-DD'.",
            "Drag annexure PDFs onto the bulk uploader — filenames auto-match (annex-VIII_bank.pdf → Annexure VIII, longest-code wins).",
            "✨ AI Draft menu: tone (formal/plain/strict) × length (short/medium/long); shows word-diff before overwriting.",
            "⟲ History drawer restores any of the last 20 snapshots (restore is itself snapshotted).",
        ],
        "qa": [
            {"step": "Save section body 3 times in a row", "expected": "Version count increments; History drawer shows all 3", "testid": "tender-section-save"},
            {"step": "Switch Kind tab after making unsaved changes", "expected": "Right pane resets; selectedId cleared (Bug 31c)", "testid": "tender-kind-tab"},
            {"step": "Export to PDF before publish", "expected": "PDF has diagonal DRAFT watermark until associated notice is_published=true", "testid": "tender-export-pdf"},
        ],
        "mgmt": [
            "Language pack: EN / RU / KK labels ship with WeasyPrint.",
            "Section-level auditor role can veto — legal counsel gets a distinct notif.",
            "KPI: average edit-cycle length; teams > 40 edits per template may need training.",
        ],
    },
    {
        "title": "Bidding Ops · Pipeline",
        "purpose": "Track every bid through the multi-role approval pipeline.",
        "users": ["Ops", "QA"],
        "image": "12_bidding.png",
        "overview": (
            "The pipeline: EMD → Escrow → Admin flag → Certifier → Legal → Accounting → "
            "Committee. Each role clears their stage; stuck bids surface in the daily "
            "audit report. Rejection at any stage requires a note."
        ),
        "ops": [
            "Filter by status (submitted/emd_paid/admin_flagged/certified/legal_cleared/accounting_ok/committee_approved/awarded/rejected).",
            "Click a bid → full timeline of every stage transition.",
            "Assign a certifier from the Assign modal; date + location required.",
            "Reject requires a note ≥10 chars.",
        ],
        "qa": [
            {"step": "Bidder submits without EMD", "expected": "Status stays 'submitted'; escrow tab shows the pending EMD", "testid": "bid-row-status"},
            {"step": "Reject with a 5-char note", "expected": "HTTP 400 'note must be at least 10 characters'", "testid": "bid-reject"},
            {"step": "Assign certifier", "expected": "Inspection record created + email dispatched with signed accept-link", "testid": "assign-certifier"},
        ],
        "mgmt": [
            "Every stage transition is an audit event with actor + previous state + new state.",
            "KPI: median bid cycle-time (submitted → awarded).",
            "SLA threshold: >7 days at any single stage triggers a daily nudge.",
        ],
    },
    {
        "title": "Bidding Ops · Committee",
        "purpose": "Form evaluation committees with chair + members + quorum + external invitees.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "12_bidding.png",
        "overview": (
            "One open committee per tender. Members are picked via checkbox grid (Bug 58 fix). "
            "Chair dropdown auto-filters to selected members only (Bug 58c). Quorum caps at "
            "≤ member count (Bug 58d). Committee can be dissolved with a reason ≥8 chars, "
            "and per-invitee 'Resend' buttons regenerate the accept-token."
        ),
        "ops": [
            "Tick members from the checkbox grid — chair dropdown auto-narrows.",
            "Set quorum; input caps at the number of ticked members.",
            "Add external invitees (name + email + designation) → they receive an accept-link email.",
            "Dissolve committee: reason ≥8 chars; committee status becomes 'dissolved' and is preserved for audit.",
        ],
        "qa": [
            {"step": "Tick 3 members, pick chair from 4th (unpicked)", "expected": "Chair dropdown does not offer the 4th; chair auto-clears if unpicked after", "testid": "committee-chair"},
            {"step": "Enter quorum = 10 with 4 members ticked", "expected": "Input capped at 4 with live hint", "testid": "committee-quorum"},
            {"step": "Dissolve committee with 6-char reason", "expected": "HTTP 400 'dissolve reason must be at least 8 characters'", "testid": "committee-dissolve"},
            {"step": "Resend invite to pending external", "expected": "New accept-token generated; email sent; old link now 404", "testid": "committee-resend"},
        ],
        "mgmt": [
            "COI check: evaluations.submit_score returns 400 unless the scorer has recorded a COI declaration for that notice (G2 governance).",
            "Chair change post-formation is a governance event — audited separately.",
            "KPI: median committee formation → first score < 3 business days.",
        ],
    },
    {
        "title": "Reverse Auctions",
        "purpose": "Live reverse-auction rooms with masked bidder identities.",
        "users": ["Ops", "QA"],
        "image": "13_auctions.png",
        "overview": (
            "Masked identity auction (Bidder A/B/C…) with min-decrement, hard price floor, "
            "and anti-snipe extension. Draft auctions never expose the public bidder link "
            "(G5 fix). Participant validation blocks duplicates + non-registered emails."
        ),
        "ops": [
            "'+ New auction' → set min-decrement (currency), price floor, anti-snipe seconds.",
            "Draft mode: bidder URL hidden; explanatory hint shown instead.",
            "Go live → the /vendor/auction/:aid room polls every 2 s.",
        ],
        "qa": [
            {"step": "Add a duplicate email to participants", "expected": "HTTP 400 'duplicate participant email'", "testid": "auction-participants"},
            {"step": "Open draft auction detail", "expected": "Bidder URL not shown; explanatory text present", "testid": "auction-bidder-link"},
            {"step": "Close a live auction", "expected": "status='closed'; last valid bid becomes winning_price", "testid": "auction-close"},
        ],
        "mgmt": [
            "Anti-snipe extends deadline by N seconds if a bid lands in the final N seconds — anti-manipulation.",
            "Winning price is written to the linked bid record for downstream award.",
        ],
    },
    {
        "title": "Escrow (EMD)",
        "purpose": "Joint escrow accounts with dual-signature EMD releases.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "14_escrow.png",
        "overview": (
            "Every EMD instrument flows through a joint account operated by one PMC officer "
            "+ one escrow-institution officer. Both must sign before release (G1 fix). Aging "
            "days per transaction; SLA breach flag when >7 days pending. Reconciliation "
            "summary in Stakeholder Reports."
        ),
        "ops": [
            "'+ Account' — two named officers required; backend rejects if pmc_officer.email == vendor_officer.email.",
            "'+ Transaction' → sign your side → wait for the other side.",
            "Release fires only after BOTH signatures; otherwise HTTP 409.",
        ],
        "qa": [
            {"step": "Create account with same email on both sides", "expected": "HTTP 400 'PMC officer and escrow officer must be different people' (G1)", "testid": "escrow-account-create"},
            {"step": "Sign PMC side but not vendor side, then click Release", "expected": "HTTP 409 'awaiting escrow-officer signature'", "testid": "escrow-release"},
            {"step": "Open Stakeholder Reports / Escrow", "expected": "aging_days per tx; sla_breach=true when >7d", "testid": "stakeholder-escrow"},
        ],
        "mgmt": [
            "G1 governance: same-login-both-sides is architecturally blocked.",
            "SLA threshold configurable per tenant (default 7 days).",
            "KPI: median release cycle-time; SLA breach count per week.",
        ],
    },
    {
        "title": "Evaluation & Scoring",
        "purpose": "Committee scoring with per-criterion weights + COI enforcement.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "15_evaluation.png",
        "overview": (
            "Committee members score each bid against the rubric set on the notice. Weighted "
            "totals compute live. Every score requires an outstanding COI declaration for that "
            "(scorer, notice) tuple — enforcement is HTTP 400 at submit_score."
        ),
        "ops": [
            "Pick a bid → enter scores 0-100 per criterion.",
            "COI tick box: 'I have no conflict of interest with this bidder on this notice'.",
            "Weighted total updates live; committee median becomes the technical score.",
        ],
        "qa": [
            {"step": "Score without ticking COI", "expected": "HTTP 400 'COI declaration required' (G2)", "testid": "eval-submit"},
            {"step": "Enter score > 100", "expected": "HTTP 400 'score must be between 0 and 100'", "testid": "eval-score-input"},
            {"step": "Rubric with weights not summing to 100", "expected": "HTTP 400 at rubric save (Bug 56)", "testid": "eval-rubric-save"},
        ],
        "mgmt": [
            "G2 governance: no committee score can be submitted without an existing COI record.",
            "Rubric is set once per notice and locked at first score.",
            "KPI: score-dispersion per bid (high dispersion = need for deliberation).",
        ],
    },
    {
        "title": "L1 Comparison",
        "purpose": "Rule-based lowest-compliant winner selection.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "19_l1.png",
        "overview": (
            "Distinct from Evaluation scoring: L1 filters technically-compliant bids and "
            "picks the lowest total price. Empty state lists exclusion reasons (technical "
            "not scored / non-compliant / withdrawn / notice status)."
        ),
        "ops": [
            "Open L1 → the eligible set + active ranking rule badge display.",
            "If empty, the panel lists why each excluded bid is out.",
        ],
        "qa": [
            {"step": "Run L1 with all bids under technical cutoff", "expected": "Empty state with reason 'non-compliant' + count per reason", "testid": "l1-empty-state"},
            {"step": "Open L1 with no closed notices", "expected": "'No eligible notices' shown; ranking rule badge hidden", "testid": "l1-panel"},
        ],
        "mgmt": [
            "Ranking rule badge shows: 'lowest-compliant price wins' (transparency requirement).",
            "CSV export via /api/v1/stakeholder-reports/awards.csv.",
        ],
    },
    {
        "title": "Awards & POs",
        "purpose": "Draft Purchase Order, SLA, Contract PDFs on award.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "16_awards.png",
        "overview": (
            "Awarding a bid drafts three PDFs: PO (`PMC-PO-YYYY-#####`), SLA, Contract — all "
            "with a diagonal DRAFT watermark until countersigned. Regenerate requires "
            "confirmation and pushes {regenerated_at, regenerated_by} into "
            "bid.award_regenerations[]."
        ),
        "ops": [
            "'Award' → confirms; three PDFs are generated + stored server-side.",
            "'Regenerate' → confirmation dialog + audit toast with timestamp.",
            "Send to DocuSign to lift the DRAFT watermark on countersign.",
        ],
        "qa": [
            {"step": "Regenerate documents", "expected": "Confirmation dialog appears; on OK the toast shows timestamp + admin email; award_regenerations[] gains 1 entry", "testid": "awards-regenerate"},
            {"step": "Award an already-awarded bid", "expected": "HTTP 409 'bid already awarded'", "testid": "awards-award"},
        ],
        "mgmt": [
            "Every regeneration is a governance event — audit log flags 'suspicious' if >3 regenerations on the same bid.",
            "KPI: median time-to-award (committee approval → award).",
        ],
    },
    {
        "title": "DocuSign · Envelope Log",
        "purpose": "JWT Grant DocuSign integration + authoritative-envelope flag.",
        "users": ["Ops", "QA"],
        "image": "20_docusign.png",
        "overview": (
            "PO / SLA / Contract PDFs go out via DocuSign either as Embedded (in-app iframe) "
            "or Email (hosted signing). Envelope Log per (bid_id, sub_kind) flags the "
            "authoritative envelope: status=completed wins, break ties by created_at."
        ),
        "ops": [
            "First run → 'Grant DocuSign consent' redirects to DocuSign, then comes back.",
            "Envelope Log rows show status + delivery mode + is_authoritative badge.",
            "Resend for envelopes in 'sent' status.",
        ],
        "qa": [
            {"step": "Filter Envelope Log by bid_id + sub_kind", "expected": "Only relevant envelopes; exactly one row has is_authoritative=true", "testid": "envelope-log-filter"},
            {"step": "Two envelopes both status=completed", "expected": "The one with the later created_at wins is_authoritative=true", "testid": "envelope-log-row"},
        ],
        "mgmt": [
            "Authoritative envelope is the single source of truth for legal downstream — audit ties to that envelope_id.",
            "Consent expires per DocuSign policy (usually 1 year) — dashboard warns 30 days out.",
        ],
    },
    {
        "title": "BOQ & Contracts",
        "purpose": "Bill-of-Quantities templates + Contract lifecycle.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "17_boq.png",
        "overview": (
            "BOQ templates are imported via Excel (Sl.No | Description | Unit | Quantity | "
            "Unit Rate | Remarks). Vendors quote against the template. Only awarded bids can "
            "spawn a contract (`PMC-CON-YYYY-####`). Contracts export CSV + per-contract "
            "version timeline (creation + milestone completions + variation orders)."
        ),
        "ops": [
            "Import Excel BOQ template; validate columns are exact.",
            "Vendors submit BOQ answers as part of the bid.",
            "Awarded bid → create contract; add milestones + variation orders as needed.",
            "Contracts sub-tab: filter by status/vendor/query; export CSV; view version timeline.",
        ],
        "qa": [
            {"step": "Export contracts.csv with status=active filter", "expected": "CSV downloads with correct row count; Content-Disposition: attachment header", "testid": "contracts-export-csv"},
            {"step": "Open version timeline for a contract with 2 milestones + 1 VO", "expected": "3 events sorted by 'at' ASC; each shows event type + amount + by", "testid": "contract-versions"},
        ],
        "mgmt": [
            "Every variation order is auditable {at, by, amount_delta, reason}.",
            "Milestone hit-rate feeds Stakeholder Reports / SLA.",
        ],
    },
    {
        "title": "Meetings",
        "purpose": "Schedule Jitsi / Zoom meetings tied to a notice OR marked internal.",
        "users": ["Ops", "QA"],
        "image": "18_meetings.png",
        "overview": (
            "Every meeting either references a notice_ref OR is explicitly flagged as an "
            "'Internal meeting'. Backend rejects create with HTTP 400 otherwise. Cancelled "
            "meetings are hidden by default (include_cancelled=true toggle to show)."
        ),
        "ops": [
            "'+ Schedule' → pick provider (Jitsi/Zoom), subject, time, invitees.",
            "Tick 'Internal meeting' to skip the notice dropdown (e.g. team standup).",
            "Otherwise, pick a notice — invitees receive a signed accept-link.",
        ],
        "qa": [
            {"step": "Create meeting without notice_ref and is_internal=false", "expected": "HTTP 400 'notice_ref required unless is_internal=true' (Bug 48b)", "testid": "mtg-create"},
            {"step": "Tick 'Internal meeting'", "expected": "Notice dropdown disables + clears; create succeeds without notice_ref", "testid": "mtg-is-internal"},
        ],
        "mgmt": [
            "Every meeting join is logged with invitee token + timestamp.",
            "Zoom uses JWT app credentials; Jitsi is self-hosted (no credentials).",
        ],
    },
    {
        "title": "Vendor Intel",
        "purpose": "Bulk vendor risk register with BL / WL flags.",
        "users": ["Ops", "Mgmt"],
        "image": "21_vendor-intel.png",
        "overview": (
            "Imported watch-lists + blacklists — used to alert Committee scorers when a bidder "
            "appears on any list. Anonymised entries (—) support imports from law-enforcement "
            "feeds where identities cannot be disclosed."
        ),
        "ops": [
            "Legend bar at the top: BL = Blacklisted, WL = Watch-list, — = anonymised.",
            "Add entry manually OR bulk-import CSV.",
        ],
        "qa": [
            {"step": "Score a bid where the vendor is on BL", "expected": "Committee scorer sees an inline red BL badge on the bidder card", "testid": "eval-vendor-badge"},
        ],
        "mgmt": [
            "BL entries block auto-award; committee must override with a reason.",
            "Anonymised entries mask the vendor name but preserve match-hash for detection.",
        ],
    },
    {
        "title": "Product Catalog",
        "purpose": "SKU catalog feeding Stripe checkout + price-history log.",
        "users": ["Ops", "Mgmt"],
        "image": "22_products.png",
        "overview": (
            "Products drive the public checkout page (Stripe). Every price change is written "
            "to price_history[] with {old_price, new_price, changed_by, changed_at}."
        ),
        "ops": [
            "'+ Product' → name, price, currency, description, image URL.",
            "Edit → save changes → history entry auto-created.",
        ],
        "qa": [
            {"step": "Change product price 3 times", "expected": "price_history[] has 3 entries with distinct changed_at", "testid": "product-edit-save"},
        ],
        "mgmt": [
            "Price changes are a governance event — dashboard flags >30% change.",
            "KPI: gross checkout revenue per SKU per month.",
        ],
    },
    {
        "title": "Engagements (Quotes)",
        "purpose": "Public quote-requests through to invoicing + aging report.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "23_engagements.png",
        "overview": (
            "State machine: quote_requested → quoted → invoiced → paid (or cancelled with "
            "reason ≥5 chars). Aging summary buckets receivables by age (0-7/8-30/31-60/61+ days)."
        ),
        "ops": [
            "New quote requests land as engagements from the public site.",
            "Set quoted amount → 'Invoice' generates a Stripe checkout link.",
            "Cancel requires reason ≥5 chars.",
        ],
        "qa": [
            {"step": "Cancel an engagement with 3-char reason", "expected": "HTTP 400 'reason must be at least 5 characters' (Bug 35)", "testid": "eng-cancel"},
            {"step": "GET /engagements/aging/summary", "expected": "Returns 0-7/8-30/31-60/61+ buckets with counts", "testid": "eng-aging"},
        ],
        "mgmt": [
            "Aging report drives receivables collection.",
            "KPI: quote → paid conversion rate; median days to payment.",
        ],
    },
    {
        "title": "Masters · Roles & Permissions",
        "purpose": "Single source of truth for who can do what.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "25_permissions.png",
        "overview": (
            "Permissions Matrix + hierarchy Level are now unified via "
            "GET /api/v1/permissions/effective/{role} (Wave G2). One call returns "
            "{role, level, level_label, tabs, actions} — drives menu visibility + "
            "button disabled-state everywhere."
        ),
        "ops": [
            "Masters → Permissions → tick/untick actions per role per document type.",
            "Every save writes updated_at + updated_by; visible in the header.",
            "Level (0..3) is set on the Staff Master screen.",
        ],
        "qa": [
            {"step": "GET /api/v1/permissions/effective/reviewer", "expected": "Returns {level:1, level_label:'deputy', tabs:[…], actions:{view:true, create:true, modify:true, delete:false, publish:false}}", "testid": "permissions-effective"},
            {"step": "Reviewer tries to publish a notice", "expected": "HTTP 403 'insufficient permissions to publish'", "testid": "notices-publish-checkbox"},
        ],
        "mgmt": [
            "G3 governance: closed — single access-control endpoint.",
            "Full audit on matrix mutations.",
        ],
    },
    {
        "title": "Portal Branding",
        "purpose": "Tenant-level logo + theme + rolling logo history.",
        "users": ["Ops", "Mgmt"],
        "image": "30_branding.png",
        "overview": (
            "Every tenant gets primary_color + accent_color + favicon + logo. Every new logo "
            "upload appends to logo_history[] (max 10 rolling); GET /logo-history to fetch."
        ),
        "ops": [
            "Upload a new logo → history entry auto-created.",
            "PATCH /api/v1/branding/{tid}/theme with primary_color, accent_color (#RRGGBB), favicon_data_url.",
        ],
        "qa": [
            {"step": "Upload 11 logos sequentially", "expected": "logo_history[] contains only the last 10 entries", "testid": "branding-logo-upload"},
            {"step": "PATCH theme with primary_color='red'", "expected": "HTTP 422 'primary_color must match #RRGGBB'", "testid": "branding-theme-save"},
        ],
        "mgmt": [
            "Branding changes are audited — no silent tenant re-brand.",
        ],
    },
    {
        "title": "Reports · Asked-vs-Delivered + Flowcharts",
        "purpose": "Development / scope-completion snapshot for engineering handoff.",
        "users": ["Mgmt"],
        "image": "27_reports.png",
        "overview": (
            "Original 39-page Enterprise CRM & e-Tender Revised Integrated Report is "
            "reduced to a live 'asked vs delivered' statement + three swim-lane flowcharts "
            "(platform / user guide / testing). Snapshot to /app/docs/reports/ writes all "
            "9 artefacts + a manifest."
        ),
        "ops": [
            "'Snapshot to disk' → 9 files land in /docs/reports/.",
            "Bug 38 fix: each artefact is wrapped in try/except so one failure returns errors[] instead of a 500.",
        ],
        "qa": [
            {"step": "POST /api/v1/reports/snapshot", "expected": "{ok:true, files:[…9 items], errors:[]}", "testid": "reports-snapshot"},
        ],
        "mgmt": [
            "Deliverable for investor code review + engineering handoff.",
            "Zero-error snapshot = build health.",
        ],
    },
    {
        "title": "Stakeholder Reports · G4 rebuild",
        "purpose": "Four operational reports for procurement stakeholders.",
        "users": ["Mgmt", "Ops"],
        "image": "28_stakeholder.png",
        "overview": (
            "G4 was rebuilt in v15/v18: four live JSON + CSV reports keyed off real "
            "collections. Tenders (pipeline snapshot), Awards (PO + contract value), Escrow "
            "(aging + SLA breach), SLA (contracts + milestone hit-rate)."
        ),
        "ops": [
            "Tab through the four reports; each has a CSV download button.",
            "Escrow report highlights SLA breach count in the top row.",
        ],
        "qa": [
            {"step": "Open Stakeholder Reports / Escrow", "expected": "aging_days per tx; sla_breach=true when >7d; header shows breach count", "testid": "stakeholder-escrow-sla"},
            {"step": "Download tenders.csv", "expected": "CSV downloads with Content-Disposition: attachment", "testid": "stakeholder-download-csv"},
        ],
        "mgmt": [
            "Circulate CSV to stakeholders without portal access.",
            "KPI dashboard: SLA breaches, awards/month, milestone hit-rate.",
        ],
    },
    {
        "title": "Help Requests",
        "purpose": "Triage inbound support tickets from the public site.",
        "users": ["Ops", "Mgmt"],
        "image": "29_help.png",
        "overview": (
            "Public help form drops a ticket with kind (Sales / Support / Technical / Other) + "
            "requester identity + phone + company. Panel surfaces aging + resolution history."
        ),
        "ops": [
            "Sort by aging (oldest first).",
            "Update kind, mark resolved, add resolution note.",
        ],
        "qa": [
            {"step": "Public submits a Help form with no email", "expected": "HTTP 400 'email required'", "testid": "help-public-submit"},
            {"step": "Mark resolved", "expected": "Row moves to 'Resolved' tab; resolution_at + resolution_note stamped", "testid": "help-resolve"},
        ],
        "mgmt": [
            "SLA planned: 24 h first response for Sales, 72 h for Technical.",
        ],
    },
    {
        "title": "Audit Log",
        "purpose": "Chronological ledger of every substantive action.",
        "users": ["Ops", "Mgmt"],
        "image": "26_audit.png",
        "overview": (
            "Every mutation writes to audit_log with {at, actor, action, resource_type, "
            "resource_id, payload}. Global <ErrorBoundary/> catches any render hang on this "
            "screen so users are never locked out."
        ),
        "ops": [
            "Sort by 'at' DESC (default).",
            "Copy any row's payload to inspect the raw event.",
        ],
        "qa": [
            {"step": "Render audit with 10 000 rows", "expected": "Table remains scrollable; no white screen; ErrorBoundary NOT triggered", "testid": "admin-audit-panel"},
        ],
        "mgmt": [
            "Legal-grade: audit log is append-only.",
            "Filters (actor/type/date) planned for Bucket B.",
        ],
    },
    {
        "title": "Governance Guardrails",
        "purpose": "Five architectural controls audited by the QA team.",
        "users": ["Mgmt", "QA"],
        "image": None,
        "overview": (
            "G1..G5 are the guardrails that turn 'compliance theatre' into real controls. "
            "Every one is either an HTTP 400 at the API layer OR a UI element that cannot "
            "leak sensitive state."
        ),
        "ops": [],
        "qa": [
            {"step": "G1 · same-login-both-escrow-sides", "expected": "HTTP 400 'must be different people'", "testid": "escrow-account-create"},
            {"step": "G2 · score without COI", "expected": "HTTP 400 'COI declaration required'", "testid": "eval-submit"},
            {"step": "G3 · effective/{role}", "expected": "Single payload merges tabs + actions + level", "testid": "permissions-effective"},
            {"step": "G4 · Stakeholder Reports", "expected": "Panel exposes 4 real reports + CSV", "testid": "stakeholder-reports-panel"},
            {"step": "G5 · draft auction public link", "expected": "Not rendered when status='draft'", "testid": "auction-bidder-link"},
        ],
        "mgmt": [
            "Bug tracker v5 · 44 of 52 observations FIXED (85 %).",
            "Guardrails are the pass/fail for investor code review.",
        ],
    },
    {
        "title": "Dashboard · Analytics & Drill-through",
        "purpose": "Real-time KPIs + click-through to filtered lists.",
        "users": ["Ops", "Mgmt"],
        "image": "06_analytics.png",
        "overview": (
            "AI Anomaly, Pipeline Funnel, Top-Priced Bids — each card is now clickable and "
            "drills through /api/v1/dashboard-drill/* to a filtered mini-table (Bug 32/47 fixes)."
        ),
        "ops": [
            "Click any card to expand a filtered mini-table.",
            "Click again to collapse.",
        ],
        "qa": [
            {"step": "Click AI Anomaly card", "expected": "Drill panel expands with 200 rows max; empty state text 'No AI-flagged bids' if none", "testid": "drill-card-anom"},
            {"step": "Click Pipeline Funnel card", "expected": "/dashboard-drill/pipeline?status= returns 500 rows max", "testid": "drill-card-pipe"},
        ],
        "mgmt": [
            "KPI dashboard is the daily standup screen.",
            "AI Copilot is advisory — no state change without human sign-off.",
        ],
    },
    {
        "title": "Sign-out & Exit",
        "purpose": "Cookie-clear + redirect to public login.",
        "users": ["Ops", "QA"],
        "image": "31_sign-out-return.png",
        "overview": (
            "Sign-out clears the HTTPOnly admin cookie and redirects to /login. Any deep-link "
            "back to /admin bounces to /login. Cookie is set to Secure + SameSite=Lax."
        ),
        "ops": [
            "Top-right → 'Sign out'.",
            "Session cookie cleared server-side; browser cookie invalidated.",
        ],
        "qa": [
            {"step": "Click Sign out", "expected": "Redirect to /login within 1 s; admin cookie no longer present", "testid": "admin-logout"},
            {"step": "Navigate directly to /admin after sign-out", "expected": "Bounce to /login; /api/v1/me returns 401", "testid": "admin-logout"},
        ],
        "mgmt": [
            "Session TTL 12 h max; sliding renewal on activity.",
        ],
    },
]


# ============ DOCX BUILDER ====================================================

def _shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _run(para, text, *, size=10, bold=False, italic=False, color=None,
          font="Calibri"):
    r = para.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def _kicker(doc, label, hex_fill="0B1F3A"):
    # Insert a 1-cell full-width table used as a coloured section header.
    t = doc.add_table(rows=1, cols=1)
    cell = t.rows[0].cells[0]
    _shading(cell, hex_fill)
    para = cell.paragraphs[0]
    _run(para, label.upper(), size=9, bold=True,
          color=RGBColor(0xFF, 0xFF, 0xFF))
    t.autofit = True
    return t


def _test_table(doc, rows):
    """3-column QA table: # | Test step | Expected outcome (+ testid)."""
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "#"
    hdr[1].text = "Test step"
    hdr[2].text = "Expected outcome"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, row in enumerate(rows, start=1):
        cells = tbl.add_row().cells
        cells[0].text = str(i)
        cells[1].text = row["step"]
        # Concatenate expected + testid line
        cells[2].text = row["expected"]
        if row.get("testid"):
            p = cells[2].add_paragraph()
            _run(p, f"data-testid: {row['testid']}", size=8,
                  color=NAVY_SOFT, font="Consolas")
        for c in cells:
            for para in c.paragraphs:
                for r in para.runs:
                    if not r.font.size:
                        r.font.size = Pt(8.5)
                    if r.font.color.rgb is None:
                        r.font.color.rgb = NAVY
    tbl.columns[0].width = Inches(0.35)
    tbl.columns[1].width = Inches(3.3)
    tbl.columns[2].width = Inches(3.5)
    return tbl


def _bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        _run(p, it, size=10, color=NAVY)


def _footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    _run(p, "PMC Managers v2 · Master Training Manual · v1 · Confidential",
          size=8, color=GREY)
    p.add_run("\t\t")
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r = p.add_run("").element
    r.append(fld_begin); r.append(instr); r.append(fld_sep); r.append(fld_end)


def build():
    doc = Document()

    section = doc.sections[0]
    section.page_height = Inches(11.69)
    section.page_width = Inches(8.27)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(0.6))
    _footer(section)

    # -------- Cover ----------------------------------------------------------
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p, TITLE, size=30, bold=True, color=NAVY)
    p = doc.add_paragraph()
    _run(p, SUBTITLE, size=15, italic=True, color=NAVY_SOFT)
    doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p, f"Generated {GENERATED}", size=9, color=GREY)
    doc.add_paragraph()
    doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p,
          "This document supersedes every earlier PMC training manual "
          "(v1 → v3.2 handbook · Screenshot Training Manual v1 · every "
          "observation-response iteration).",
          size=11, bold=True, color=NAVY)
    doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p,
          "For each logical module in the portal you get four consumer-specific "
          "tracks in the same document:", size=10.5, color=NAVY)
    for label, hex_fill in [
        ("Overview — one-paragraph story · who uses it · where it sits in the workflow", "0B1F3A"),
        ("Operations Team — 'how to use' step-by-step for trainee ops staff", "0B4F6C"),
        ("QA Team — numbered test cases · expected outcomes · data-testid selectors", "7F1D1D"),
        ("Management Team — governance controls · KPIs · reports", "065F46"),
    ]:
        p = doc.add_paragraph()
        _shading_run = p.add_run("  ")
        _run(p, label, size=10, color=NAVY)
    doc.add_page_break()

    # -------- TOC ------------------------------------------------------------
    p = doc.add_paragraph()
    _run(p, "Contents", size=22, bold=True, color=NAVY)
    doc.add_paragraph()
    toc = doc.add_table(rows=1, cols=3)
    toc.style = "Light Grid Accent 1"
    hdr = toc.rows[0].cells
    hdr[0].text = "#"; hdr[1].text = "Module"; hdr[2].text = "Audience"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True; r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, ch in enumerate(CHAPTERS, start=1):
        row = toc.add_row().cells
        row[0].text = str(i)
        row[1].text = ch["title"]
        row[2].text = " · ".join(ch["users"])
        for cell in row:
            for para in cell.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(9); r.font.color.rgb = NAVY
    toc.columns[0].width = Inches(0.35)
    toc.columns[1].width = Inches(4.5)
    toc.columns[2].width = Inches(2.3)
    doc.add_page_break()

    # -------- Chapters -------------------------------------------------------
    for i, ch in enumerate(CHAPTERS, start=1):
        # Chapter heading
        p = doc.add_paragraph()
        _run(p, f"Chapter {i} · {ch['title']}", size=20, bold=True, color=NAVY)
        p = doc.add_paragraph()
        _run(p, ch["purpose"], size=11, italic=True, color=NAVY_SOFT)
        p = doc.add_paragraph()
        _run(p, "Audience: " + " · ".join(ch["users"]), size=9, color=GREY)

        # Overview
        _kicker(doc, "Overview")
        p = doc.add_paragraph()
        _run(p, ch["overview"], size=10.5, color=NAVY)

        # Screenshot
        if ch.get("image"):
            img = SCREENSHOT_DIR / ch["image"]
            if img.exists():
                doc.add_paragraph()
                doc.add_picture(str(img), width=Inches(7.0))

        # Ops
        if ch.get("ops"):
            _kicker(doc, TRACK_STYLE["OPS"][1], hex_fill="0B4F6C")
            _bullets(doc, ch["ops"])

        # QA
        if ch.get("qa"):
            _kicker(doc, TRACK_STYLE["QA"][1], hex_fill="7F1D1D")
            _test_table(doc, ch["qa"])

        # Mgmt
        if ch.get("mgmt"):
            _kicker(doc, TRACK_STYLE["MGMT"][1], hex_fill="065F46")
            _bullets(doc, ch["mgmt"])

        doc.add_page_break()

    # -------- Appendices -----------------------------------------------------
    p = doc.add_paragraph()
    _run(p, "Appendix A · Change-log", size=20, bold=True, color=NAVY)
    doc.add_paragraph()
    for entry in [
        ("v1 · Sep 2026", "Definitive master manual · every module × 4 tracks · supersedes v1..v3.2 handbook + Screenshot Manual v1 + all Observation-Response iterations."),
        ("Backend v17", "Committee UX overhaul · Wave-E2 polish (7 fixes) · G2 access-control consolidation."),
        ("Frontend v20", "Committee checkboxes + dissolve + resend · Tender kind-tab reset · status-token toast · Dashboard drill cards."),
        ("Backend v15", "G4 rebuild · Dashboard drill endpoints · Branding theme + logo history · Engagements aging · DocuSign authoritative flag."),
        ("Frontend v18", "StakeholderReportsPanel · Notices filter bar · v3.2 docs."),
    ]:
        p = doc.add_paragraph()
        _run(p, entry[0], size=11, bold=True, color=NAVY)
        p = doc.add_paragraph()
        _run(p, entry[1], size=10, color=NAVY)
    doc.add_page_break()

    p = doc.add_paragraph()
    _run(p, "Appendix B · Guardrails (governance)", size=20, bold=True, color=NAVY)
    doc.add_paragraph()
    for g in [
        "G1 · Escrow dual-signature — HTTP 400 if pmc_officer.email == vendor_officer.email.",
        "G2 · COI cross-check — HTTP 400 at evaluations.submit_score without a COI declaration for that notice.",
        "G3 · Access-control unified — GET /api/v1/permissions/effective/{role} merges tabs + actions + hierarchy Level.",
        "G4 · Stakeholder Reports — four real reports (Tenders / Awards / Escrow / SLA) with JSON + CSV.",
        "G5 · Draft auction bidder link hidden when status='draft'.",
        "ErrorBoundary — every route is wrapped; blank screens are architecturally impossible.",
        "Audit — every substantive action writes to audit_log with actor + IP + payload.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        _run(p, g, size=10, color=NAVY)

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_DOCX))
    print(f"Written {OUT_DOCX} · {OUT_DOCX.stat().st_size / 1024:.1f} KB · "
          f"{len(CHAPTERS)} chapters")


def convert_pdf():
    """Best-effort DOCX → PDF via LibreOffice CLI."""
    for cmd in ("libreoffice", "soffice"):
        try:
            r = subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf",
                 "--outdir", str(OUT_DOCX.parent), str(OUT_DOCX)],
                capture_output=True, timeout=120,
            )
            if r.returncode == 0 and OUT_PDF.exists():
                print(f"Wrote {OUT_PDF} · {OUT_PDF.stat().st_size / 1024:.1f} KB")
                return True
            else:
                print(f"[warn] {cmd} exit {r.returncode}: "
                      f"{(r.stderr or b'').decode()[:200]}")
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[warn] {cmd} error: {e}")
            break
    print("[note] LibreOffice not available; skipping PDF conversion.")
    return False


if __name__ == "__main__":
    build()
    convert_pdf()
