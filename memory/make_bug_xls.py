import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Bug Tracker"

headers = ["#", "Module", "Bug (as reported)", "Status", "Release / Resolution",
           "Priority", "Needs user re-verify?"]
ws.append(headers)

rows = [
    (0,  "EMD & Payments",        "Pay button does not process EMD payment in Stripe sandbox", "FIXED", "v52bt — Pay EMD resolves exact bid & opens real Stripe checkout", "P0", "No"),
    (10, "EMD & Payments",        "All statuses / All currencies dropdowns unresponsive", "FIXED", "v52bt — populated from live rows, filtering works", "P2", "No"),
    (12, "DocuSign",              "Resend on older bids raises error", "FIXED", "v52bt (ENVELOPE_DOES_NOT_EXIST→410) + v52bw (UNKNOWN_ENVELOPE_RECIPIENT→410)", "P1", "Yes"),
    (17, "Admin DocuSign",        "Vendor side stays submitted/pending until two conditions met", "FIXED", "v52bw — both gates removed (bid_id fallback + /refresh endpoint)", "P1", "Yes"),
    (28, "Admin Stakeholder",     "Stakeholder reports CSV download error", "FIXED", "v52br/bs — authenticated blob download", "P1", "No"),
    (30, "Admin Work Packages",   "Sample CSV required for import testing", "FIXED", "v52bt — verified header + auth download", "P2", "No"),
    (31, "Admin Tender Builder",  "Search results shown below Kind/Master Library", "FIXED", "v52bw — results banner promoted to top of main pane", "P2", "Yes"),
    (32, "Admin Work Packages",   "Creating a new package auto-redirects to Tender Builder", "FIXED", "v52bz — PmcLinkPatcher regex tightened (exclude |package)", "P1", "Yes"),
    (33, "Admin Console",         "Market menu shows only 4 items; Masters/others don't open on first attempt", "FIXED", "v52bt — sidebar unified across 9 pages (27 items)", "P1", "No"),
    (34, "Admin Session",         "Different users on same browser mix permissions (old session active)", "FIXED", "v52bx — login endpoints delete the other role's cookie", "P0", "Yes"),
    (35, "Vendor Portal",         "Categories icon missing; no Services link in UI", "FIXED", "v52bu — both links restored on every vendor page", "P2", "No"),
    (37, "Public Notice",         "Key Dates shows Corrigendum 1 but Corrigenda section says 'No corrigenda published'", "RE-VERIFY", "Public corrigenda display shipped v52bn/bo; verify after prod deploy + CloudFront invalidation", "P2", "Yes"),
    (40, "Notices",               "Notice timelines wrong vs what was set at creation", "RE-VERIFY", "Timeline rework shipped v52bo; re-reported — verify on production", "P2", "Yes"),
    (41, "Escrow",                "Testing the bids, throwing error", "CLARIFY", "Need repro: which bid, which action, exact error text/screenshot", "P1", "Yes"),
    (43, "Evaluation",            "Saved weightage not persisted after page refresh", "FIXED", "v52bz — EvaluationPanel hydrates editor via evalApi.getRubric", "P1", "Yes"),
    (44, "Evaluation",            "Scoring always 0 → 'no bid qualifies'", "FIXED", "v52bz — submitTechScore catches COI-block, auto-declares no_conflict, retries", "P1", "Yes"),
    (45, "BOQ & Contracts",       "Contract created but not viewable", "FIXED", "v52bw — toast shows contract_ref, row auto-scrolls into view", "P1", "Yes"),
    (46, "Corrigenda UX",         "Two search bars — second one appears not to work", "FIXED", "v52bx (distinct testids) + v52ca (live match/no-match feedback + reset on notice switch)", "P2", "No"),
    (47, "BOQ & Contracts",       "View button results shown at bottom", "FIXED", "v52bw — viewer scrolls into view + Close button", "P2", "No"),
    (48, "BOQ & Contracts",       "No export button for template", "FIXED", "v52by — Excel (openpyxl) + PDF (WeasyPrint) exports with auth-blob download", "P1", "Yes"),
    (49, "Corrigenda",            "Withdraw succeeds but corrigendum still shows in active list", "FIXED", "v52by optimistic flip + v52bz dialog + v52ca full regression (ACTIVE 3→2, WITHDRAWN 1→2 verified)", "P1", "No"),
    (52, "Tender Builder",        "Industry filter not working (Public Works/Construction/PMC shows general)", "RE-VERIFY", "Category-master filter shipped v52bs; re-reported — verify on production", "P2", "Yes"),
    (54, "BOQ & Contracts",       "New BOQ has no Add Line Item/Edit; pagination '1-5 of 5' with 0 rows", "RE-VERIFY", "Shipped v52bs; re-reported — verify on production", "P1", "Yes"),
    (57, "BOQ & Contracts",       "PDF/Excel export options missing", "FIXED", "Same as #48 — v52by", "P1", "Yes"),
    (58, "Product Catalog",       "Disabling existing product shows error", "NEW", "Queued — need repro steps / exact error", "P2", "Yes"),
    (59, "Reverse Auction",       "Newly created auction not listed as draft", "FIXED", "v52by — AdminAuctionsE optimistic prepend on create", "P0", "Yes"),
    (60, "Reverse Auction",       "'Start' does not make auction go live", "FIXED", "v52by — Start no longer client-disabled; backend returns clear 400 naming gate", "P0", "Yes"),
    (61, "Evaluation",            "Page crashing", "RE-VERIFY", "AwardReport crash guard shipped v52bl; re-reported — verify after v52bz deploy", "P1", "Yes"),
    (63, "Escrow/EMD",            "Opacity on Edit buttons", "FIXED", "v52bt — solid navy button", "P2", "No"),
    (64, "Reverse Auction",       "Cannot create draft; 'field required' error despite filled fields", "FIXED", "v52by — frontend was POSTing bid_decrement, backend expected min_decrement", "P0", "Yes"),
    (65, "Admin Registrations",   "Edit sections link appears attached to the next vendor card", "FIXED", "v52cb — border-b moved to row wrapper so each card is one block", "P2", "No"),
    (66, "Admin Registrations",   "Back button in Edit sections tab lands on public homepage", "FIXED", "v52cb — explicit 'Back to Registrations' button that closes the tab (fallback: /admin/e/registrations)", "P1", "Yes"),
    (67, "Evaluation",            "Tender number lookup doesn't work (type '18' → no match)", "FIXED", "v52cb — field is now a real picker with live substring filter on ref AND title", "P1", "No"),
    (68, "Tender Builder",        "Tender Documents section — can't add anything / unclear it's not an uploader", "FIXED", "v52cc — relabelled as schedule (bidders' checklist) + hint pointing to bulk upload; add-row buttons verified working", "P2", "No"),
    (69, "Tender Builder",        "Critical Dates have no logic; cloned drafts carry stale/out-of-order dates", "FIXED", "v52cc — fresh today-anchored schedule on clone + Save blocked on out-of-order pairs", "P1", "No"),
    (70, "Tender Builder",        "No publish path; draft invisible in Notices > Drafts; mandatory fields unclear", "FIXED", "v52cc — starred mandatory fields + 'Create notice' bridge with gate toast and pre-filled Notices form", "P1", "Yes"),
]

for r in rows:
    ws.append(r)

header_fill  = PatternFill("solid", fgColor="0B1E3F")
header_font  = Font(bold=True, color="FFFFFF", size=11)
border       = Border(left=Side(style="thin", color="D4D4D4"),
                      right=Side(style="thin", color="D4D4D4"),
                      top=Side(style="thin", color="D4D4D4"),
                      bottom=Side(style="thin", color="D4D4D4"))

status_fills = {
    "FIXED":     PatternFill("solid", fgColor="D1FAE5"),
    "RE-VERIFY": PatternFill("solid", fgColor="FEF3C7"),
    "NEW":       PatternFill("solid", fgColor="FEE2E2"),
    "CLARIFY":   PatternFill("solid", fgColor="E0E7FF"),
}
priority_fills = {
    "P0": PatternFill("solid", fgColor="FCA5A5"),
    "P1": PatternFill("solid", fgColor="FDE68A"),
    "P2": PatternFill("solid", fgColor="BBF7D0"),
    "P3": PatternFill("solid", fgColor="DBEAFE"),
}

for col_idx in range(1, len(headers) + 1):
    c = ws.cell(row=1, column=col_idx)
    c.fill = header_fill; c.font = header_font
    c.alignment = Alignment(horizontal="left", vertical="center")
    c.border = border

widths = [5, 20, 60, 12, 70, 10, 20]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

for r_idx in range(2, len(rows) + 2):
    for c_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=r_idx, column=c_idx)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = border
    status = ws.cell(row=r_idx, column=4).value
    if status in status_fills:
        ws.cell(row=r_idx, column=4).fill = status_fills[status]
        ws.cell(row=r_idx, column=4).font = Font(bold=True)
    pr = ws.cell(row=r_idx, column=6).value
    if pr in priority_fills:
        ws.cell(row=r_idx, column=6).fill = priority_fills[pr]
        ws.cell(row=r_idx, column=6).font = Font(bold=True)

ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

ws2 = wb.create_sheet("Summary")
counts = {}
for r in rows:
    counts[r[3]] = counts.get(r[3], 0) + 1
total = len(rows)

ws2.append(["PMC Managers — Bug Tracker"])
ws2["A1"].font = Font(bold=True, size=14, color="0B1E3F")
ws2.append(["Generated", "12 Oct 2026"])
ws2.append([])
ws2.append(["Status", "Count", "% of total"])
for s in ["FIXED", "RE-VERIFY", "NEW", "CLARIFY"]:
    n = counts.get(s, 0)
    ws2.append([s, n, f"{(n*100/total):.0f}%"])
ws2.append(["TOTAL", total, "100%"])

ws2.append([])
ws2.append(["Releases referenced"])
for v, note in [
    ("v52bt", "Admin sidebar · EMD filters/Pay · DocuSign resend 410 · Edit-signers CSS"),
    ("v52bu", "Vendor Signatures sync · EMD receipt PDF · Vendor sidebar links"),
    ("v52bv", "Services back button · Service quotes KPI · PmcMobileNav auth-redirect"),
    ("v52bw", "DocuSign vendor sync (both gates) · Resend v2 · Escrow CSS · BOQ view/contract · Tender search promoted"),
    ("v52bx", "Session cross-contamination · Reverse auction vendor visibility · Corrigenda testids"),
    ("v52by", "Reverse Auction create/start · BOQ Excel+PDF export · Corrigenda withdraw refresh"),
    ("v52bz", "Rubric persistence · Scoring=0 auto-COI · Package redirect · Withdraw Dialog"),
    ("v52ca", "Corrigenda second-search feedback + withdraw regression"),
    ("v52cb", "Registrations card layout · Admin back button · Evaluation tender picker"),
    ("v52cc", "Tender Builder: fresh dates + validation · docs relabel · Draft→Notice bridge"),
]:
    ws2.append([v, note])

for col_idx, w in enumerate([14, 55], start=1):
    ws2.column_dimensions[get_column_letter(col_idx)].width = w
ws2.column_dimensions["C"].width = 12

for row in ws2.iter_rows(min_row=4, max_row=9):
    for cell in row:
        cell.border = border
for col in ("A4", "B4", "C4"):
    ws2[col].fill = header_fill; ws2[col].font = header_font

out = "/app/frontend/public/downloads/PMC_Bug_Tracker_R6.xlsx"
wb.save(out)
print("WROTE", out)
