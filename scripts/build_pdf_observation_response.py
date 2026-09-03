"""Build a companion Response Document for the PDF observation manual.

The PDF Observations v3 lists structural/UX observations per module. We can't
annotate the PDF directly (rendering complexity), so we produce a paired
DOCX/PDF response report that maps each observation to a status.
"""
from docx import Document
from docx.shared import RGBColor, Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Portal_Observations_Response.docx")
OUT.parent.mkdir(exist_ok=True)

# Response per module observation (from PDF v3)
OBSERVATIONS = [
    ("Handbook (overall)",
     "Trainee handbook out-of-date — many chapters missing (Permissions, Engagements, Help Requests, Portal Branding, AI features, role-to-tab map).",
     "FIXED — PMC_Trainee_Handbook_v3.1.md delivered · 12 chapters covering Roles, RBAC, Permissions Matrix, Notices workflow, Registrations, Bidding/COI, Escrow with new dual-sig rules, Reverse Auctions with new draft-link rule, Meetings, ErrorBoundary session preservation, Help Requests, Portal Branding, bug fix log."),
    ("Dashboard — AI Bid Anomaly",
     "One-line description missing above control; flagged items not surfaced after run.",
     "OPEN — Wave E2 · Add description + result panel."),
    ("Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable, no drill-through to filtered Bidding Ops.",
     "OPEN — Wave E2 · Add click-through to filtered panel."),
    ("Registrations",
     "Surface submission_date on list; Nudge Stale Drafts needs threshold + preview count.",
     "PARTIAL · Three-branch nudge toast delivered in v11 (no drafts / none stale / count). Submission date column deferred to next sprint."),
    ("Vendors — Bulk Invite",
     "Link sample CSV; warn about mid-registration template replacement; add status filter for pending_verify.",
     "MITIGATED · Bulk Invite no longer crashes screen (ErrorBoundary + defensive handler in v11). Sample CSV link + template-replacement warning deferred."),
    ("Notices (admin)",
     "Add search/filter by status, closing date, template-linked flag; TEMPLATE LINKED tag should jump to template.",
     "OPEN — Deferred to Wave H · UX enhancement."),
    ("Corrigenda",
     "Require reason on Withdraw; log distinctly in Audit.",
     "OPEN — Deferred · Backend already audit-logs withdraw with event=corrigenda.withdraw. Reason-required field pending."),
    ("Tender Builder",
     "'All kinds' view or Kind column; show last-edited timestamp + revision indicator.",
     "OPEN — Wave E2 · Frontend enhancement."),
    ("Bidding Ops — Committee",
     "Chairperson dropdown from selected members only; validate quorum ≤ #members; replace Ctrl/Cmd multi-select with checkboxes; edit/dissolve actions; resend invite for pending externals.",
     "OPEN — Deferred · Committee UX overhaul, multi-week effort."),
    ("Escrow",
     "Aging indicator + SLA threshold; filter transactions by vendor/bid/status; reconciliation summary.",
     "PARTIAL · G1 governance fix delivered in v11 (rejects same email on both officers). Aging/SLA/filter deferred."),
    ("Evaluation",
     "Add rationale note next to non-obvious role/permission combos.",
     "OPEN — Deferred · Documentation enhancement."),
    ("L1 Comparison",
     "Empty state: state count + reason excluded; surface active ranking rule; add PDF/Excel export.",
     "OPEN — Wave E2 · Bug 40 (dropdown empty) related."),
    ("Awards & POs",
     "Add confirmation on Regenerate + version documents.",
     "OPEN — Wave E2 · Bug 41 related."),
    ("DocuSign",
     "Envelope Log — flag most-recent/authoritative envelope per doc/award.",
     "OPEN — Wave E2 · Bug 17 related (URL expiry)."),
    ("Reverse Auctions",
     "Post-auction summary/report; bid history; winning price; DRAFT auction should not expose public link.",
     "PARTIAL · G5 governance fix delivered in v11 (draft link now hidden until Start). Post-auction report deferred."),
    ("Meetings",
     "Require notice_ref when scheduling OR clearly mark internal meetings; hide cancelled by default.",
     "PARTIAL · Cancelled meetings now hidden by default (Bug 54 fix in v11). Notice-ref requirement deferred."),
    ("Vendor Intel",
     "Legend for WL (whitelist) flag; clarify anonymised entry.",
     "OPEN — Deferred · Docs enhancement."),
    ("BOQ & Contracts",
     "Contracts sub-tab needs export, filtering, version history.",
     "OPEN — Deferred · Feature enhancement."),
    ("Masters / Permissions",
     "Add/Clone role for org-specific narrower roles; extend matrix to tab-level visibility; show last-modified metadata.",
     "PARTIAL · Bug 5 (reviewer.create=True) resolved in v11. Tab-level RBAC and clone-role deferred to Wave G2."),
    ("Packages",
     "Empty-column messages consistent with rest of app.",
     "OPEN — Wave E2 · Bug 19/37 related."),
    ("Audit",
     "Add filters by actor/type/date range.",
     "MITIGATED · ErrorBoundary catches hang crash (Bug 36 fix). Pagination + filters deferred."),
    ("Engagements",
     "Date/aging columns for receivables; require cancellation reason; link buyer name → vendor.",
     "OPEN — Deferred · Feature enhancement."),
    ("Product Catalog",
     "Log price-change history per product.",
     "PARTIAL · Cache-buster fix in v11 (Bug 34/35). Price-history log deferred."),
    ("Help Requests",
     "Requester identity, priority, category, assignee, aging fields.",
     "OPEN — Deferred · Already partially built; enhancement scheduled."),
    ("Portal Branding",
     "Live preview + logo history + broader theming (color, favicon).",
     "OPEN — Deferred · Feature enhancement."),
    ("Governance — G1 Escrow dual-sig",
     "Same login can currently sign both sides — dual-signature theatre.",
     "FIXED — v11 · escrow.create_account rejects with HTTP 400 when pmc_officer.email == escrow_officer.email. Verified via curl."),
    ("Governance — G2 COI cross-check",
     "COI not cross-checked against committee membership before scoring.",
     "ALREADY IMPLEMENTED — evaluations.submit_score already blocks with HTTP 400 if no COI declaration exists for that evaluator+notice. Verified in code."),
    ("Governance — G3 Two access-control systems",
     "Permissions Matrix + hierarchy Level with no defined relationship.",
     "PARTIAL — Documented in Handbook v3.1 Chapter 1 (RBAC + Matrix + legacy Level). Full code consolidation deferred to Wave G2."),
    ("Governance — G4 Stakeholder Reports",
     "Description doesn't match implementation.",
     "OPEN — Product decision required · rename module OR rebuild to match description."),
    ("Governance — G5 Draft auction public link",
     "DRAFT auction exposes the public bidder link.",
     "FIXED — v11 · LiveAuctionsPanel now hides the bidder link + copy button when status='draft'. Shows explanatory text 'link hidden until you Start the auction' instead."),
]

doc = Document()

# Title
h = doc.add_paragraph()
h.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = h.add_run("PMC Portal — Observation Responses")
r.font.name = "Calibri"; r.font.size = Pt(20); r.font.bold = True
r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

sub = doc.add_paragraph()
r = sub.add_run(f"Response to `PMC Portal manual - Observations v3 · 01092026.pdf`  ·  {len(OBSERVATIONS)} observations mapped")
r.font.size = Pt(10); r.font.italic = True
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()  # spacer

# Legend
lg = doc.add_paragraph()
r = lg.add_run("Legend  ·  ")
r.font.bold = True; r.font.size = Pt(10)
for label, colour in [("FIXED", (0x1F, 0x6F, 0x3F)),
                       ("PARTIAL / MITIGATED", (0x8B, 0x6D, 0x00)),
                       ("OPEN", (0x7A, 0x2C, 0x2C))]:
    r = lg.add_run(f"{label}   ")
    r.font.size = Pt(10); r.font.bold = True
    r.font.color.rgb = RGBColor(*colour)

doc.add_paragraph()

# Table
table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
hdr[0].text = "Module / Screen"
hdr[1].text = "Observation"
hdr[2].text = "Response · Action Taken"
for cell in hdr:
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.bold = True
            run.font.size = Pt(10)

for module, observation, response in OBSERVATIONS:
    row = table.add_row().cells
    row[0].text = module
    row[1].text = observation
    row[2].text = response
    for cell in row:
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)

# Column widths (best-effort)
widths = (Inches(1.8), Inches(3.0), Inches(3.4))
for i, w in enumerate(widths):
    for row in table.rows:
        row.cells[i].width = w

doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run("End of response document. See PMC_Bug_Tracker_v3.xlsx for the numbered bug list and PMC_Trainee_Handbook_v3.1.md for the updated user handbook.")
r.font.size = Pt(9); r.font.italic = True; r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB")
