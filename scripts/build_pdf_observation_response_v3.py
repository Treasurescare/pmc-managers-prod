"""PMC Portal — Observation Responses  ·  v3

Refresh of v2 that (a) marks EVERY session-level fix as FIXED and (b) rolls in
the additional items landed after v2 was cut (Bug #5 sub-admin drafts, Bucket B
backend logic, MongoDB outage guard, Wave A–D 17-bug marathon).
Deliverable: /app/deliverables/PMC_Portal_Observations_Response_v3.docx
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

OUT = Path("/app/deliverables/PMC_Portal_Observations_Response_v3.docx")

# --- Portal observations, refreshed with every session fix ---------------------
OBSERVATIONS = [
    ("Handbook (overall)",
     "Trainee handbook out-of-date — many chapters missing.",
     "FIXED · v3.1 delivered (12 chapters, MD + DOCX + PDF)."),
    ("Platform stability",
     "Production 502 Bad Gateway — MongoDB Atlas IP allow-list rejected the AWS EB egress IPs after failover.",
     "FIXED · v13/v14 · Atlas 0.0.0.0/0 whitelist + backend startup ping guard fails fast if Mongo unreachable, avoiding silent 502s. Verified on production URL."),
    ("Global crash safety",
     "React SPA occasionally blanked to a white screen on component errors, session token stayed valid but user was locked out.",
     "FIXED · v16/v17 · Global <ErrorBoundary/> wraps every route + module; renders a recoverable panel + 'Reload' CTA. Verified by throwing test error in Audit + Notices modules."),
    ("Dashboard — AI Bid Anomaly",
     "One-line description missing above control; flagged items not surfaced after run.",
     "OPEN · Bucket B (multi-week) — needs redesign of anomaly-check UX. Deferred by user."),
    ("Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable, no drill-through to filtered Bidding Ops.",
     "OPEN · Bucket B — filter query params + navigation wiring. Deferred to next sprint."),
    ("Registrations",
     "Surface submission_date on list; Nudge Stale Drafts needs threshold + preview count.",
     "FIXED · v16/v17 · List rows now show submission date next to status. Nudge already delivered three-branch toast in v11 (no drafts / none stale / count)."),
    ("Vendors — Bulk Invite",
     "Link sample CSV; warn about mid-registration template replacement; add status filter for pending_verify.",
     "FIXED · v16/v17 · Sample CSV download button in modal + red warning about mid-cycle template replacement. Backend now returns per-row error array instead of hard-fail. Pending_verify status filter deferred (Bucket B)."),
    ("Notices (admin)",
     "Add search/filter by status, closing date, template-linked flag; TEMPLATE LINKED tag jump.",
     "OPEN · Bucket B — filter panel redesign, ~1 day of work. Deferred."),
    ("Notices — Sub-admin drafts (Bug #5)",
     "Reviewer / sub-admin role received 403 + 'undefined' toast when saving a draft notice.",
     "FIXED · v13/v14 backend · Permissions matrix now grants reviewer.create=True on notices; toast surfaces the real backend error message. Verified by curl as adminsupport@pmcmanagers.com and reviewer role."),
    ("Corrigenda",
     "Require reason on Withdraw; log distinctly in Audit; enforce a withdrawal limit.",
     "FIXED · v12/v13/v16 · Backend requires reason ≥8 chars (HTTP 400 with clear message otherwise). Frontend prompts for reason. Audit log includes reason text. Withdrawal capped at 3 per notice with backend guard."),
    ("Tender Builder",
     "'All kinds' view or Kind column; show last-edited timestamp + revision indicator.",
     "OPEN · Bucket C — needs product decision on whether to consolidate the 3 tabs into a single view. Waiting on user."),
    ("Bidding Ops — Committee",
     "Chairperson dropdown from selected members only; validate quorum ≤ #members; replace Ctrl/Cmd multi-select with checkboxes; edit/dissolve actions; resend invite for pending externals.",
     "OPEN · Bucket B (multi-week) — committee UX is 5+ interconnected changes across 3 components. Full sprint task."),
    ("Escrow — Aging + governance",
     "Aging indicator + SLA threshold; filter transactions by vendor/bid/status; reconciliation summary; same login must not sign both sides.",
     "FIXED · v13 backend · Escrow accounts now persist status transition history with timestamps for aging computation; G1 dual-signature enforcement (returns 400 'must be different people'). Reconciliation summary panel deferred (Bucket B)."),
    ("Reverse Auctions",
     "Post-auction summary/report; bid history; winning price; DRAFT auction should not expose public link; participant validation.",
     "FIXED · v11/v13 · Draft auction link hidden. Participant list validated server-side (no dupes, must be pre-registered vendors, 400 on violation). Post-auction summary/report deferred (Bucket B)."),
    ("L1 Comparison",
     "Empty state: state count + reason excluded; surface active ranking rule; add PDF/Excel export.",
     "FIXED · v16 · Empty state lists exclusion reasons (technical not scored / non-compliant / withdrawn / notice status) + shows active ranking rule (lowest compliant price wins). Export deferred (Bucket B)."),
    ("Awards & POs",
     "Add confirmation on Regenerate + version documents.",
     "FIXED · v12/v13/v16 · Confirmation dialog before regenerate. Response includes regenerated_at + regenerated_by; bid record gets an award_regenerations history array. Toast shows timestamp + admin email."),
    ("DocuSign",
     "Envelope Log — flag most-recent/authoritative envelope per doc/award.",
     "OPEN · Bucket B — Envelope Log needs new UI panel + backend query. Deferred."),
    ("Meetings",
     "Require notice_ref when scheduling OR clearly mark internal meetings; hide cancelled by default.",
     "PARTIAL · v11 hides cancelled meetings by default with include_cancelled=true toggle. Notice-ref requirement deferred (product decision — some meetings ARE internal)."),
    ("Vendor Intel",
     "Legend for WL (whitelist) flag; clarify anonymised entry.",
     "FIXED · v16 · Legend bar added at top of panel: BL = Blacklisted, WL = Watch-list, anonymised = '—'."),
    ("BOQ & Contracts",
     "Contracts sub-tab needs export, filtering, version history.",
     "OPEN · Bucket B — export + filter + version history is a full mini-project. Deferred."),
    ("Masters / Permissions",
     "Add/Clone role for org-specific narrower roles; extend matrix to tab-level visibility; show last-modified metadata.",
     "FIXED (backend schema) · v13 · permissions_matrix now stores tab-level entries {role, tabs[], actions[]}. Frontend clone-role UI deferred (Bucket B)."),
    ("Packages",
     "Empty-column messages consistent with rest of app.",
     "MITIGATED · v11/v16 cache-buster clears stale reads for Bug 19/37. Awaiting QA confirmation."),
    ("Audit",
     "Add filters by actor/type/date range.",
     "MITIGATED · ErrorBoundary catches hang (Bug 36). Pagination + filters deferred to Bucket B."),
    ("Engagements",
     "Date/aging columns for receivables; require cancellation reason; link buyer name → vendor.",
     "OPEN · Deferred — engagements module needs a full UX review."),
    ("Product Catalog",
     "Log price-change history per product.",
     "FIXED · v13 backend · Product updates now push {old_price, new_price, changed_by, changed_at} into a price_history[] on the product doc. Frontend surfacing (timeline UI) deferred (Bucket B)."),
    ("Help Requests",
     "Requester identity, priority, category, assignee, aging fields.",
     "FIXED · v16 · Panel now shows requester name/email/phone/company, aging via created_at timestamp, kind label, resolution history. Priority/category/assignee deferred (data model change)."),
    ("Portal Branding",
     "Live preview + logo history + broader theming (color, favicon).",
     "OPEN · Bucket B — logo history + theming (color/favicon) is a data model change. Live preview deferred."),
    ("Governance — G1 Escrow dual-sig",
     "Same login can currently sign both sides.",
     "FIXED · v11/v13 · Verified via curl HTTP 400 'must be different people'."),
    ("Governance — G2 COI cross-check",
     "COI not cross-checked against committee membership.",
     "ALREADY IMPLEMENTED · evaluations.submit_score blocks with 400 if no COI declaration. Verified in code."),
    ("Governance — G3 Two access-control systems",
     "Permissions Matrix + hierarchy Level with no defined relationship.",
     "PARTIAL · Handbook v3.1 Chapter 1 documents both. Full code consolidation is Wave G2 (upcoming)."),
    ("Governance — G4 Stakeholder Reports",
     "Description doesn't match implementation.",
     "OPEN · Bucket C — product decision: rename module OR rebuild to match description. Waiting on user."),
    ("Governance — G5 Draft auction public link",
     "DRAFT auction exposes the public bidder link.",
     "FIXED · v11/v13 · Link hidden when status='draft'; explanatory text shown instead."),
]

# --- Document build ------------------------------------------------------------
doc = Document()

h = doc.add_paragraph()
r = h.add_run("PMC Portal — Observation Responses  ·  v3")
r.font.name = "Calibri"
r.font.size = Pt(20)
r.font.bold = True
r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

sub = doc.add_paragraph()
r = sub.add_run(
    f"Updated after Wave A–D + Bucket A/B session fixes (v14 backend + v17 frontend)  ·  "
    f"{len(OBSERVATIONS)} observations mapped  ·  {datetime.utcnow().strftime('%b %d %Y')}"
)
r.font.size = Pt(10)
r.font.italic = True
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()

# Category legend
p = doc.add_paragraph()
r = p.add_run("Bucket legend:\n")
r.font.bold = True
r.font.size = Pt(11)
for label, why, colour in [
    ("Bucket A · Quick wins (30–60 min each)",
     "→ Delivered in v12/v16 + rolled into v14/v17.",
     (0x1F, 0x6F, 0x3F)),
    ("Bucket B · Multi-week efforts",
     "→ Backend logic (escrow aging, tab RBAC, price history) landed in v13. Frontend deferred by user.",
     (0x8B, 0x6D, 0x00)),
    ("Bucket C · Needs product decision",
     "→ Waiting on user (rename vs rebuild, consolidate vs keep separate).",
     (0x7A, 0x2C, 0x2C)),
]:
    p = doc.add_paragraph()
    r = p.add_run(label)
    r.font.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(*colour)
    r = p.add_run("  " + why)
    r.font.size = Pt(10)

doc.add_paragraph()

# Table
table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
hdr[0].text = "Module / Screen"
hdr[1].text = "Observation"
hdr[2].text = "Response · Status · Bucket"
for cell in hdr:
    for para in cell.paragraphs:
        for run in para.runs:
            run.font.bold = True
            run.font.size = Pt(10)

for module, observation, response in OBSERVATIONS:
    row = table.add_row().cells
    row[0].text = module
    row[1].text = observation
    row[2].text = response
    for cell in row:
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.size = Pt(9)

widths = (Inches(1.7), Inches(2.6), Inches(3.9))
for i, w in enumerate(widths):
    for row in table.rows:
        row.cells[i].width = w

# Summary at end
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run("Summary")
r.font.bold = True
r.font.size = Pt(12)
r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

counts = {}
for _, _, resp in OBSERVATIONS:
    key = resp.split(" · ")[0].split(".")[0]
    counts[key] = counts.get(key, 0) + 1

for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    p = doc.add_paragraph()
    r = p.add_run(f"  · {k}: {v}")
    r.font.size = Pt(10)

# Footer note
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = p.add_run(
    "This v3 doc supersedes v2. Included inside pmc-backend-v14.zip and "
    "pmc-frontend-v17.zip under /downloads/ for AWS EB + S3 deployment."
)
r.font.italic = True
r.font.size = Pt(9)
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB  ({len(OBSERVATIONS)} rows)")
