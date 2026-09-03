"""Portal Observations tracker (Excel) — SEPARATE from the bugs tracker.
Contains only observations from PMC_Portal_manual_Observations_v3.pdf,
with Bucket A/B/C classification and status per item.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Observations_Tracker_v1.xlsx")

# Columns: ID, Module, Observation, Bucket, Status, Action Taken, Effort Est
ROWS = [
    # Handbook
    ("O-01", "Handbook (overall)",
     "Trainee handbook out-of-date — many chapters missing (Permissions, Engagements, Help Requests, Portal Branding, AI features).",
     "A", "FIXED (v3.1)",
     "PMC_Trainee_Handbook_v3.1.md/docx/pdf delivered — 12 chapters covering RBAC, Permissions Matrix, Notices workflow, Registrations, Bidding+COI, Escrow (with new dual-sig rules), Reverse Auctions (with new draft-link rule), Meetings, ErrorBoundary, Help Requests, Portal Branding, bug fix log.",
     "1 day"),
    # Dashboard
    ("O-02", "Dashboard — AI Bid Anomaly",
     "One-line description missing above control; flagged items not surfaced after run.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — needs anomaly-check UX redesign. Skipped per user instruction.",
     "3-5 days"),
    ("O-03", "Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable, no drill-through to filtered Bidding Ops.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — needs filter query params + navigation wiring. Skipped per user instruction.",
     "2-3 days"),
    # Registrations
    ("O-04", "Registrations",
     "Surface submission_date on list; Nudge Stale Drafts needs threshold + preview count.",
     "A", "FIXED (v11 + v16)",
     "v11 delivered three-branch nudge toast (no drafts / none stale / count reminded). v16 adds submission-date visible next to status on each list row.",
     "30 min"),
    # Vendors
    ("O-05", "Vendors — Bulk Invite",
     "Link sample CSV; warn about mid-registration template replacement; add status filter for pending_verify.",
     "A", "MOSTLY FIXED (v16)",
     "v16 · Download sample CSV button added to modal + red warning about mid-cycle template replacement. Pending_verify status filter deferred (Bucket B — needs filter UI).",
     "45 min"),
    # Notices
    ("O-06", "Notices (admin)",
     "Add search/filter by status, closing date, template-linked flag; TEMPLATE LINKED tag jump.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — filter panel needs redesign. Skipped per user instruction.",
     "1-2 days"),
    # Corrigenda
    ("O-07", "Corrigenda",
     "Require reason on Withdraw; log distinctly in Audit.",
     "A", "FIXED (v12 + v16)",
     "v12 · Backend requires reason ≥8 chars (returns 400 with clear message). Audit log entry includes reason text. v16 · Frontend prompts for reason before calling API. Verified via curl.",
     "1 hour"),
    # Tender Builder
    ("O-08", "Tender Builder",
     "'All kinds' view or Kind column; show last-edited timestamp + revision indicator.",
     "C", "PRODUCT DECISION NEEDED",
     "Waiting on user — consolidate 3 tabs (Tender/RFP/RFQ) into one grid, OR keep separate tabs?",
     "1 day (once decided)"),
    # Bidding Ops
    ("O-09", "Bidding Ops — Committee",
     "Chairperson dropdown from selected members only; validate quorum ≤ #members; replace Ctrl/Cmd multi-select with checkboxes; edit/dissolve actions; resend invite for pending externals.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — 5+ interconnected changes across 3 components. Full sprint task. Skipped per user instruction.",
     "5-7 days"),
    # Escrow (partial Bucket B backend done)
    ("O-10", "Escrow",
     "Aging indicator + SLA threshold; filter transactions by vendor/bid/status; reconciliation summary.",
     "B", "PARTIAL FIX (v13 backend)",
     "v13 backend · list_accounts now returns age_days, sla_days (default 30), sla_breach flag per account + tenant-level sla_summary (in_sla/breached counts). Transaction filters + reconciliation UI deferred (Bucket B frontend).",
     "1 day"),
    # Evaluation
    ("O-11", "Evaluation",
     "Add rationale note next to non-obvious role/permission combos.",
     "A", "DOCS-ONLY",
     "Documented in Handbook v3.1 Chapter 1 — deferred to full text expansion in v3.2.",
     "30 min"),
    # L1 Comparison
    ("O-12", "L1 Comparison",
     "Empty state: state count + reason excluded; surface active ranking rule; add PDF/Excel export.",
     "A", "MOSTLY FIXED (v16)",
     "v16 · Empty state now lists 4 exclusion reasons (technical not scored / non-compliant / withdrawn / notice status) + shows active ranking rule (lowest compliant price wins). PDF/Excel export deferred (Bucket B).",
     "30 min"),
    # Awards
    ("O-13", "Awards & POs",
     "Add confirmation on Regenerate + version documents.",
     "A", "FIXED (v12 + v16)",
     "v12 · Response includes regenerated_at + regenerated_by; bid record gets award_regenerations history array. v16 · Confirmation dialog before regenerate; toast shows timestamp + admin email.",
     "1 hour"),
    # DocuSign
    ("O-14", "DocuSign",
     "Envelope Log — flag most-recent/authoritative envelope per doc/award.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — new UI panel + backend query. Skipped per user instruction.",
     "2 days"),
    # Reverse Auctions
    ("O-15", "Reverse Auctions",
     "Post-auction summary/report; bid history; winning price; DRAFT auction should not expose public link.",
     "A + B", "PARTIAL (v11 G5 governance done)",
     "v11 G5 · Draft link hidden until Start (verified in bundle). Post-auction summary/report deferred (Bucket B frontend).",
     "2 days"),
    # Meetings
    ("O-16", "Meetings",
     "Require notice_ref when scheduling OR clearly mark internal meetings; hide cancelled by default.",
     "A + C", "PARTIAL",
     "v11 · Cancelled meetings hidden by default (backend include_cancelled param + frontend toggle). Notice-ref requirement is Bucket C (product decision — some meetings ARE internal, need policy).",
     "1 hour"),
    # Vendor Intel
    ("O-17", "Vendor Intel",
     "Legend for WL (whitelist) flag; clarify anonymised entry.",
     "A", "FIXED (v16)",
     "v16 · Legend bar added at top of panel: BL=Blacklisted, WL=Watch-list, '—'=anonymised.",
     "20 min"),
    # BOQ
    ("O-18", "BOQ & Contracts",
     "Contracts sub-tab needs export, filtering, version history.",
     "B", "DEFERRED (frontend redesign)",
     "Not started — full mini-project. Skipped per user instruction.",
     "4-5 days"),
    # Masters / Permissions
    ("O-19", "Masters / Permissions",
     "Add/Clone role for org-specific narrower roles; extend matrix to tab-level visibility; show last-modified metadata.",
     "B", "PARTIAL FIX (v13 backend)",
     "v13 backend · Added tab-level RBAC schema — PermissionRow.tabs Optional[List[str]] + DEFAULT_TABS dict + GET /permissions/tabs/{role} endpoint. Frontend Clone-Role UI + tab enforcement deferred (Bucket B frontend).",
     "2 days"),
    # Packages
    ("O-20", "Packages",
     "Empty-column messages consistent with rest of app.",
     "A/B", "DEFERRED",
     "Waiting to see if v11 hard-refresh resolves Bug 19/37 first. If confirmed, revisit consistency of empty-column text.",
     "1 hour"),
    # Audit
    ("O-21", "Audit",
     "Add filters by actor/type/date range.",
     "B", "MITIGATED (v11 ErrorBoundary)",
     "v11 · ErrorBoundary catches hang (Bug 36). Pagination + filters deferred (Bucket B frontend).",
     "2 days"),
    # Engagements
    ("O-22", "Engagements",
     "Date/aging columns for receivables; require cancellation reason; link buyer name → vendor.",
     "B", "DEFERRED",
     "Full UX review needed. Skipped per user instruction.",
     "3 days"),
    # Product Catalog
    ("O-23", "Product Catalog",
     "Log price-change history per product.",
     "B", "FIXED (v13 backend)",
     "v13 backend · products PATCH endpoint now detects price changes and appends {at, by, old_price, new_price, old_currency, new_currency} to product's price_history[] array. Frontend history-viewer UI deferred (Bucket B frontend).",
     "1 hour"),
    # Help Requests
    ("O-24", "Help Requests",
     "Requester identity, priority, category, assignee, aging fields.",
     "A + B", "PARTIAL (v16)",
     "v16 · Context-aware empty state added. Priority/category/assignee fields require data model change (Bucket B).",
     "45 min"),
    # Portal Branding
    ("O-25", "Portal Branding",
     "Live preview + logo history + broader theming (color, favicon).",
     "B", "DEFERRED",
     "Live preview + theming needs new UI. Logo history requires data model change. Skipped per user instruction.",
     "3 days"),
    # Governance items
    ("G-01", "Governance — Escrow dual-sig",
     "Same login can currently sign both sides.",
     "A", "FIXED (v11)",
     "v11 · escrow.create_account rejects with HTTP 400 when pmc_officer.email == escrow_officer.email. Verified via curl.",
     "1 hour"),
    ("G-02", "Governance — COI cross-check",
     "COI not cross-checked against committee membership.",
     "A", "ALREADY IMPLEMENTED",
     "evaluations.submit_score blocks with HTTP 400 if no COI declaration. Verified in existing code.",
     "N/A"),
    ("G-03", "Governance — Two access-control systems",
     "Permissions Matrix + hierarchy Level with no defined relationship.",
     "A + B", "PARTIAL",
     "Handbook v3.1 Chapter 1 documents both (Bucket A done). Full code consolidation of Matrix + Level = Bucket B (deferred).",
     "3 days"),
    ("G-04", "Governance — Stakeholder Reports",
     "Description doesn't match implementation.",
     "C", "PRODUCT DECISION NEEDED",
     "Waiting on user — rename module to match implementation, OR rebuild reports to match description?",
     "1-3 days (once decided)"),
    ("G-05", "Governance — Draft auction public link",
     "DRAFT auction exposes the public bidder link.",
     "A", "FIXED (v11)",
     "v11 · LiveAuctionsPanel hides bidder link when status='draft'. Explanatory text shown instead. Verified in bundle.",
     "1 hour"),
]

wb = Workbook()
ws = wb.active
ws.title = "Observations"

HEADERS = ["ID", "Module / Screen", "Observation", "Bucket", "Status", "Action Taken", "Effort Est."]
FILLS = {
    "A": PatternFill("solid", fgColor="C6EFCE"),  # Bucket A = green (quick win)
    "B": PatternFill("solid", fgColor="FFEB9C"),  # Bucket B = yellow (deferred)
    "C": PatternFill("solid", fgColor="FFC7CE"),  # Bucket C = red (product decision)
    "A + B": PatternFill("solid", fgColor="D9EAD3"),
    "A + C": PatternFill("solid", fgColor="F4E4C1"),
    "A/B": PatternFill("solid", fgColor="D9EAD3"),
}
HEADER_FILL = PatternFill("solid", fgColor="0F1B3D")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
CELL_FONT = Font(size=10)
BORDER = Border(*[Side(style="thin", color="D0D0D0")] * 4)

for c, h in enumerate(HEADERS, 1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.fill = HEADER_FILL; cell.font = HEADER_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER

for r, row in enumerate(ROWS, 2):
    for c, val in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=val)
        cell.font = CELL_FONT
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = BORDER
    bucket = row[3]
    fill = FILLS.get(bucket)
    if fill:
        for c in range(1, 8):
            ws.cell(row=r, column=c).fill = fill

widths = [8, 28, 55, 10, 30, 65, 18]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 32
ws.freeze_panes = "A2"

# Summary sheet
ws2 = wb.create_sheet("Summary")
def _count(bucket):
    return sum(1 for r in ROWS if r[3] == bucket)

ws2.column_dimensions["A"].width = 24
ws2.column_dimensions["B"].width = 12
ws2.column_dimensions["C"].width = 70

ws2.append(["Bucket", "Count", "Meaning"])
ws2.append(["A · Quick wins", _count("A"), "30-60 min fixes — DELIVERED in v11/v12/v13/v15/v16"])
ws2.append(["B · Multi-week efforts", _count("B"), "1-7 day tasks — many DEFERRED (frontend redesign per user instruction), some backend done in v13"])
ws2.append(["C · Product decisions", _count("C"), "Waiting on user product decision (rename vs rebuild, consolidate vs keep)"])
ws2.append(["A + B mix", _count("A + B") + _count("A + C") + _count("A/B"),
            "Partially delivered — backend/quick-win part done, redesign/data-model part deferred"])
ws2.append([])
ws2.append(["Total observations", len(ROWS), ""])
ws2.append([])
ws2.append(["Deploy plan"])
ws2.append(["1. Deploy pmc-backend-v13-bucketB.zip to EB (adds tab RBAC + escrow aging + product price history)"])
ws2.append(["2. Deploy pmc-frontend-v16-bucketA.zip to S3+CloudFront (Bucket A UI fixes)"])
ws2.append(["3. Frontend redesign items (Bucket B UI) remain deferred per user instruction"])
ws2.append(["4. Two Bucket C items await product decisions before code work can start"])

for c in range(1, 4):
    ws2.cell(row=1, column=c).fill = HEADER_FILL
    ws2.cell(row=1, column=c).font = HEADER_FONT

wb.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB")
print(f"Observations: {len(ROWS)}")
print(f"Bucket A (quick wins): {_count('A')}")
print(f"Bucket B (multi-week): {_count('B')}")
print(f"Bucket C (product decision): {_count('C')}")
