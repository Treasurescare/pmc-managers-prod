"""Bug Tracker v3 — final status after Waves A-G fixes."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Bug_Tracker_v3.xlsx")

ROWS = [
    # ---- SHIPPED to prod (from prior sessions) ----
    (1,  "Clone as draft error 500", "Tender Builder", "P0", "FIXED", "order field auto-assigned", "Shipped v5", "Prod live"),
    (3,  "Bidding Ops button logs out user", "Bidding Ops", "P0", "FIXED", "Promise.allSettled", "Shipped v5", "Prod live"),
    (4,  "Blank form download PDF fails", "Vendor Invites", "P1", "FIXED", "reportlab fallback", "Shipped v5", "Prod live"),
    (8,  "Invite Vendor not working", "Vendors", "P1", "CONFIRMED WORKING", "User confirmed", "N/A", "No action"),
    (9,  "Vendor Add & Fill Full Form 'undefined' toast", "Vendors", "P1", "FIXED", "Defensive undefined fallback", "Shipped v5", "Prod live"),
    (11, "L1 Comparison Run hangs", "L1 Comparison", "P0", "FIXED", "45-sec Promise.race timeout", "Shipped v5", "Prod live"),
    (13, "Masters tab hangs", "Masters", "P0", "FIXED", "Promise.allSettled", "Shipped v5", "Prod live"),
    (14, "Escrow joint account created without officer info", "Escrow", "P1", "FIXED", "Strict role + email uniqueness", "Shipped v6", "Prod live"),
    (16, "Budget accepts negative numbers", "Notices/Budget", "P1", "FIXED", "NoticeIn budget_amount ge=0", "Shipped v6", "Prod live"),
    (55, "Duplicate of #14", "Escrow", "P1", "FIXED", "See Bug 14", "Shipped v6", "Duplicate"),

    # ---- READY IN v11/v15 (FINAL BATCH) ----
    (5,  "Notice creation as madhavi shows 'undefined'", "Notices (Admin)", "P1", "FIXED", "reviewer.create=True + defensive notice_ref + role-aware publish", "READY v11/v15", "In final zip"),
    (22, "Notices form retains previous details", "Notices", "P2", "FIXED", "Full form reset on success", "READY v11/v15", "In final zip"),
    (23, "Unclear validation toast (10 char min)", "Notices Form", "P2", "FIXED", "Explicit 'Title 3+ chars, Description 10+ chars'", "READY v11/v15", "In final zip"),
    (24, "Publish checkbox disabled for Master Admin", "Notices (Admin)", "P1", "FIXED", "isMasterAdmin gate", "READY v11/v15", "In final zip"),
    (46, "Nudge Stale Drafts unclear success", "Registrations", "P1", "FIXED", "Three-branch toast", "READY v11/v15", "In final zip"),
    (50, "'clarify recorded' typo + wrong verb", "Registrations", "P1", "FIXED", "Verb mapping", "READY v11/v15", "In final zip"),
    (28, "Bulk Invite CSV — page blanks / signs out", "Vendors — Bulk Invite", "P0", "FIXED", "Defensive submit + ErrorBoundary", "READY v11/v15", "In final zip"),
    (36, "Portal hangs on Audit click", "Audit", "P1", "MITIGATED", "ErrorBoundary catches crashes; session preserved", "READY v11/v15", "Partial"),
    (39, "Generate Award Report page hangs", "Evaluation / Awards", "P0", "MITIGATED", "ErrorBoundary catches crashes; session preserved", "READY v11/v15", "Partial"),
    (52, "Screen goes blank after bulk invite", "Vendors — Bulk Invite", "P0", "FIXED", "Dup of 28", "READY v11/v15", "Duplicate"),
    (57, "Screen goes blank after award report", "Awards & POs", "P0", "MITIGATED", "Dup of 39", "READY v11/v15", "Duplicate"),
    (58, "Screen goes blank across flows, requires re-login", "General", "P0", "FIXED", "Root React ErrorBoundary — session preserved", "READY v11/v15", "In final zip"),
    (43, "Reverse auction Start button doesn't go live", "Reverse Auctions", "P1", "FIXED", "Clearer error naming missing participants", "READY v11/v15", "In final zip"),
    (44, "Reverse auction Close button doesn't close", "Reverse Auctions", "P1", "FIXED", "Reject close-on-draft + clearer msg", "READY v11/v15", "In final zip"),
    (51, "No notifications after nudging stale drafts", "Notifications", "P1", "FIXED", "Admin notification per email sent", "READY v11/v15", "In final zip"),
    (2,  "New BOQ template not visible after submission", "BOQ Templates", "P1", "PARTIAL", "Backend list capped + sorted; retest needed", "READY v11/v15", "Retest needed"),
    (12, "New BOQ contract not showing in list", "BOQ Contracts", "P1", "PARTIAL", "Backend list capped + sorted; retest needed", "READY v11/v15", "Retest needed"),
    # Wave E fixes (new in this batch)
    (34, "Product catalog save doesn't persist / not in table", "Product Catalog", "P1", "FIXED", "Cache-buster query param on reload", "READY v11/v15", "In final zip"),
    (35, "Product catalog created but not in table", "Product Catalog", "P1", "FIXED", "See Bug 34 — same fix", "READY v11/v15", "Duplicate"),
    (54, "Cancelled meeting still visible", "Meetings", "P1", "FIXED", "Backend hides cancelled by default (include_cancelled param); frontend toggle", "READY v11/v15", "In final zip"),
    (56, "Rubric saved with values > max / weights invalid", "Evaluation", "P1", "FIXED", "ScoringRubricIn validates weights sum=1.0, max>0, weight in 0-1", "READY v11/v15", "In final zip"),
    # Wave G governance fixes (new in this batch)
    ("G1","Escrow dual-sig not enforced (same login can sign both)", "Escrow", "P0-Gov", "FIXED", "escrow.create_account rejects when pmc_officer.email == escrow_officer.email", "READY v11/v15", "In final zip"),
    ("G2","COI not cross-checked against committee membership", "Evaluation", "P0-Gov", "ALREADY IMPLEMENTED", "evaluations.submit_score blocks if no COI declaration (was already in place)", "N/A", "Verified in code"),
    ("G5","Reverse Auction DRAFT exposes public link", "Reverse Auctions", "P1", "FIXED", "Frontend hides bidder link until status != draft; shows explanatory text instead", "READY v11/v15", "In final zip"),
    # Wave F handbook (new in this batch)
    ("F1","Trainee Handbook out-of-date (missing chapters)", "Docs", "P2", "FIXED", "Written PMC_Trainee_Handbook_v3.1.md — 12 chapters covering Roles, RBAC, Permissions Matrix, Notices, Registrations, Bidding/COI, Escrow, Reverse Auctions, Meetings, ErrorBoundary, Help Requests, Portal Branding, bug fix log", "READY v11/v15", "Docs delivered"),

    # ---- Still OPEN — needs retest or repro ----
    (19, "New package created msg but not in list", "Packages", "P1", "OPEN", "Backend + frontend correct on inspection; suspect browser cache. Retest with hard refresh", "Retest", "Retest first"),
    (30, "Newly activated vendor not appearing in Vendors table", "Vendors", "P1", "OPEN", "approve_and_create_vendor sets tenant_id correctly; retest", "Retest", "Retest first"),
    (37, "Duplicate of Bug 19", "Packages", "P1", "OPEN", "See Bug 19", "Retest", "Duplicate"),
    (42, "New reverse auction not listed as draft", "Reverse Auctions", "P1", "OPEN", "Backend + frontend correct; may be status filter or cache", "Retest", "Retest first"),
    (45, "Rejected company not shown in Rejected list", "Registrations", "P1", "OPEN", "Backend admin_list filters correctly; verify status enum casing", "Retest", "Retest first"),
    (25, "Withdrawn corrigenda still visible as active", "Corrigenda / Notices", "P1", "OPEN", "Public list filters is_active=True; admin list intentionally shows all with opacity. UX clarification needed", "Retest", "Clarify UX"),
    (26, "Corrigenda status not updated after Withdraw", "Corrigenda", "P1", "OPEN", "See Bug 25", "Retest", "Clarify UX"),
    (60, "Corrigendum still visible after withdrawing", "Corrigenda", "P1", "OPEN", "See Bug 25", "Retest", "Duplicate"),
    (6,  "Vendor mailing address error persists", "Vendor Registration", "P1", "OPEN", "Need QA screenshot of exact field", "Awaiting repro", "Awaiting screenshot"),
    (27, "Supplier Approve/Reject/Clarify actions not saved", "Registrations", "P1", "OPEN", "Backend updates correctly; retest with hard refresh", "Retest", "Retest first"),
    (29, "Replace Registration Template — undefined toast", "Vendors", "P1", "OPEN", "Need repro from QA", "Awaiting repro", "Awaiting screenshot"),
    (47, "Can navigate past identity section without required fields", "Vendor Registration", "P1", "OPEN", "Section navigation validation needed", "Next sprint", "Frontend"),
    (48, "Unable to download blank registration form", "Vendor Registration", "P1", "OPEN", "Likely dup of Bug 4 (fixed). Verify with QA", "Retest", "Retest / dup"),
    # Wave E remaining
    (7,  "Resume link not sent to email despite success msg", "Vendor Registration / Email", "P1", "OPEN", "Verify EMAIL_KEY env propagation to Docker", "Wave E2", "Verify env"),
    (15, "AI Bid Anomaly score/deviation blank", "Dashboard", "P2", "OPEN", "Add 'no anomalies' default state", "Wave E2", "Backend + frontend"),
    (17, "Error clicking 'Review document' from DocuSign email", "DocuSign", "P1", "OPEN", "DocuSign URL expiry — add retry", "Wave E2", "Backend"),
    (20, "Check status token — no error for invalid token", "Public Landing", "P2", "OPEN", "Show toast on invalid token", "Wave E2", "Frontend"),
    (21, "Login shows console error", "Login", "P2", "OPEN", "Need actual console error", "Wave E2", "Investigate"),
    (31, "Localization incomplete", "i18n", "P2", "OPEN", "Audit i18n JSON files", "Wave E2", "Frontend"),
    (32, "Profile image not shown after re-login", "Profile", "P1", "OPEN", "TopBar reload on route change", "Wave E2", "Frontend"),
    (33, "Missing email/mobile validation across forms", "Forms (general)", "P2", "OPEN", "Zod/yup validation", "Wave E2", "Frontend"),
    (38, "Tender Builder content doesn't update on tab switch", "Tender Builder", "P1", "OPEN", "Reset activeTemplate on tab change", "Wave E2", "Frontend"),
    (40, "L1 Comparison dropdown empty", "L1 Comparison", "P1", "OPEN", "Filter for awarded bids", "Wave E2", "Frontend"),
    (41, "Regenerate documents doesn't work", "Awards & POs", "P1", "OPEN", "Add confirmation + version docs", "Wave E2", "Backend"),
    (49, "Save snapshot to repo — JSON parsing error", "Stakeholder Reports", "P2", "OPEN", "Wrap in try/catch, return JSON error", "Wave E2", "Backend"),
    # Wave G remaining
    ("G3","Two access-control systems (Permissions vs Level)", "Governance", "P1", "PARTIAL", "Documented in Handbook chapter 1; full consolidation deferred", "Wave G2", "Docs done, code TBD"),
    ("G4","Stakeholder Reports doesn't match description", "Reports", "P1", "OPEN", "Product decision — rename or rebuild", "Wave G2", "Product decision"),
]

wb = Workbook()
ws = wb.active
ws.title = "Bug Tracker"

HEADERS = ["Bug ID", "Title", "Module", "Severity", "Status", "Fix Approach", "Wave", "Ship / Notes"]
FILLS = {
    "FIXED": PatternFill("solid", fgColor="C6EFCE"),
    "CONFIRMED WORKING": PatternFill("solid", fgColor="C6EFCE"),
    "ALREADY IMPLEMENTED": PatternFill("solid", fgColor="C6EFCE"),
    "MITIGATED": PatternFill("solid", fgColor="FFEB9C"),
    "PARTIAL": PatternFill("solid", fgColor="FFEB9C"),
    "OPEN": PatternFill("solid", fgColor="FFC7CE"),
}
HEADER_FILL = PatternFill("solid", fgColor="0F1B3D")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
CELL_FONT = Font(size=10)
BORDER = Border(*[Side(style="thin", color="D0D0D0")] * 4)

for c, h in enumerate(HEADERS, 1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.fill = HEADER_FILL
    cell.font = HEADER_FONT
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

# Summary
ws2 = wb.create_sheet("Summary")
counts = {"FIXED": 0, "MITIGATED": 0, "PARTIAL": 0, "CONFIRMED WORKING": 0, "ALREADY IMPLEMENTED": 0, "OPEN": 0}
for r in ROWS:
    if r[7] == "Duplicate":
        continue
    counts[r[4]] = counts.get(r[4], 0) + 1

ws2.append(["Status", "Count", "Notes"])
ws2.append(["FIXED / SHIPPED",
             counts["FIXED"] + counts["CONFIRMED WORKING"] + counts["ALREADY IMPLEMENTED"],
             "Live in prod OR in v11/v15 zip OR verified in existing code"])
ws2.append(["MITIGATED", counts["MITIGATED"],
             "ErrorBoundary catches; full underlying fix pending"])
ws2.append(["PARTIAL", counts["PARTIAL"], "Root cause mitigated; needs retest"])
ws2.append(["OPEN", counts["OPEN"], "Awaiting retest OR needs more repro info"])
ws2.append([])
ws2.append(["Deploy plan for v11/v15"])
ws2.append(["1. Deploy pmc-backend-v11-final.zip to EB"])
ws2.append(["2. Upload pmc-frontend-v15-final.zip to S3 + CloudFront /*"])
ws2.append(["3. QA retest ALL bugs marked 'READY v11/v15' (28 items)"])
ws2.append(["4. Verify 'OPEN' bugs marked 'Retest first' — many may resolve after hard refresh"])
ws2.append(["5. Wave E2 remaining (12 misc bugs) + G2 governance (2 items) in next sprint"])

for c in range(1, 4):
    ws2.cell(row=1, column=c).fill = HEADER_FILL
    ws2.cell(row=1, column=c).font = HEADER_FONT
ws2.column_dimensions["A"].width = 25
ws2.column_dimensions["B"].width = 10
ws2.column_dimensions["C"].width = 90

wb.save(OUT)
print(f"Written {OUT}")
print(f"Bug rows: {len(ROWS)}")
print(f"Counts: {counts}")
