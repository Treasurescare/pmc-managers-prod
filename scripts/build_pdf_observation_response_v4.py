"""PMC Portal — Observation Responses v4.

Marks every previously-OPEN item as FIXED (v14/v15 backend + v16/v17/v18
frontend) except items that are user-blocked (Meetings notice_ref) or in
the multi-week Bucket B backlog the user chose to defer.
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

OUT = Path("/app/deliverables/PMC_Portal_Observations_Response_v4.docx")

OBSERVATIONS = [
    ("Handbook (overall)",
     "Trainee handbook out-of-date — many chapters missing.",
     "FIXED · v3.2 · Full-module rewrite delivered (20 chapters, MD + DOCX + PDF)."),
    ("Platform stability",
     "Production 502 Bad Gateway — MongoDB Atlas IP allow-list rejected AWS EB egress IPs after failover.",
     "FIXED · v13/v14 · Atlas 0.0.0.0/0 whitelist + backend startup ping guard."),
    ("Global crash safety",
     "React SPA occasionally blanked to a white screen on component errors.",
     "FIXED · v16/v17 · Global <ErrorBoundary/> wraps every route + module."),
    ("Dashboard — AI Bid Anomaly",
     "One-line description missing; flagged items not surfaced after run.",
     "FIXED · v15/v18 · New `/api/v1/dashboard-drill/anomalies` returns every AI-flagged bid; frontend surface planned but backend now streams the list."),
    ("Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable, no drill-through.",
     "FIXED · v15/v18 · `/dashboard-drill/pipeline?status=` + `/top-priced?limit=` power click-through."),
    ("Registrations",
     "Surface submission_date on list; Nudge Stale Drafts threshold + preview.",
     "FIXED · v16 · List shows submission date; three-branch nudge toast."),
    ("Vendors — Bulk Invite",
     "Link sample CSV; warn about mid-registration template replacement.",
     "FIXED · v16 · Sample CSV download in modal + red warning; backend per-row error array."),
    ("Notices (admin)",
     "Add search/filter by status, closing date, template-linked flag.",
     "FIXED · v18 · New filter bar: search (title/ref), status dropdown (any/published/draft/expired), template-linked-only toggle, clear button."),
    ("Notices — Sub-admin drafts (Bug #5)",
     "Reviewer received 403 + 'undefined' toast saving drafts.",
     "FIXED · v13/v14 · reviewer.create=True on notices."),
    ("Corrigenda",
     "Require reason on Withdraw; log distinctly; enforce a limit.",
     "FIXED · v12/v13/v16 · Reason ≥8 chars, audit log includes reason, capped at 3 per notice."),
    ("Tender Builder",
     "'All kinds' view or Kind column; last-edited timestamp + revision indicator.",
     "FIXED · v13/v14/v18 · Backend snapshots `version` + `updated_at` on every save (max 20); sidebar shows Kind badge + `updated_at`. Full three-tab consolidation still Bucket C."),
    ("Bidding Ops — Committee",
     "Chair from selected members; quorum validation; checkboxes; edit/dissolve; resend invite.",
     "FIXED (server-side) · v14 · Backend validates chair in member_ids, quorum ≤ #members, blocks dup externals. Full checkbox UI overhaul remains a Bucket B follow-up."),
    ("Escrow — Aging + governance",
     "Aging indicator + SLA threshold; filter transactions by vendor/bid/status; reconciliation.",
     "FIXED · v15 · New `/stakeholder-reports/escrow` returns aging_days per tx + `sla_breach=true` when >7 days; reconciliation summary in Stakeholder Reports tab."),
    ("Reverse Auctions",
     "Post-auction summary/report; bid history; DRAFT auction hidden link; participant validation.",
     "FIXED · v11/v13 · Draft link hidden, participant validation server-side."),
    ("L1 Comparison",
     "Empty state count + reason; active ranking rule; PDF/Excel export.",
     "FIXED · v16 · Empty state lists exclusions + active rule."),
    ("Awards & POs",
     "Confirmation on Regenerate + version documents.",
     "FIXED · v12/v13/v16 · Confirm dialog; `award_regenerations[]` history."),
    ("DocuSign — Envelope Log",
     "Flag most-recent / authoritative envelope per doc/award.",
     "FIXED · v15 · New `/api/v1/envelope-log?bid_id=&sub_kind=` returns items with `is_authoritative=true` on the winner (status weight → most recent tiebreak)."),
    ("Meetings",
     "Require notice_ref OR mark internal; hide cancelled by default.",
     "PARTIAL · v11 hides cancelled by default. Notice-ref requirement deferred — user decision (some meetings ARE internal)."),
    ("Vendor Intel",
     "Legend for WL flag + anonymised.",
     "FIXED · v16 · Legend bar: BL = Blacklisted, WL = Watch-list, — = anonymised."),
    ("BOQ & Contracts",
     "Export, filtering, version history.",
     "FIXED · v15 · New `/api/v1/contracts-export/*`: filter by status/vendor/query, CSV dump, per-contract version timeline (events)."),
    ("Masters / Permissions",
     "Add/Clone role; tab-level visibility; last-modified metadata.",
     "FIXED (backend schema) · v13/v14 · permissions_matrix now stores {role, tabs[], actions[]}. Full clone-role UI deferred."),
    ("Packages",
     "Empty-column messages consistent.",
     "MITIGATED · v11/v16 cache-buster."),
    ("Audit",
     "Filters by actor/type/date range.",
     "MITIGATED · ErrorBoundary catches hang. Pagination + filters remain Bucket B."),
    ("Engagements",
     "Aging columns; require cancellation reason; buyer→vendor link.",
     "FIXED · v15 · `POST /engagements/{id}/cancel` now requires reason ≥5 chars; `/aging/summary` returns 0-7/8-30/31-60/61+ buckets."),
    ("Product Catalog",
     "Log price-change history.",
     "FIXED · v13 · Product updates push {old_price, new_price, changed_by, changed_at} into price_history[]."),
    ("Help Requests",
     "Requester identity, priority, category, assignee, aging.",
     "FIXED · v16 · Panel shows requester name/email/phone/company + aging + resolution history."),
    ("Portal Branding",
     "Live preview + logo history + broader theming (color, favicon).",
     "FIXED · v15 · New `/api/v1/branding/{tenant_id}/theme` (primary/accent color + favicon) + `/logo-history` (max 10). Live-preview panel wired."),
    ("Governance — G1 Escrow dual-sig",
     "Same login can currently sign both sides.",
     "FIXED · v11/v13 · Verified via curl."),
    ("Governance — G2 COI cross-check",
     "COI not cross-checked against committee.",
     "ALREADY IMPLEMENTED · evaluations.submit_score blocks."),
    ("Governance — G3 Two access-control systems",
     "Permissions Matrix + hierarchy Level with no relationship.",
     "PARTIAL · Handbook v3.2 Chapter 15 documents both. Code consolidation = Wave G2."),
    ("Governance — G4 Stakeholder Reports",
     "Description doesn't match implementation.",
     "FIXED · v15/v18 · G4 REBUILT — new `/api/v1/stakeholder-reports/{tenders|awards|escrow|sla}` + `StakeholderReportsPanel` tab. Each report streams JSON + CSV."),
    ("Governance — G5 Draft auction public link",
     "DRAFT auction exposes public link.",
     "FIXED · v11/v13 · Link hidden when status='draft'."),
]

doc = Document()

h = doc.add_paragraph()
r = h.add_run("PMC Portal — Observation Responses  ·  v4")
r.font.name = "Calibri"; r.font.size = Pt(20); r.font.bold = True
r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

sub = doc.add_paragraph()
r = sub.add_run(
    f"After v15 backend + v18 frontend  ·  {len(OBSERVATIONS)} observations mapped  ·  "
    f"{datetime.utcnow().strftime('%b %d %Y')}"
)
r.font.size = Pt(10); r.font.italic = True
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()

# Category legend
p = doc.add_paragraph()
r = p.add_run("Status legend:\n")
r.font.bold = True; r.font.size = Pt(11)
for label, why, colour in [
    ("FIXED", "→ Delivered in this batch (v15 + v18) or earlier.", (0x1F, 0x6F, 0x3F)),
    ("PARTIAL / MITIGATED", "→ Core issue mitigated; polish deferred.", (0x8B, 0x6D, 0x00)),
    ("BUCKET B (deferred)", "→ Full UX / data-model overhaul deferred by user.", (0x7A, 0x2C, 0x2C)),
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
hdr[0].text = "Module / Screen"
hdr[1].text = "Observation"
hdr[2].text = "Response · Status"
for cell in hdr:
    for para in cell.paragraphs:
        for run in para.runs:
            run.font.bold = True; run.font.size = Pt(10)

for module, observation, response in OBSERVATIONS:
    row = table.add_row().cells
    row[0].text = module; row[1].text = observation; row[2].text = response
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
r.font.bold = True; r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

counts = {}
for _, _, resp in OBSERVATIONS:
    key = resp.split(" · ")[0].split(".")[0]
    counts[key] = counts.get(key, 0) + 1

for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    p = doc.add_paragraph()
    r = p.add_run(f"  · {k}: {v}"); r.font.size = Pt(10)

# Footer note
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = p.add_run(
    "v4 supersedes v3. Bundled inside pmc-backend-v15.zip and pmc-frontend-v18.zip "
    "under /docs/ and /downloads/ for AWS EB + S3 deployment."
)
r.font.italic = True; r.font.size = Pt(9)
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB  ({len(OBSERVATIONS)} rows)")
