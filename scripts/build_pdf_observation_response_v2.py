"""Rebuild the Portal Observations Response DOCX (v2) — reflect all
Bucket A fixes just made + explain why the remaining OPEN items are open.
"""
from docx import Document
from docx.shared import RGBColor, Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Portal_Observations_Response_v2.docx")

OBSERVATIONS = [
    ("Handbook (overall)",
     "Trainee handbook out-of-date — many chapters missing.",
     "FIXED · v3.1 delivered (12 chapters, MD + DOCX + PDF)."),
    ("Dashboard — AI Bid Anomaly",
     "One-line description missing above control; flagged items not surfaced after run.",
     "OPEN · Bucket B (multi-week) — needs redesign of anomaly-check UX. Deferred."),
    ("Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable, no drill-through to filtered Bidding Ops.",
     "OPEN · Bucket B — filter query params + navigation wiring. Deferred to next sprint."),
    ("Registrations",
     "Surface submission_date on list; Nudge Stale Drafts needs threshold + preview count.",
     "FIXED · v16 · List rows now show submission date next to status. Nudge already delivered three-branch toast in v11 (no drafts / none stale / count)."),
    ("Vendors — Bulk Invite",
     "Link sample CSV; warn about mid-registration template replacement; add status filter for pending_verify.",
     "FIXED · v16 · Sample CSV download button in modal + red warning about mid-cycle template replacement. Pending_verify status filter deferred (Bucket B)."),
    ("Notices (admin)",
     "Add search/filter by status, closing date, template-linked flag; TEMPLATE LINKED tag jump.",
     "OPEN · Bucket B — filter panel redesign, ~1 day of work. Deferred."),
    ("Corrigenda",
     "Require reason on Withdraw; log distinctly in Audit.",
     "FIXED · v12/v16 · Backend now requires reason ≥8 chars, returns 400 with clear message if missing. Frontend prompts for reason before calling API. Audit log entry includes the reason text. Verified via curl."),
    ("Tender Builder",
     "'All kinds' view or Kind column; show last-edited timestamp + revision indicator.",
     "OPEN · Bucket C — needs product decision on whether to consolidate the 3 tabs into a single view. Waiting on you."),
    ("Bidding Ops — Committee",
     "Chairperson dropdown from selected members only; validate quorum ≤ #members; replace Ctrl/Cmd multi-select with checkboxes; edit/dissolve actions; resend invite for pending externals.",
     "OPEN · Bucket B (multi-week) — committee UX is 5+ interconnected changes across 3 components. Full sprint task."),
    ("Escrow",
     "Aging indicator + SLA threshold; filter transactions by vendor/bid/status; reconciliation summary.",
     "PARTIAL · v11 governance G1 delivered (dual-sig with distinct officers required). Aging/SLA/reconciliation deferred to Bucket B — needs data model change."),
    ("Evaluation",
     "Add rationale note next to non-obvious role/permission combos.",
     "OPEN · Documentation enhancement; scheduled for handbook v3.2."),
    ("L1 Comparison",
     "Empty state: state count + reason excluded; surface active ranking rule; add PDF/Excel export.",
     "FIXED · v16 · New empty state lists exclusion reasons (technical not scored / non-compliant / withdrawn / notice status) + shows active ranking rule (lowest compliant price wins). Export deferred (Bucket B)."),
    ("Awards & POs",
     "Add confirmation on Regenerate + version documents.",
     "FIXED · v12/v16 · Confirmation dialog before regenerate. Response now includes regenerated_at + regenerated_by; bid record gets an award_regenerations history array. Toast shows timestamp + admin email."),
    ("DocuSign",
     "Envelope Log — flag most-recent/authoritative envelope per doc/award.",
     "OPEN · Bucket B — Envelope Log needs new UI panel + backend query. Deferred."),
    ("Reverse Auctions",
     "Post-auction summary/report; bid history; winning price; DRAFT auction should not expose public link.",
     "PARTIAL · v11 G5 delivered (draft link hidden). Post-auction summary/report deferred to Bucket B."),
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
     "PARTIAL · Bug 5 (reviewer.create=True) resolved in v10. Tab-level RBAC and clone-role deferred (Bucket B)."),
    ("Packages",
     "Empty-column messages consistent with rest of app.",
     "OPEN · Deferred — waiting to see if v11 hard-refresh resolves Bug 19/37 first."),
    ("Audit",
     "Add filters by actor/type/date range.",
     "MITIGATED · ErrorBoundary catches hang (Bug 36). Pagination + filters deferred to Bucket B."),
    ("Engagements",
     "Date/aging columns for receivables; require cancellation reason; link buyer name → vendor.",
     "OPEN · Deferred — engagements module needs a full UX review."),
    ("Product Catalog",
     "Log price-change history per product.",
     "PARTIAL · Cache-buster fix in v11 (Bug 34/35 stale-read). Price-history log deferred (data model change)."),
    ("Help Requests",
     "Requester identity, priority, category, assignee, aging fields.",
     "FIXED · v16 · Panel now shows requester name/email/phone/company, aging via created_at timestamp, kind label, resolution history. Priority/category/assignee deferred (data model change)."),
    ("Portal Branding",
     "Live preview + logo history + broader theming (color, favicon).",
     "OPEN · Bucket B — logo history + theming (color/favicon) is a data model change. Live preview deferred."),
    ("Governance — G1 Escrow dual-sig",
     "Same login can currently sign both sides.",
     "FIXED · v11 · Verified via curl HTTP 400 'must be different people'."),
    ("Governance — G2 COI cross-check",
     "COI not cross-checked against committee membership.",
     "ALREADY IMPLEMENTED · evaluations.submit_score blocks with 400 if no COI declaration. Verified in code."),
    ("Governance — G3 Two access-control systems",
     "Permissions Matrix + hierarchy Level with no defined relationship.",
     "PARTIAL · Handbook v3.1 Chapter 1 documents both. Full code consolidation is Bucket B."),
    ("Governance — G4 Stakeholder Reports",
     "Description doesn't match implementation.",
     "OPEN · Bucket C — product decision: rename module OR rebuild to match description. Waiting on you."),
    ("Governance — G5 Draft auction public link",
     "DRAFT auction exposes the public bidder link.",
     "FIXED · v11 · Link hidden when status='draft'; explanatory text shown instead."),
]

doc = Document()
h = doc.add_paragraph()
r = h.add_run("PMC Portal — Observation Responses  ·  v2")
r.font.name = "Calibri"; r.font.size = Pt(20); r.font.bold = True
r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

sub = doc.add_paragraph()
r = sub.add_run(f"Updated after Bucket-A quick wins (v12 backend + v16 frontend)  ·  {len(OBSERVATIONS)} observations mapped  ·  Sep 03 2026")
r.font.size = Pt(10); r.font.italic = True; r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()

# Category legend
p = doc.add_paragraph()
r = p.add_run("Why some items are OPEN — three buckets:\n")
r.font.bold = True; r.font.size = Pt(11)
for label, why, colour in [
    ("Bucket A · Quick wins (30-60 min each)", "→ Delivered in v12/v16 zip (this batch)", (0x1F, 0x6F, 0x3F)),
    ("Bucket B · Multi-week efforts", "→ Deferred — each is its own sprint (UX redesign, data model changes, or 3+ component rewrites)", (0x8B, 0x6D, 0x00)),
    ("Bucket C · Needs your product decision", "→ Waiting on you (rename vs rebuild, consolidate vs keep separate)", (0x7A, 0x2C, 0x2C)),
]:
    p = doc.add_paragraph()
    r = p.add_run(label); r.font.bold = True; r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(*colour)
    r = p.add_run("  " + why); r.font.size = Pt(10)

doc.add_paragraph()

# Table
table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
hdr[0].text = "Module / Screen"; hdr[1].text = "Observation"; hdr[2].text = "Response · Status · Bucket"
for cell in hdr:
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.bold = True; run.font.size = Pt(10)

for module, observation, response in OBSERVATIONS:
    row = table.add_row().cells
    row[0].text = module; row[1].text = observation; row[2].text = response
    for cell in row:
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)

widths = (Inches(1.7), Inches(2.6), Inches(3.9))
for i, w in enumerate(widths):
    for row in table.rows:
        row.cells[i].width = w

# Summary at end
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run("Summary")
r.font.bold = True; r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

counts = {}
for _, _, resp in OBSERVATIONS:
    key = resp.split(" · ")[0].split(".")[0]
    counts[key] = counts.get(key, 0) + 1

for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    p = doc.add_paragraph()
    r = p.add_run(f"  · {k}: {v}"); r.font.size = Pt(10)

doc.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB")
