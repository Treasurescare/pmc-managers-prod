"""PMC Bug Tracker v18 — v50g close-out (02 Oct 2026).
Rolls forward v17: marks Batch 0 (new) + Batch A as Fixed/Deferred."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/app/frontend/public/downloads/PMC_Bug_Tracker_v18_v50g_20261002.xlsx"

GREEN="0F3B2E"; BRASS="B08E4A"; CREAM="F6F0DC"
RED="C0392B"; AMBER="B7791F"; GREY="6B7280"; BLUE="2B6CB0"; GREEN_OK="1E7B4D"
thin = Side(style="thin", color="D8D2C4"); BORDER = Border(left=thin,right=thin,top=thin,bottom=thin)

# NEW items from user chat (v50g batch 0)
# N1 = Masters tab missing
# N2 = Category master from backend
# N3 = Tooltip white-on-cream

ROWS = [
    # sl, module, bug, priority, team_status, retest, team_remarks, agent_triage, agent_status, batch, fix_ver, verified
    ("N1","Admin console","Entire Masters tab is gone — where are the masters now.","High","Reported 02-10-2026","",
     "Masters was accessible only via legacy /admin?tab=masters; no link in Option E sidebar.",
     "Added /admin/e/masters route + sidebar entry + E_TAB_ROUTES redirect so legacy URL redirects correctly.",
     "Fixed — retest after deploy","0","v50g","02-10-2026"),
    ("N2","Admin console","Need a Category master coming from the backend.","High","Reported 02-10-2026","",
     "Category was hardcoded free-text; no CRUD. Required by Notices/Tender Builder.",
     "Added /api/v1/masters/categories CRUD (list/public/create/patch/delete). Auto-seeded on startup: 87 UNSPSC + 18 KZ legacy = 105 categories. New Categories tab in Masters with search/filter/add/deactivate. Create Notice form now uses backend dropdown.",
     "Fixed — retest after deploy","0","v50g","02-10-2026"),
    ("N3","Admin console","Tooltip buttons are in white colour and not readable on white/cream background.","Medium","Reported 02-10-2026","",
     "Shadcn TooltipContent used bg-primary → white in Option E theme. Hover tooltips on ⓘ info dots unreadable.",
     "Overrode TooltipContent inline style: dark forest-green (#0B1A14) bg + white text + brass border. Readable on every page.",
     "Fixed — retest after deploy","0","v50g","02-10-2026"),
    (5,"Notices","Creating a new notice from admin login - not working.","High","Not Fixed","01-10-2026",
     "Retested successfully. New notice created with DRAFT badge. Round 5",
     "Team's own retest reports pass. v50g unchanged — verify.",
     "Verify","Batch D (pending)","","" ),
    (6,"Vendors","Mailing Address is added. Still receiving the error message while registering the vendor.","High","Not Fixed","28-09-2026",
     "Vendor activation did not complete, no success message.",
     "Needs: VendorsPanel activate API response handling + success toast.",
     "Open","Batch B","","" ),
    (7,"Vendor Signin","Resume link not sent to mail id provided although message says sent.","Medium","Not Fixed","01-10-2026",
     "Retested successfully (Round 5).",
     "Team retest pass; today's Resend DNS/suppression fix should keep it working.",
     "Verify","Batch E","","" ),
    (8,"Vendors","Invite vendor not working. Clicking Send Invitation produces no response.","","Not Fixed","28-09-2026","",
     "Needs: vendor_invites API call + response handling fix.",
     "Open","Batch B","",""),
    (9,"Vendors","Vendor creation from 'Vendor Fill form' not working.","","Not Fixed","28-09-2026","",
     "Needs: form validation + submit path trace.",
     "Open","Batch B","",""),
    (13,"Escrow & EMD","Create Joint Account button not responding; also allows blank mandatory fields.","","Not Fixed","28-09-2026","",
     "Button dead + missing mandatory-field validation.",
     "Open","Batch D","",""),
    (27,"Vendors","After adding/activating new vendor, not appearing in Vendors table.","","Not Fixed","01-10-2026",
     "After approval, it appeared in Vendors table.",
     "Team retest pass — verify list refresh.",
     "Verify","Batch B","",""),
    (37,"L1 Comparison","Drop down does not show all notices.","","Not Fixed","30-09-2026","",
     "Dropdown source filter mismatch; align with /notices/admin/all.",
     "Open","Batch D","",""),
    (39,"Reverse Auctions","New Reverse Auction created but not listed as draft.","Medium","Not Fixed","30-09-2026",
     "Cannot find the tab for Reverse Auctions.",
     "Reverse Auctions tab missing from E console sidebar; needs route + sidebar + list refresh.",
     "Open","Batch D","",""),
    (40,"Reverse Auctions","Start button doesn't make notice go live.","Low","Not Fixed","30-09-2026",
     "Cannot find the tab.","Same root as #39.","Open","Batch D","",""),
    (41,"Reverse Auctions","Close button doesn't close auction.","","Not Fixed","30-09-2026",
     "Cannot find the tab.","Same root as #39.","Open","Batch D","",""),
    (42,"Registrations","Rejected list missing a company.","Medium","Not Fixed","01-10-2026","Round 5",
     "Rejected tab filter vs backend status mismatch.","Open","Batch C","",""),
    (44,"Registrations","Allows advancing to 'contact and signatory' without completing identity info.","High","Not Fixed","01-10-2026","Round 5",
     "Wizard step gating missing — block Next until required fields valid.","Open","Batch C","",""),
    (45,"Stakeholder Reports","Save snapshot fails with JSON parsing error.","High","Not Fixed","28-09-2026",
     "Cannot find the tab for Stakeholder reports.",
     "Tab missing + backend snapshot endpoint returning non-JSON.","Open","Batch D","",""),
    (46,"Registrations","Submitted draft not shown in needs_clarification tab; typo 'clarify recorded'.","Cosmetic","Not Fixed","01-10-2026","Round 5",
     "(a) status not moving to needs_clarification tab; (b) toast typo fix.","Open","Batch C","",""),
    (59,"Vendors","Invite Vendor success message shows 'Invite Undefined'. No email received.","","Not Fixed","01-10-2026","Round 5",
     "Success toast uses undefined name var; email path — retest after Resend fix.","Open","Batch B","",""),
    (60,"Public","Download Blank Registration Form: file downloaded but not opening.","","Not Fixed","01-10-2026","Round 5",
     "Template file corrupt/wrong content-type.","Open","Batch E","",""),
    (61,"Registrations","APPROVE click success toast but status not updating.","","Not Fixed","01-10-2026","Round 5",
     "Approve updates DB but list not refreshing / role-gated path.","Open","Batch C","",""),
    (62,"Vendors","Bulk invite CSV gives an error message.","","Not Fixed","01-10-2026","Round 5",
     "Bulk invite CSV parse/validation error — need exact message.","Open","Batch B","",""),
    (63,"Vendors","Add & Fill Full Form — user id not listed in Vendors list after creation.","","Not Fixed","01-10-2026","Round 5",
     "Vendor created but list query excludes it or list not refreshed.","Open","Batch B","",""),
    (64,"Registrations","Reject click success toast but still shows as submitted.","","Not Fixed","01-10-2026","Round 5",
     "Same family as #61.","Open","Batch C","",""),
    (65,"Registrations","Request Clarification click success toast but still submitted.","","Not Fixed","01-10-2026","Round 5",
     "Same family as #61/#64.","Open","Batch C","",""),
    (66,"Notices","New Notice created, dashboard counter +1, but not listed under Notices tab as draft.","","Not Fixed","01-10-2026","Round 5",
     "Notices list filter hides drafts for non-master roles.","Open","Batch D","",""),
    (99,"Tender Builder","Country filter does not filter Master Library templates.","","Not Fixed","01-10-2026","Round 5",
     "CONFLICT: v50e intentionally shows ALL masters grouped by country per owner request. Confirm which behaviour wins.",
     "Needs Decision","Batch F","",""),
    (118,"Dashboard","AI Bid Anomaly dropdown text is extremely faint.","","Not Fixed","01-10-2026","Round 5",
     "CSS contrast on select options in AI compare panel.","Open","Batch D","",""),
    (119,"Vendors – Fill Form","Document card buttons/icons overlap around Address Proof actions.","","Not Fixed","01-10-2026","Round 5",
     "CSS overlap on document card action row.","Open","Batch B","",""),
    (120,"Vendors – Fill Form","Section K can be saved without the 6 mandatory declarations.","","Not Fixed","01-10-2026","Round 5",
     "Add client+server validation for 6 mandatory declarations.","Open","Batch B","",""),
    (121,"Logging in","Forgot password says email sent but nothing arrives.","","Not Fixed","01-10-2026","Round 5",
     "FIXED 02-10-2026: Resend suppression list cleared + Route 53 DKIM/SPF CNAMEs + new API key + sender domain switched to apex. Verified delivered live.",
     "Fixed — retest after v50g deploy","Batch A","v50g","02-10-2026"),
    (122,"Vendor Registration","Accepts 9-digit mobile numbers; should block with popup.","High","Not Fixed","01-10-2026","Round 5",
     "Phone validation (min length + country format) on registration step 1.","Open","Batch C","",""),
    (123,"Logging in","Translation button on login shows no options.","","Not Fixed","01-10-2026","Round 5",
     "No translation button on current /login route (SignInE). Likely on legacy /vendor/login or /admin/login — needs user to confirm which screen.",
     "Needs Clarification","Batch A","",""),
    (124,"Home → sign in","Wrong user/pass gives no error when wrong role is selected.","Medium","Not Fixed","NA","",
     "FIXED v50g: Explicit role-aware error toast with 8s duration on wrong credentials for Supplier/PMC staff/Administrator.",
     "Fixed — retest after v50g deploy","Batch A","v50g","02-10-2026"),
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Bug Tracker v18"
headers = ["Sl No","Tab/Module","Bug / Observation","Priority","Status (Team)","Retested Date",
           "Team Remarks","Agent Triage / Root Cause","Agent Status","Fix Batch","Fix Version","Verified Date"]
ws.append(headers)
for r in ROWS:
    ws.append(list(r))

widths = [8,22,55,10,18,13,45,55,30,10,12,13]
for i,w in enumerate(widths,1):
    ws.column_dimensions[get_column_letter(i)].width=w

for cell in ws[1]:
    cell.font = Font(bold=True,color="FFFFFF",size=11)
    cell.fill = PatternFill("solid",fgColor=GREEN)
    cell.alignment = Alignment(horizontal="center",vertical="center",wrap_text=True)
    cell.border = BORDER
ws.row_dimensions[1].height=30
ws.freeze_panes="A2"
ws.auto_filter.ref=f"A1:L{ws.max_row}"

pri_fill = {"High":RED,"Medium":AMBER,"Low":GREY,"Cosmetic":BLUE}
for row in ws.iter_rows(min_row=2,max_row=ws.max_row):
    for cell in row:
        cell.border = BORDER
        cell.alignment = Alignment(vertical="top",wrap_text=True)
        cell.font = Font(size=10)
    p = row[3].value
    if p in pri_fill:
        row[3].font = Font(size=10,bold=True,color="FFFFFF")
        row[3].fill = PatternFill("solid",fgColor=pri_fill[p])
        row[3].alignment = Alignment(horizontal="center",vertical="center")
    st = str(row[8].value or "")
    if st.startswith("Fixed"):
        row[8].font = Font(size=10,bold=True,color="FFFFFF")
        row[8].fill = PatternFill("solid",fgColor=GREEN_OK)
    elif st == "Verify":
        row[8].font = Font(size=10,bold=True,color="FFFFFF")
        row[8].fill = PatternFill("solid",fgColor=BLUE)
    elif st in ("Needs Decision","Needs Clarification"):
        row[8].font = Font(size=10,bold=True,color="FFFFFF")
        row[8].fill = PatternFill("solid",fgColor=AMBER)

ws2 = wb.create_sheet("Release notes v50g")
ws2["A1"] = "v50g — Batch 0 + Batch A close-out (02 Oct 2026)"
ws2["A1"].font = Font(bold=True,size=14,color=GREEN)
notes = [
    "", "FIXED in v50g:",
    "• NEW: Masters tab restored at /admin/e/masters with sidebar entry.",
    "• NEW: Procurement Category master backend CRUD + 105 seeded categories (87 UNSPSC + 18 KZ legacy).",
    "• NEW: Categories tab inside Masters with search/filter/add/deactivate.",
    "• NEW: Create Notice Category field is now a backend-driven dropdown.",
    "• NEW: Tooltip readability (dark bg + white text + brass border) across all pages.",
    "• #121: Resend email delivery works (DNS + API key + suppression cleared).",
    "• #124: Role-aware sign-in error toast replaces silent failure.",
    "",
    "DEFERRED / NEEDS INPUT:",
    "• #99 (Tender Builder country filter): CONFLICT between team request vs owner request. Confirm desired behaviour.",
    "• #123 (translation button): screen not located. Confirm which login screen has the button.",
    "",
    "NEXT BATCHES:",
    "• Batch B — Vendors (bugs 6, 8, 9, 27, 59, 62, 63, 119, 120)",
    "• Batch C — Registrations (bugs 42, 44, 46, 61, 64, 65, 122)",
    "• Batch D — Notices/Escrow/Auctions/L1/Reports/Dashboard (bugs 5, 13, 37, 39, 40, 41, 45, 66, 118)",
    "• Batch E — Public portal + vendor sign-in (bugs 7, 60)",
    "• Batch F — Tender Builder (bug 99 pending decision)",
    "• After all batches: Full E2E procurement regression (DPR → tender → publish → bid → EMD → award → DocuSign).",
]
for n in notes:
    ws2.append([n])
ws2.column_dimensions["A"].width = 120

wb.save(OUT)
print("Saved:", OUT)
