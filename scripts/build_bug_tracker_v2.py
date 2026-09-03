"""Rebuild the Bug Tracker Excel with Waves A-D deployment statuses."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Bug_Tracker_v2.xlsx")
OUT.parent.mkdir(exist_ok=True)

# Bug rows — updated statuses after Waves A/B/C/D fixes
ROWS = [
    # ---- SHIPPED to prod ----
    (1,  "Clone as draft error 500", "Tender Builder", "P0", "FIXED", "order field auto-assigned", "Shipped v5", "Prod live"),
    (3,  "Bidding Ops button logs out user", "Bidding Ops", "P0", "FIXED", "Promise.allSettled", "Shipped v5", "Prod live"),
    (4,  "Blank form download PDF fails", "Vendor Invites", "P1", "FIXED", "reportlab fallback", "Shipped v5", "Prod live"),
    (8,  "Invite Vendor not working", "Vendors", "P1", "CONFIRMED WORKING", "User confirmed 26-Aug", "N/A", "No action"),
    (9,  "Vendor Add & Fill Full Form 'undefined' toast", "Vendors", "P1", "FIXED", "Defensive undefined fallback", "Shipped v5", "Prod live"),
    (11, "L1 Comparison Run hangs", "L1 Comparison", "P0", "FIXED", "45-sec Promise.race timeout", "Shipped v5", "Prod live"),
    (13, "Masters tab hangs", "Masters", "P0", "FIXED", "Promise.allSettled", "Shipped v5", "Prod live"),
    (14, "Escrow joint account created without officer info", "Escrow", "P1", "FIXED", "Strict role + email uniqueness", "Shipped v6", "Prod live"),
    (16, "Budget accepts negative numbers", "Notices/Budget", "P1", "FIXED", "NoticeIn budget_amount ge=0", "Shipped v6", "Prod live"),
    (55, "Duplicate of #14", "Escrow", "P1", "FIXED", "See Bug 14", "Shipped v6", "Duplicate"),

    # ---- READY IN v10/v14 (this batch) ----
    (5,  "Notice creation as madhavi shows 'undefined'", "Notices (Admin)", "P1", "FIXED", "reviewer.create=True + defensive notice_ref + role-aware publish", "READY v10/v14", "In this zip"),
    (22, "Notices form retains previous details", "Notices", "P2", "FIXED", "Full form reset on success", "READY v10/v14", "In this zip"),
    (23, "Unclear validation toast (10 char min)", "Notices Form", "P2", "FIXED", "Explicit 'Title 3+ chars, Description 10+ chars'", "READY v10/v14", "In this zip"),
    (24, "Publish checkbox disabled for Master Admin", "Notices (Admin)", "P1", "FIXED", "isMasterAdmin gate", "READY v10/v14", "In this zip"),
    (46, "Nudge Stale Drafts unclear success", "Registrations", "P1", "FIXED", "Three-branch toast (no drafts / none stale / count)", "READY v10/v14", "In this zip"),
    (50, "'clarify recorded' typo + wrong verb", "Registrations", "P1", "FIXED", "Verb mapping", "READY v10/v14", "In this zip"),
    (28, "Bulk Invite CSV — page blanks / signs out", "Vendors — Bulk Invite", "P0", "FIXED", "Defensive try/catch in submit + ErrorBoundary at root", "READY v10/v14", "In this zip"),
    (36, "Portal hangs on Audit click", "Audit", "P1", "PARTIAL", "Root ErrorBoundary catches crashes; pagination still needed for full fix", "READY v10/v14", "Partial in zip"),
    (39, "Generate Award Report page hangs", "Evaluation / Awards", "P0", "PARTIAL", "Root ErrorBoundary catches crashes; PDF-timeout guard still needed", "READY v10/v14", "Partial in zip"),
    (52, "Screen goes blank after bulk invite (dup of 28)", "Vendors — Bulk Invite", "P0", "FIXED", "See Bug 28", "READY v10/v14", "Duplicate"),
    (57, "Screen goes blank after award report (dup of 39)", "Awards & POs", "P0", "PARTIAL", "See Bug 39", "READY v10/v14", "Duplicate"),
    (58, "Screen goes blank across flows, requires re-login", "General", "P0", "FIXED", "React ErrorBoundary at root — session preserved on crash", "READY v10/v14", "In this zip"),
    (43, "Reverse auction Start button doesn't go live", "Reverse Auctions", "P1", "FIXED", "Clearer error msg naming the specific gate (needs 2+ participants)", "READY v10/v14", "In this zip"),
    (44, "Reverse auction Close button doesn't close", "Reverse Auctions", "P1", "FIXED", "Clearer error msg + reject close-on-draft", "READY v10/v14", "In this zip"),
    (51, "No notifications sent after nudging stale drafts", "Notifications", "P1", "FIXED", "send-reminders now inserts admin notification per email sent", "READY v10/v14", "In this zip"),
    (2,  "New BOQ template not visible after submission", "BOQ Templates", "P1", "PARTIAL", "Backend list now limits+sorts; QA to re-verify (may be old browser cache)", "READY v10/v14", "Retest needed"),
    (12, "New BOQ contract not showing in list", "BOQ Contracts", "P1", "PARTIAL", "Backend list capped at 500; retest with hard refresh", "READY v10/v14", "Retest needed"),

    # ---- OPEN - Wave A remaining ----
    (19, "New package shows created msg but not in list", "Packages", "P1", "OPEN", "Backend + frontend look correct on inspection; may be a caching bug. Reproduce with QA", "Wave A2", "Retest first"),
    (30, "Newly activated vendor not appearing in Vendors table", "Vendors", "P1", "OPEN", "approve_and_create_vendor sets tenant_id — should work. Retest with QA", "Wave A2", "Retest first"),
    (35, "Product catalog created but not in table", "Product Catalog", "P1", "OPEN", "reload() runs; suspect browser cache. Add cache-buster query param", "Wave A2", "Frontend"),
    (37, "Duplicate of Bug 19", "Packages", "P1", "OPEN", "See Bug 19", "Wave A2", "Duplicate"),
    (42, "New reverse auction not listed as draft", "Reverse Auctions", "P1", "OPEN", "Backend + frontend look correct; may be status filter or cache. Retest", "Wave A2", "Retest first"),
    (45, "Rejected company not shown in Rejected list", "Registrations", "P1", "OPEN", "Backend admin_list filters correctly. Verify status enum casing", "Wave A2", "Retest first"),
    (25, "Withdrawn corrigenda still visible as active", "Corrigenda / Notices", "P1", "OPEN", "Public list already filters is_active=True; admin list intentionally shows all with opacity. May be a UX confusion — clarify with QA", "Wave C2", "Retest / clarify"),
    (26, "Corrigenda status not updated after Withdraw", "Corrigenda", "P1", "OPEN", "See Bug 25", "Wave C2", "Retest / clarify"),
    (60, "Corrigendum still visible after withdrawing (dup of 25)", "Corrigenda", "P1", "OPEN", "See Bug 25", "Wave C2", "Duplicate"),

    # ---- OPEN - Wave D ----
    (6,  "Vendor mailing address error persists", "Vendor Registration", "P1", "OPEN", "SectionB/C validation; needs QA screenshot of exact field", "Wave D2", "Awaiting repro"),
    (27, "Supplier Approve/Reject/Clarify actions not saved", "Registrations", "P1", "OPEN", "Backend updates correctly; frontend reload should show. Retest", "Wave D2", "Retest first"),
    (29, "Replace Registration Template — undefined toast", "Vendors", "P1", "OPEN", "Backend response missing template_name in some paths; retest", "Wave D2", "Retest first"),
    (47, "Can navigate past identity section without required fields", "Vendor Registration", "P1", "OPEN", "Add section-level validation gate in wizard", "Wave D2", "Frontend"),
    (48, "Unable to download blank registration form", "Vendor Registration", "P1", "OPEN", "Likely dup of Bug 4 (fixed). QA to verify", "Wave D2", "Retest / dup?"),

    # ---- OPEN - Wave E ----
    (7,  "Resume link not sent to email despite success msg", "Vendor Registration / Email", "P1", "OPEN", "Verify EMAIL_KEY env var propagation to Docker", "Wave E", "Backend"),
    (15, "AI Bid Anomaly score/deviation blank", "Dashboard", "P2", "OPEN", "Add default 'no anomalies' state", "Wave E", "Backend + frontend"),
    (17, "Error clicking 'Review document' from DocuSign email", "DocuSign", "P1", "OPEN", "DocuSign URL expiry — add retry", "Wave E", "Backend"),
    (20, "Check status token — no error for invalid token", "Public Landing", "P2", "OPEN", "Show toast on invalid token", "Wave E", "Frontend"),
    (21, "Login shows console error", "Login", "P2", "OPEN", "Need actual console error from QA", "Wave E", "Investigate"),
    (31, "Localization incomplete", "i18n", "P2", "OPEN", "Audit i18n JSON files", "Wave E", "Frontend"),
    (32, "Profile image not shown after re-login", "Profile", "P1", "OPEN", "TopBar reload on route change", "Wave E", "Frontend"),
    (33, "Missing email/mobile validation across forms", "Forms (general)", "P2", "OPEN", "Zod/yup validation", "Wave E", "Frontend"),
    (34, "Product catalog save doesn't persist", "Product Catalog", "P1", "OPEN", "May be dup of Bug 35 caching", "Wave E", "Retest / dup?"),
    (38, "Tender Builder content doesn't update on tab switch", "Tender Builder", "P1", "OPEN", "Reset activeTemplate on tab change", "Wave E", "Frontend"),
    (40, "L1 Comparison dropdown empty", "L1 Comparison", "P1", "OPEN", "Filter for awarded bids", "Wave E", "Frontend"),
    (41, "Regenerate documents doesn't work", "Awards & POs", "P1", "OPEN", "Add confirmation + version docs", "Wave E", "Backend"),
    (49, "Save snapshot to repo — JSON parsing error", "Stakeholder Reports", "P2", "OPEN", "Wrap in try/catch, return JSON error", "Wave E", "Backend"),
    (54, "Cancelled meeting still visible", "Meetings", "P1", "OPEN", "Add filter to hide cancelled by default", "Wave E", "Backend + frontend"),
    (56, "Rubric saved with values > max", "Evaluation", "P1", "OPEN", "Server-side + client-side range check", "Wave E", "Backend + frontend"),

    # ---- Wave F handbook + Wave G governance ----
    ("F1","Trainee Handbook out-of-date", "Docs", "P2", "OPEN", "Rewrite missing chapters", "Wave F", "Docs"),
    ("G1","Escrow dual-signature not enforced — same login can sign both", "Escrow", "P0-Gov", "OPEN", "Enforce email + user_id != between signers", "Wave G", "Backend"),
    ("G2","COI not cross-checked against committee membership", "Evaluation / Committee", "P0-Gov", "OPEN", "Block score submission if COI declaration missing", "Wave G", "Backend"),
    ("G3","Two access-control systems (Permissions vs Level)", "Governance", "P1", "OPEN", "Consolidate or clarify in handbook", "Wave G", "Docs + Backend"),
    ("G4","Stakeholder Reports doesn't match description", "Reports", "P1", "OPEN", "Rename module or build described reports", "Wave G", "Product decision"),
    ("G5","Reverse Auction DRAFT exposes public link", "Reverse Auctions", "P1", "OPEN", "Hide bidder-URL until status=live", "Wave G", "Frontend + backend"),
]

wb = Workbook()
ws = wb.active
ws.title = "Bug Tracker"

HEADERS = ["Bug ID", "Title", "Module", "Severity", "Status", "Fix Approach", "Wave", "Ship / Notes"]
FILLS = {
    "FIXED": PatternFill("solid", fgColor="C6EFCE"),
    "CONFIRMED WORKING": PatternFill("solid", fgColor="C6EFCE"),
    "PARTIAL": PatternFill("solid", fgColor="FFEB9C"),
    "OPEN": PatternFill("solid", fgColor="FFC7CE"),
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
    if row[7] == "Duplicate":
        for c in range(1, 9):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor="E7E6E6")
    else:
        fill = FILLS.get(row[4])
        if fill:
            for c in range(1, 9):
                ws.cell(row=r, column=c).fill = fill

widths = [10, 55, 24, 14, 22, 70, 16, 26]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 32
ws.freeze_panes = "A2"

# Summary sheet
ws2 = wb.create_sheet("Summary")
counts = {"FIXED": 0, "PARTIAL": 0, "CONFIRMED WORKING": 0, "OPEN": 0}
for r in ROWS:
    if r[7] == "Duplicate":
        continue
    counts[r[4]] = counts.get(r[4], 0) + 1

ws2.append(["Status", "Count", "Notes"])
ws2.append(["FIXED / SHIPPED", counts["FIXED"] + counts["CONFIRMED WORKING"],
            "Live in prod or in this deploy batch"])
ws2.append(["PARTIAL", counts["PARTIAL"],
            "Root cause mitigated (ErrorBoundary etc.), full fix pending retest"])
ws2.append(["OPEN", counts["OPEN"],
            "Awaiting deploy of v10/v14 + QA retest OR needs more repro info"])
ws2.append([])
ws2.append(["Deploy plan"])
ws2.append(["1. Deploy backend-v10-waves-abcd.zip to EB"])
ws2.append(["2. Upload frontend-v14-waves-abcd.zip to S3 + CloudFront /*"])
ws2.append(["3. QA retest bugs marked 'READY v10/v14'"])
ws2.append(["4. Confirm bugs in Wave A2/C2/D2 with QA — many may already be fixed"])
ws2.append(["5. Tackle Wave E (16 remaining) + Wave F/G in next sprint"])

for c in range(1, 4):
    ws2.cell(row=1, column=c).fill = HEADER_FILL
    ws2.cell(row=1, column=c).font = HEADER_FONT
ws2.column_dimensions["A"].width = 25
ws2.column_dimensions["B"].width = 10
ws2.column_dimensions["C"].width = 70

wb.save(OUT)
print(f"Written {OUT}")
print(f"Bug rows: {len(ROWS)}")
print(f"Status counts: {counts}")
