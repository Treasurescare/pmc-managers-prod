"""PMC Bug Tracker v17 — consolidated NOT-FIXED list (from user's sheet, 02 Oct 2026).
Two sheets: (1) Not Fixed — Triage, (2) Regression & Release Log."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/app/frontend/public/downloads/PMC_Bug_Tracker_v17_NotFixed_20261002.xlsx"

GREEN = "0F3B2E"
DARK = "0B1A14"
BRASS = "B08E4A"
CREAM = "F6F0DC"
RED = "C0392B"
AMBER = "B7791F"
GREY = "6B7280"
BLUE = "2B6CB0"
GREEN_OK = "1E7B4D"

thin = Side(style="thin", color="D8D2C4")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

ROWS = [
    # sl, module, bug, priority, team_status, retest_date, team_remarks, triage, agent_status, batch
    (5, "Notices", "Creating a new notice from admin login - not working.", "High", "Not Fixed", "01-10-2026",
     "Retested successfully. New notice was created and appeared in the notices list with a DRAFT badge. Round 5",
     "Remark says retest PASSED — verify on current build; likely already resolved.", "Verify", "D"),
    (6, "Vendors", "Mailing Address is added. Still receiving the error message while registering the vendor.", "High", "Not Fixed", "28-09-2026",
     "Retested with Mailing Address filled. No Mailing Address error appeared, but vendor activation did not complete and no success message was displayed.",
     "Vendor activation completes without success toast; check VendorsPanel activate API call + response handling.", "Open", "B"),
    (7, "Vendor Signin", "Resume link not sent to mail id provided although message on portal says sent the secure link to mail id.", "Medium", "Not Fixed", "01-10-2026",
     "Retested successfully. Resume registration email was received, and the link opened the saved registration form with previously entered data. Round 5",
     "Remark says retest PASSED — verify; possibly affected by today's email pipeline fix (suppression/DNS).", "Verify", "E"),
    (8, "Vendors", "Invite vendor not working.", "", "Not Fixed", "28-09-2026",
     "Clicking Send Invitation produces no response and the vendor invitation is not sent.",
     "Frontend click handler / vendor_invites API; check console + network.", "Open", "B"),
    (9, "Vendors", "Vendor creation from \"Vendor Fill form\" not working.", "", "Not Fixed", "28-09-2026",
     "Vendor creation from the Vendor Fill Form does not complete; clicking Create & Activate Vendor does not create/activate the vendor.",
     "Vendor fill-form submit path; validation or API failure swallowed.", "Open", "B"),
    (13, "Escrow & EMD", "ESCROW option — clicking new joint account without filling any details gets it created.", "", "Not Fixed", "28-09-2026",
     "Create Joint Account button is not responding, so the original issue of creating a joint account with blank details could not be verified.",
     "Two issues: (a) button dead, (b) missing mandatory-field validation.", "Open", "D"),
    (27, "Vendors", "After adding a new vendor and activating it from the Activation tab, the newly created vendor not appearing in the Vendors table.", "", "Not Fixed", "01-10-2026",
     "After approving/activating the newly created vendor, it appeared in the Vendors table.",
     "Remark indicates resolved after activation — verify list refresh behaviour.", "Verify", "B"),
    (37, "L1 Comparison", "In \"L1 Comparison\" tab the drop down does not show all the notices.", "", "Not Fixed", "30-09-2026",
     "",
     "Dropdown source likely filtered to published/limited notices; align with /notices/admin/all.", "Open", "D"),
    (39, "Reverse Auctions", "On click of \"New Reverse Auction\" in the Reverse Auction tab, newly created auction is not listed as draft.", "Medium", "Not Fixed", "30-09-2026",
     "Cannot find the tab for Reverse Auctions",
     "Reverse Auctions tab missing from admin nav (E-console redirect map); then list-after-create refresh.", "Open", "D"),
    (40, "Reverse Auctions", "On clicking the \"Start\" button it does not make the notice go live.", "Low", "Not Fixed", "30-09-2026",
     "Cannot find the tab for Reverse Auctions",
     "Same root: tab missing; then Start action wiring.", "Open", "D"),
    (41, "Reverse Auctions", "On clicking the \"Close\" button auction is not getting closed.", "", "Not Fixed", "30-09-2026",
     "Cannot find the tab for Reverse Auctions",
     "Same root: tab missing; then Close action wiring.", "Open", "D"),
    (42, "Registrations", "Registrations Tab - Rejected has a company. But it is not listed under Rejected list.", "Medium", "Not Fixed", "01-10-2026",
     "Round 5",
     "Rejected tab filter vs backend status value mismatch.", "Open", "C"),
    (44, "Registrations", "Can go to \"contact and signatory\" and further steps without even fully entering the necessary information in \"identity and basic information\".", "High", "Not Fixed", "01-10-2026",
     "Round 5",
     "Registration wizard step gating — block Next until required fields valid.", "Open", "C"),
    (45, "Stakeholder Reports", "Save snapshot button fails with JSON parsing error in the Stakeholder Reports.", "High", "Not Fixed", "28-09-2026",
     "Cannot find the tab for Stakeholder reports",
     "Tab missing + backend snapshot endpoint returning non-JSON (HTML error page).", "Open", "D"),
    (46, "Registrations", "When requested clarification, the submitted draft is not shown in needs_clarification tab. It should read \"clarification recorded\" instead of \"clarify recorded\".", "Cosmetic", "Not Fixed", "01-10-2026",
     "Round 5",
     "(a) status not moving to needs_clarification tab; (b) toast typo fix.", "Open", "C"),
    (59, "Vendors", "Click the \"Invite Vendor\" button gives the success message \"Invite Undefined\". No email is received.", "", "Not Fixed", "01-10-2026",
     "Sept 8, Fixed only with Super Admin Round 5",
     "Success toast uses undefined name var; email send — retest after today's email fix.", "Open", "B"),
    (60, "Public", "Public Portal - Register as Supplier → Download Blank Registration Form: file is downloaded, but not opening.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "Template file corrupt/wrong content-type; check test-registration-template.pdf serving.", "Open", "E"),
    (61, "Registrations", "Status not changing from \"Submitted\" to \"Approved\" on click of APPROVE. Success message shows but no update visible in portal.", "", "Not Fixed", "01-10-2026",
     "Sept 8, Fixed only with Super Admin Round 5",
     "Approve updates DB but list not refreshing / role-gated path.", "Open", "C"),
    (62, "Vendors", "Vendors - Bulk invite CSV gives an error message.", "", "Not Fixed", "01-10-2026",
     "Sept 10, Fixed only with Super Admin Round 5",
     "Bulk invite CSV parse/validation error — need exact message; test with sample CSV.", "Open", "B"),
    (63, "Vendors", "Add & Fill Full Form - Active Immediately gives success message. But the user id is not listed in the Vendors list.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "Vendor created but list query excludes it (status/tenant filter) or list not refreshed.", "Open", "B"),
    (64, "Registrations", "Click on \"Reject\" gives success message \"Reject Recorded\". Still showing as submitted.", "", "Not Fixed", "01-10-2026",
     "Sept 8, Fixed only with Super Admin Round 5",
     "Same family as #61 — status write vs UI refresh.", "Open", "C"),
    (65, "Registrations", "Click on \"Request Clarification\" gives success message \"Clarification Recorded\". Still showing as submitted.", "", "Not Fixed", "01-10-2026",
     "Sept 8, Fixed only with Super Admin Round 5",
     "Same family as #61/#64.", "Open", "C"),
    (66, "Notices", "New Notice created successfully with Notice ID; dashboard Notices counter +1, but the notice is not listed under Notices tab as draft. (Publish Immediately checkbox not enabled — Master Admin only.)", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "Notices list filter hides drafts for non-master roles; check status filter + permissions.", "Open", "D"),
    (99, "Tender Builder", "Country filter does not filter Master Library templates. Same 3 master templates displayed for India/KZ/TR.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "CONFLICT: v50e intentionally shows ALL masters grouped by country per your request. Confirm with team which behaviour is correct.", "Needs Decision", "F"),
    (118, "Dashboard", "AI Bid Anomaly — Bid dropdown options not clearly visible; bid names/text appear extremely faint, difficult to read/select.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "CSS contrast on select/dropdown options in AI compare panel.", "Open", "D"),
    (119, "Vendors – Add & Fill Full Form", "Document card buttons/icons overlap in Vendor Fill Form, particularly around Address Proof and View/Download/Delete actions.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "CSS overlap on document card action row.", "Open", "B"),
    (120, "Vendors – Add & Fill Full Form", "Section K can be saved without selecting any of the six mandatory declarations.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "Add client+server validation for 6 mandatory declarations.", "Open", "B"),
    (121, "Logging in", "Forgot password says email sent but no mail comes to inbox to reset password.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "FIXED TODAY 02-10-2026: Resend suppression list + Route 53 DKIM/SPF + new API key + sender domain. Verified delivered live.", "Fixed — retest after v50f deploy", "A"),
    (122, "Vendor Registration", "Accepts even 9-digit numbers and proceeds for registration; should stop with a pop-up to enter valid mobile number.", "High", "Not Fixed", "01-10-2026",
     "Round 5",
     "Phone validation (min length + country format) on registration step 1.", "Open", "C"),
    (123, "Logging in", "When we click on the translation button, it doesn't show any option.", "", "Not Fixed", "01-10-2026",
     "Round 5",
     "Language/translation dropdown unpopulated on login page.", "Open", "A"),
    (124, "Home Page → sign in", "Wrong username and password does not give error message on screen when wrong role is selected.", "Medium", "Not Fixed", "NA",
     "",
     "Sign-in error toast suppressed on role mismatch path.", "Open", "A"),
]

wb = openpyxl.Workbook()

# ── Sheet 1: Not Fixed — Triage ──────────────────────────────────────────
ws = wb.active
ws.title = "Not Fixed — Triage"
headers = ["Sl No", "Tab/Module", "Bug / Observation", "Priority", "Status (Team)",
           "Retested Date", "Team Remarks (Round 5)", "Agent Triage / Suspected Root Cause",
           "Agent Status", "Fix Batch", "Fix Version", "Verified Date", "Regression Notes"]
ws.append(headers)
for r in ROWS:
    ws.append([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], "", "", ""])

widths = [7, 22, 55, 10, 14, 13, 45, 55, 22, 10, 12, 13, 25]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill("solid", fgColor=GREEN)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER
ws.row_dimensions[1].height = 30
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:M{ws.max_row}"

pri_fill = {"High": RED, "Medium": AMBER, "Low": GREY, "Cosmetic": BLUE}
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
        cell.border = BORDER
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.font = Font(size=10)
    p = row[3].value
    if p in pri_fill:
        row[3].font = Font(size=10, bold=True, color="FFFFFF")
        row[3].fill = PatternFill("solid", fgColor=pri_fill[p])
        row[3].alignment = Alignment(horizontal="center", vertical="center")
    st = str(row[8].value or "")
    if st.startswith("Fixed"):
        row[8].font = Font(size=10, bold=True, color="FFFFFF")
        row[8].fill = PatternFill("solid", fgColor=GREEN_OK)
    elif st == "Verify":
        row[8].font = Font(size=10, bold=True, color="FFFFFF")
        row[8].fill = PatternFill("solid", fgColor=BLUE)
    elif st == "Needs Decision":
        row[8].font = Font(size=10, bold=True, color="FFFFFF")
        row[8].fill = PatternFill("solid", fgColor=AMBER)
    if row[0].row % 2 == 0:
        for cell in row:
            if cell.fill.fgColor.rgb in ("00000000", None):
                cell.fill = PatternFill("solid", fgColor=CREAM)

# ── Sheet 2: Regression & Release Log ────────────────────────────────────
ws2 = wb.create_sheet("Regression & Release Log")
ws2.append(["PMC Bug Tracker v17 — process to stop regressions", "", "", ""])
ws2["A1"].font = Font(bold=True, size=14, color=GREEN)
ws2.merge_cells("A1:D1")
ws2.append([])
notes = [
    ("WHY REGRESSIONS KEEP HAPPENING", ""),
    ("1.", "Fixes were applied to single pages while shared components (PmcLinkPatcher, pmcELiveData, CSS layers) affect many pages — one change can shift behaviour elsewhere."),
    ("2.", "No automated regression suite was run after each fix; verification was per-bug only."),
    ("3.", "Frontend and backend were sometimes deployed at different versions."),
    ("", ""),
    ("NEW PROCESS (from v17 onwards)", ""),
    ("1.", "Bugs fixed in BATCHES by module (Batch A–F below), never one-at-a-time deploys."),
    ("2.", "After EVERY batch: automated regression sweep of all 28 core routes (desktop 1440 + mobile 390) before handoff."),
    ("3.", "Frontend + backend always released together in one numbered version with release notes."),
    ("4.", "This tracker is the single source of truth — Fix Version + Verified Date filled per row."),
    ("", ""),
    ("FIX BATCHES", ""),
    ("Batch A", "Login / Auth: #121 (done — retest), #123, #124"),
    ("Batch B", "Vendors: #6, #8, #9, #27, #59, #62, #63, #119, #120"),
    ("Batch C", "Registrations: #42, #44, #46, #61, #64, #65, #122"),
    ("Batch D", "Notices / Escrow / Auctions / L1 / Reports / Dashboard: #5, #13, #37, #39, #40, #41, #45, #66, #118"),
    ("Batch E", "Public portal & vendor sign-in: #7, #60"),
    ("Batch F", "Tender Builder: #99 (needs your decision — see triage note)"),
    ("", ""),
    ("AFTER ALL BATCHES", "Full E2E procurement regression: DPR upload → AI tender → edit → publish → vendor bid → EMD payment → award → DocuSign."),
]
for label, text in notes:
    ws2.append([label, text, "", ""])
    if label and not text:
        ws2.cell(row=ws2.max_row, column=1).font = Font(bold=True, size=12, color=BRASS)
    elif label in ("Batch A", "Batch B", "Batch C", "Batch D", "Batch E", "Batch F", "AFTER ALL BATCHES"):
        ws2.cell(row=ws2.max_row, column=1).font = Font(bold=True, size=10, color=GREEN)
ws2.column_dimensions["A"].width = 22
ws2.column_dimensions["B"].width = 140

wb.save(OUT)
print("Saved:", OUT)
print("Rows:", len(ROWS))
