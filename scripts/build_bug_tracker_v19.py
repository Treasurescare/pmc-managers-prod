"""PMC Bug Tracker v19 — close-out through v50l (02 Oct 2026)."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/app/frontend/public/downloads/PMC_Bug_Tracker_v19_v50l_20261002.xlsx"

GREEN="0F3B2E"; BRASS="B08E4A"; CREAM="F6F0DC"
RED="C0392B"; AMBER="B7791F"; GREY="6B7280"; BLUE="2B6CB0"
GREEN_OK="1E7B4D"; PURPLE="6B21A8"
thin = Side(style="thin", color="D8D2C4")
BORDER = Border(left=thin,right=thin,top=thin,bottom=thin)

ROWS = [
    # sl, module, bug, priority, team_status, retest, team_remarks,
    # agent_triage, agent_status, batch, fix_ver, verified
    ("N1","Admin console","Masters tab missing from Option E sidebar.","High","Reported","02-10-2026",
     "User chat 02-10","Legacy /admin?tab=masters only. Added /admin/e/masters route + sidebar entry + redirect.","Fixed","0","v50g","02-10-2026"),
    ("N2","Admin console","Need Category master coming from the backend.","High","Reported","02-10-2026",
     "User chat 02-10","Added full CRUD + 105 seeded categories (87 UNSPSC + 18 KZ legacy). Create Notice now uses dropdown.","Fixed","0","v50g","02-10-2026"),
    ("N3","Admin console","Tooltip buttons white on cream background.","Medium","Reported","02-10-2026",
     "User chat 02-10","shadcn TooltipContent inline-styled: dark forest-green bg + white text + brass border.","Fixed","0","v50g","02-10-2026"),
    ("N4","Admin console","Masters tab doesn't show first login; appears after tab switches.","Medium","Reported","02-10-2026",
     "User chat 02-10","Root cause: stale service worker. Fixed globally by v50j SW update banner.","Fixed","J","v50j","02-10-2026"),
    ("N5","Create Notice","Delivery country should be a dropdown from a master.","Medium","Reported","02-10-2026",
     "User chat 02-10","Replaced free-text input with 30-country master dropdown.","Fixed","H","v50h","02-10-2026"),
    ("N6","Create Notice","Auto-EMD should also key by category not just country.","Medium","Reported","02-10-2026",
     "User chat 02-10","EmdMasterIn.category field + category filter on /emd-masters + picker passes category.","Fixed","H","v50h","02-10-2026"),
    ("N7","Approval Matrix","Need to pick actual employees/escrow/legal per step.","High","Reported","02-10-2026",
     "User chat 02-10","ApprovalStepIn.assignee_user_id/email/name + MatrixEditor assignee dropdown filtered by role.","Fixed","H","v50h","02-10-2026"),
    ("N8","Notices","Need View & Edit modals + document edit + view uploaded docs.","High","Reported","02-10-2026",
     "User chat 02-10","NoticeViewModal (full read-only + per-doc View/Download/Delete), NoticeEditModal (all fields + append uploads), new row buttons.","Fixed","I","v50i","02-10-2026"),
    ("N9","Notices","No one-click Publish button on draft rows.","High","Reported","02-10-2026",
     "User chat 02-10","Green Publish button on every draft row (Master Admin only). Calls /notices/{ref}/publish.","Fixed","I","v50i","02-10-2026"),
    ("N10","Deploy UX","Users keep seeing stale UI after each deploy.","High","Reported","02-10-2026",
     "User chat 02-10","Service worker no-auto-skip + SwUpdateBanner.jsx (dark banner, bottom-centre). Posts SKIP_WAITING on tap; controllerchange triggers one clean reload. Also runs registration.update() every 30 min.","Fixed","J","v50j","02-10-2026"),
    ("N11","Security","P0 — No one should download notice documents without supplier/vendor login.","High","Reported","02-10-2026",
     "User chat 02-10","/api/v1/uploads/files/{key} requires admin bearer OR vendor cookie. Anonymous = 401. NoticeDetail wraps every file in GatedDownload with 'Sign in to download' CTA.","Fixed","K","v50k","02-10-2026"),
    ("N12","Admin console","Notices list row title collapses one-word-per-line beside long filename link.","Medium","Reported","02-10-2026",
     "User screenshot 02-10","Re-laid-out row as 2-row card: header (ref/type/status/deadline/actions) + body (title + attached file + +N attachments). Filename truncates to 280px.","Fixed","K","v50k","02-10-2026"),
    ("N13","Supplier · Admin","Supplier should add new categories of interest; admin should approve/reject.","High","Reported","02-10-2026",
     "User chat 02-10","New vendor_categories router (5 endpoints). /vendor/categories page with picker + rationale + pending/recent lists. Admin tab Masters > Vendor requests with approve/reject + notes.","Fixed","L","v50l","02-10-2026"),
    # ---------------- Round-5 team-submitted bugs (29) ----------------
    (5,"Notices","Creating a new notice from admin login — not working.","High","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; v50i View/Edit/Publish on top. Re-verify.","Verify","D","",""),
    (6,"Vendors","Mailing Address added but still error while registering vendor.","High","Not Fixed","28-09-2026",
     "Vendor activation did not complete","VendorsPanel activate API response handling. Needs re-test after SW banner clears cache.","Open","B·D","",""),
    (7,"Vendor sign-in","Resume link not sent though UI says sent.","Medium","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; Resend DNS/suppression already fixed 02-10.","Verify","E","v50l",""),
    (8,"Vendors","Invite vendor not working (no response).","Medium","Not Fixed","28-09-2026","",
     "Likely stale cache; retest after SW banner.","Verify","B","v50j",""),
    (9,"Vendors","Vendor creation from 'Vendor Fill form' not working.","Medium","Not Fixed","28-09-2026","",
     "Likely stale cache; retest after SW banner.","Verify","B","v50j",""),
    (13,"Escrow & EMD","Create Joint Account button not responding; also no mandatory validation.","Medium","Not Fixed","28-09-2026","",
     "Needs code fix: button handler + validation. Scheduled Batch D.","Open","D","",""),
    (27,"Vendors","After activating new vendor, not appearing in Vendors table.","Medium","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; verify after SW banner.","Verify","B","v50j",""),
    (37,"L1 Comparison","Drop down does not show all notices.","Medium","Not Fixed","30-09-2026","",
     "Filter mismatch vs /notices/admin/all. Batch D.","Open","D","",""),
    (39,"Reverse Auctions","New auction not listed as draft.","Medium","Not Fixed","30-09-2026",
     "Cannot find tab","Reverse Auctions missing from E sidebar. Batch D.","Open","D","",""),
    (40,"Reverse Auctions","Start button doesn't make auction go live.","Low","Not Fixed","30-09-2026",
     "Cannot find tab","Same root as #39.","Open","D","",""),
    (41,"Reverse Auctions","Close button doesn't close auction.","Low","Not Fixed","30-09-2026",
     "Cannot find tab","Same root as #39.","Open","D","",""),
    (42,"Registrations","Rejected list missing a company.","Medium","Not Fixed","01-10-2026",
     "Round 5","Status filter mismatch. v50k fix shipped; retest.","Verify","C","v50k",""),
    (44,"Registrations","Can advance past Section A without completing identity.","High","Not Fixed","01-10-2026",
     "Round 5","Step gating already in RegistrationResume (missingSectionA + disabled Next). Retest.","Verify","C","v50k",""),
    (45,"Stakeholder Reports","Save snapshot JSON parsing error.","High","Not Fixed","28-09-2026",
     "Cannot find tab","Tab missing + backend returning non-JSON. Batch D.","Open","D","",""),
    (46,"Registrations","needs_clarification tab missing draft; 'clarify recorded' typo.","Cosmetic","Not Fixed","01-10-2026",
     "Round 5","Toast now 'Clarification recorded'. Status-advance switches tab. Retest.","Verify","C","v50k",""),
    (59,"Vendors","Invite Vendor toast reads 'Invite Undefined'. No email received.","High","Not Fixed","01-10-2026",
     "Round 5","Toast is defensive now (uses r.email/r.vendor_ref). Was stale-cache. Email fixed 02-10 (Resend).","Verify","B","v50j",""),
    (60,"Public","Download Blank Registration Form — file downloaded but not opening.","Medium","Not Fixed","01-10-2026",
     "Round 5","Template file corrupt or wrong content-type. Batch E (regen file).","Open","E","",""),
    (61,"Registrations","APPROVE click success toast but status not updating.","High","Not Fixed","01-10-2026",
     "Round 5","decide() auto-switches filter tab to approved. Retest.","Verify","C","v50k",""),
    (62,"Vendors","Bulk invite CSV gives an error message.","Medium","Not Fixed","01-10-2026",
     "Round 5","Client pre-validates every row with row-level reasons. Retest.","Verify","B","v50j",""),
    (63,"Vendors","Add & Fill Full Form — user not in Vendors list after creation.","Medium","Not Fixed","01-10-2026",
     "Round 5","Likely stale cache; retest.","Verify","B","v50j",""),
    (64,"Registrations","Reject click toast success but still submitted.","High","Not Fixed","01-10-2026",
     "Round 5","Same family as #61 fix. Retest.","Verify","C","v50k",""),
    (65,"Registrations","Request Clarification toast success but still submitted.","High","Not Fixed","01-10-2026",
     "Round 5","Same family as #61 fix. Retest.","Verify","C","v50k",""),
    (66,"Notices","New notice created, dashboard +1, but not in Notices tab as draft.","High","Not Fixed","01-10-2026",
     "Round 5","v50k row redesign + v50i View/Edit visibility. Retest.","Verify","D","v50k",""),
    (99,"Tender Builder","Country filter does not filter Master Library templates.","Medium","Not Fixed","01-10-2026",
     "Round 5","Owner left v50e grouping behaviour as-is per instruction 02-10.","Deferred","F","",""),
    (118,"Dashboard","AI Bid Anomaly dropdown text extremely faint.","Low","Not Fixed","01-10-2026",
     "Round 5","CSS contrast fix. Batch D.","Open","D","",""),
    (119,"Vendors (Fill Form)","Document card buttons overlap at Address Proof.","Low","Not Fixed","01-10-2026",
     "Round 5","DocSlot action row flex-wrap + shrink-0 + truncate.","Fixed","B","v50j","02-10-2026"),
    (120,"Vendors (Fill Form)","Section K saved without 6 mandatory declarations.","High","Not Fixed","01-10-2026",
     "Round 5","Section E now has X/6 meter + amber borders + submit refuses. Backend 400s if any missing.","Fixed","B","v50j","02-10-2026"),
    (121,"Logging in","Forgot password says email sent but nothing arrives.","High","Not Fixed","01-10-2026",
     "Round 5","Resend DNS DKIM/SPF in Route 53 + new API key + suppression cleared + sender moved to apex. Live-verified delivered.","Fixed","A","v50g","02-10-2026"),
    (122,"Vendor Registration","Accepts 9-digit mobile numbers; should block with popup.","High","Not Fixed","01-10-2026",
     "Round 5","PhoneInput E.164 7-15 digit rule + inline error.","Verify","C","v50k",""),
    (123,"Login","Translation button on login shows no options.","Low","Not Fixed","01-10-2026",
     "Round 5","Not located on SignInE; needs user clarification on which screen.","Needs Info","A","",""),
    (124,"Home sign-in","Wrong user/pass + wrong role → no error.","Medium","Not Fixed","NA","",
     "SignInE now shows role-aware 8-second toast on every failure path.","Fixed","A","v50g","02-10-2026"),
]

wb = openpyxl.Workbook()

# ---------- Sheet 1: Tracker ----------
ws = wb.active
ws.title = "Bug Tracker v19"
headers = ["Sl No","Tab/Module","Bug / Observation","Priority","Status (Team)",
           "Retested Date","Team Remarks","Agent Triage / Root Cause",
           "Agent Status","Fix Batch","Fix Version","Verified Date"]
ws.append(headers)
for r in ROWS:
    ws.append(list(r))

widths = [9, 24, 55, 10, 16, 13, 32, 55, 15, 10, 12, 13]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill("solid", fgColor=GREEN)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER
ws.row_dimensions[1].height = 30
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:L{ws.max_row}"

pri_fill = {"High": RED, "Medium": AMBER, "Low": GREY, "Cosmetic": BLUE}
status_fill = {
    "Fixed": GREEN_OK, "Verify": BLUE, "Open": RED,
    "Deferred": GREY, "Needs Info": AMBER,
}
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
    if st in status_fill:
        row[8].font = Font(size=10, bold=True, color="FFFFFF")
        row[8].fill = PatternFill("solid", fgColor=status_fill[st])
        row[8].alignment = Alignment(horizontal="center", vertical="center")
    ver = str(row[10].value or "")
    if ver.startswith("v50"):
        row[10].fill = PatternFill("solid", fgColor=CREAM)
        row[10].font = Font(size=10, bold=True, color=PURPLE)
        row[10].alignment = Alignment(horizontal="center", vertical="center")

# ---------- Sheet 2: Release summary ----------
ws2 = wb.create_sheet("Releases v50g to v50l")
ws2["A1"] = "PMC release recap — 02 Oct 2026"
ws2["A1"].font = Font(bold=True, size=14, color=GREEN)
rel_rows = [
    ("", ""),
    ("v50g", "Masters restored (/admin/e/masters), Category master backend+UI (105 cats), tooltip readability, Section K declarations, sign-in error toasts."),
    ("v50h", "Create Notice country dropdown (30-country master), Auto-EMD by country+category, Approval Matrix per-step user assignee picker."),
    ("v50i", "Notice View + Edit modals, per-document View/Download/Delete, PATCH /notices + DELETE /notices/{ref}/document, draft Publish button."),
    ("v50j", "Permanent cure for stale UI: SwUpdateBanner (New version available - Refresh). No more hard refreshes after deploy. Also fixes Masters-first-login flicker."),
    ("v50k", "Download gating P0: /uploads/files requires admin bearer OR vendor cookie. GatedDownload component on public Notice Detail. Notices list row redesigned as 2-row card so long titles no longer collapse."),
    ("v50l", "Vendor Category Interest flow: supplier /vendor/categories page + admin Masters > Vendor requests tab with Approve/Reject. 5 new backend endpoints. Approve auto-adds to vendors.business_categories."),
    ("", ""),
    ("STATS", f"Total tracked bugs: {len(ROWS)} | Fixed: {sum(1 for r in ROWS if r[8]=='Fixed')} | Verify (team retest): {sum(1 for r in ROWS if r[8]=='Verify')} | Open: {sum(1 for r in ROWS if r[8]=='Open')} | Deferred: {sum(1 for r in ROWS if r[8]=='Deferred')} | Needs Info: {sum(1 for r in ROWS if r[8]=='Needs Info')}"),
    ("", ""),
    ("NEXT", "Batch D: Notices, Escrow (#13), Auctions (#39-41), L1 (#37), Reports (#45), Dashboard (#118), Notice list (#66). Also EMD Master editor UI."),
    ("NEXT", "Batch E: Public portal (#60). Then P0 security (SEC-001, SEC-002, SEC-003). Then E2E procurement regression."),
]
for a, b in rel_rows:
    ws2.append([a, b])
    if a.startswith("v50"):
        ws2.cell(row=ws2.max_row, column=1).font = Font(bold=True, color=PURPLE)
    elif a in ("STATS", "NEXT"):
        ws2.cell(row=ws2.max_row, column=1).font = Font(bold=True, color=GREEN)
ws2.column_dimensions["A"].width = 10
ws2.column_dimensions["B"].width = 160
for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)

wb.save(OUT)
print("Saved:", OUT)
print("Rows:", len(ROWS))
print("Fixed:", sum(1 for r in ROWS if r[8]=='Fixed'))
print("Verify:", sum(1 for r in ROWS if r[8]=='Verify'))
print("Open:", sum(1 for r in ROWS if r[8]=='Open'))
