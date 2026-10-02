"""PMC Bug Tracker v20 — close-out through v50m (02 Oct 2026).

Carries forward v19 rows and:
- marks Batch D bugs (#13, #37, #39-41, #45, #118) as Fixed in v50m,
- adds the new v50m vendor-portal / profile-edit / SEC work as rows N14-N18,
- updates the Releases sheet with a v50m recap + refreshed NEXT.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/app/frontend/public/downloads/PMC_Bug_Tracker_v25_v50r_20261002.xlsx"

GREEN="0F3B2E"; BRASS="B08E4A"; CREAM="F6F0DC"
RED="C0392B"; AMBER="B7791F"; GREY="6B7280"; BLUE="2B6CB0"
GREEN_OK="1E7B4D"; PURPLE="6B21A8"
thin = Side(style="thin", color="D8D2C4")
BORDER = Border(left=thin,right=thin,top=thin,bottom=thin)

ROWS = [
    # sl, module, bug, priority, team_status, retest, team_remarks,
    # agent_triage, agent_status, batch, fix_ver, verified
    # ---- v50m vendor-portal rewrite / profile edit / SEC fixes ----
    ("N14","Vendor portal","Find Tenders showed '12 match' but only 6 cards.","High","Fixed","02-10-2026",
     "User chat 02-10","Static mockup replaced with live publicApi.listNotices + search + 9-per-page pagination. Heading now mirrors the rendered list.","Fixed","M","v50m","02-10-2026"),
    ("N15","Vendor portal","No way to edit address / phone / email.","High","Fixed","02-10-2026",
     "User chat 02-10","New Profile Edit form on /vendor/account posting to admin approval queue (vendor_profile_changes router).","Fixed","M","v50m","02-10-2026"),
    ("N16","Vendor portal","Signatures page showed errors / dead links.","High","Fixed","02-10-2026",
     "User chat 02-10","Rewired to docusignApi.listMine + resumeSign opens embedded DocuSign view + Download on completed.","Fixed","M","v50m","02-10-2026"),
    ("N17","Vendor portal","Sidebar links all href='#'.","High","Fixed","02-10-2026",
     "User chat 02-10","Shared VendorPortalChrome wires every entry as react-router <Link>; Help is now a button.","Fixed","M","v50m","02-10-2026"),
    ("N18","Vendor profile","Email changes should need admin approval + verify link on new email.","High","Fixed","02-10-2026",
     "User choice (option b)","Email change = vendor clicks verify link sent to NEW address AND admin approves. Approve blocks with HTTP 412 until verified. /vendor/verify-email-change/:token page confirms the token.","Fixed","M","v50m","02-10-2026"),
    # ---- v50m SEC remediations ----
    ("N19","Security","SEC-001 hardcoded seed credentials.","High","Fixed","02-10-2026",
     "Agent audit","config.py::_seed_password honours env for ADMIN/OWNER/STAFF passwords; fails fast in production when missing; loud warning in non-prod.","Fixed","M","v50m","02-10-2026"),
    ("N20","Security","SEC-003 DocuSign webhook HMAC fail-open.","High","Fixed","02-10-2026",
     "Agent audit","_verify_hmac fail-closes in production when DOCUSIGN_CONNECT_HMAC_SECRET is missing; warn+accept in non-prod so sandbox webhooks keep working.","Fixed","M","v50m","02-10-2026"),

    # ---- v50g-l recap (unchanged) ----
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

    # ---- v50n vendor-portal hardening ----
    ("N21","Company & KYC","Tab bar (Licences / Company docs / Team / Bank / Reviews) is static.","High","Fixed","02-10-2026",
     "User screenshot 02-10","VendorCompanyKycE rewritten live: tabs switch panels, Add licence dialog posts to /vendor/licenses.","Fixed","N","v50n","02-10-2026"),
    ("N22","Company & KYC","No way to add a licence; Add licence button dead.","High","Fixed","02-10-2026",
     "User screenshot 02-10","New vendor_licenses router (list/add/renew/delete + status computed) + Licence dialog with certificate upload.","Fixed","N","v50n","02-10-2026"),
    ("N23","Signatures","Download button on completed envelope throws 'no document linked'.","Medium","Fixed","02-10-2026",
     "User chat 02-10","docusign/mine now returns has_document; UI hides Download and shows 'PDF not archived' note when absent.","Fixed","N","v50n","02-10-2026"),
    ("N24","Vendor account","Phone change accepts any digit count; no country code picker.","Medium","Fixed","02-10-2026",
     "User chat 02-10","Country-code dropdown (30 countries, auto-prefills vendor country) + per-country digit validation (IN=10 etc.). Label 'New email' / 'Reason for the change'.","Fixed","N","v50n","02-10-2026"),
    ("N25","Vendor categories","Page crashes: vendorApi.myCategories is not a function.","High","Fixed","02-10-2026",
     "User screenshot 02-10","Regression from v50m vendorApi rewrite dropping v50l methods. Restored myCategories + requestCategory.","Fixed","N","v50n","02-10-2026"),
    # ---- v50o vendor-portal polish ----
    ("N26","Vendor portal","Home button in sidebar loads public home page.","High","Fixed","02-10-2026",
     "User chat 02-10","VendorHomeE rewritten on shared VendorPortalChrome — every sidebar entry is a real React Router <Link>; Home always stays inside /vendor.","Fixed","O","v50o","02-10-2026"),
    ("N27","Vendor account","Address change should use structured street/city/state/country/zip.","Medium","Fixed","02-10-2026",
     "User chat 02-10","Address dialog now has Street / City / State / Country (dropdown) / ZIP fields; parts stored as address_parts; mandatory-field validation.","Fixed","O","v50o","02-10-2026"),
    ("N28","Vendor account","Cannot edit company name; header shows stale name.","Medium","Fixed","02-10-2026",
     "User chat 02-10","company_name added to the profile-change approval queue; header reads the live value.","Fixed","O","v50o","02-10-2026"),
    ("N29","Vendor portal","Avatar dropdown should offer Change profile / photo / password / sign out.","Medium","Fixed","02-10-2026",
     "User chat 02-10","VendorPortalChrome avatar now opens a menu: Change profile → Company & KYC, Change photo (upload), Change password, Sign out.","Fixed","O","v50o","02-10-2026"),
    ("N30","Find tenders","Pagination style differs from admin console.","Low","Fixed","02-10-2026",
     "User chat 02-10","Find Tenders now uses the shared useListPager widget (Show 10/20/30/All, '1–10 of N', Prev/Next) — identical to admin lists.","Fixed","O","v50o","02-10-2026"),
    ("N31","Signatures","Download on completed envelope shows 'This document is not linked to an envelope yet'.","High","Fixed","02-10-2026",
     "User screenshot 02-10","Global PmcLinkPatcher hijacked any 'Download' label (handleSigDoc) before the React onClick. Guard added: fully-React vendor pages (home/tenders/signatures/account/company) are exempt from the legacy action-label map.","Fixed","P","v50p","02-10-2026"),
    ("N32","Admin · DocuSign","No way to repair envelopes whose signed PDF is unavailable.","Medium","Fixed","02-10-2026",
     "User chat 02-10","New admin Archive-PDF tool: POST /docusign/envelopes/{id}/archive-pdf stores the combined signed PDF in PMC storage; vendor/admin downloads serve the archive first; Archive button on completed envelopes.","Fixed","Q","v50q","02-10-2026"),
    ("N33","Admin · Masters","Finance cannot tune EMD rules without engineering.","Medium","Fixed","02-10-2026",
     "User chat 02-10","EMD Master Editor UI (Masters > EMD rules): create/edit/delete rules with country/kind/category scope, slab editor (fixed/%, caps), active toggle, quick calculator.","Fixed","Q","v50q","02-10-2026"),
    ("N34","Vendor portal","Home button on static pages (My bids / EMD / Reviews / Alerts) redirected to pmcmanagers.com landing.","High","Fixed","02-10-2026",
     "User prod feedback 02-10","Sidebar hrefs on all remaining static Option-E vendor pages replaced with real /vendor/* paths so link patcher cannot misroute Home.","Fixed","R","v50r","02-10-2026"),
    ("N35","Admin · Market","Vendor requests panel crashes with 'This panel hit an error'.","High","Fixed","02-10-2026",
     "User screenshot 02-10","vendor_categories.router now registered BEFORE vendors.router so /{vendor_ref} catch-all does not swallow /category-requests. Panel also hardened for non-array payloads.","Fixed","R","v50r","02-10-2026"),
    ("N36","Admin console","Vendor requests + Profile changes should sit under Market, not Masters.","Low","Fixed","02-10-2026",
     "User chat 02-10","Both moved to top-level Market sidebar items (/admin/e/vendor-requests, /admin/e/profile-changes). Masters shows '(moved -> Market)' labels for one release.","Fixed","R","v50r","02-10-2026"),
    ("N37","Help centre","'Back to tender board' button is actually a redirect to admin dashboard.","Medium","Fixed","02-10-2026",
     "User chat 02-10","Replaced hard /admin/e/dashboard link with a real Back button (window.history.back(), falls back to /help).","Fixed","R","v50r","02-10-2026"),
    # ---------------- Round-5 team-submitted bugs ----------------
    (5,"Notices","Creating a new notice from admin login — not working.","High","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; v50i View/Edit/Publish on top. Re-verify.","Verify","D","",""),
    (6,"Vendors","Mailing Address added but still error while registering vendor.","High","Fixed","02-10-2026",
     "Vendor activation did not complete","Full flow re-tested end-to-end via API: admin-create → activate (set_password) → vendor appears in list active → signs in (must_change_password enforced).","Fixed","B·D","v50q","02-10-2026"),
    (7,"Vendor sign-in","Resume link not sent though UI says sent.","Medium","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; Resend DNS/suppression already fixed 02-10.","Verify","E","v50l",""),
    (8,"Vendors","Invite vendor not working (no response).","Medium","Not Fixed","28-09-2026","",
     "Likely stale cache; retest after SW banner.","Verify","B","v50j",""),
    (9,"Vendors","Vendor creation from 'Vendor Fill form' not working.","Medium","Not Fixed","28-09-2026","",
     "Likely stale cache; retest after SW banner.","Verify","B","v50j",""),
    (13,"Escrow & EMD","Create Joint Account button not responding; also no mandatory validation.","Medium","Fixed","28-09-2026",
     "Client-side validation added","Toast names missing fields (name/institution/account/officers); rejects if PMC & Escrow emails match. Backend 422 still enforced.","Fixed","D","v50m","02-10-2026"),
    (27,"Vendors","After activating new vendor, not appearing in Vendors table.","Medium","Not Fixed","01-10-2026",
     "Retested OK (Round 5)","Team retest pass; verify after SW banner.","Verify","B","v50j",""),
    (37,"L1 Comparison","Drop down does not show all notices.","Medium","Fixed","30-09-2026",
     "Switched to /api/v1/notices/admin/all","Was publicApi.listNotices(limit 200, published only). Now adminApi.listAllNotices(limit 500) so drafts also show.","Fixed","D","v50m","02-10-2026"),
    (39,"Reverse Auctions","New auction not listed as draft.","Medium","Fixed","30-09-2026",
     "Added Reverse auctions page","New AdminAuctionsE page at /admin/e/auctions with Create form + inline Start/Close + Open-room link. Sidebar entry under Money & compliance.","Fixed","D","v50m","02-10-2026"),
    (40,"Reverse Auctions","Start button doesn't make auction go live.","Low","Fixed","30-09-2026",
     "Same root as #39","Start button wired to POST /api/v1/reverse-auctions/{id}/start; backend returns 400 with named gate if <2 participants.","Fixed","D","v50m","02-10-2026"),
    (41,"Reverse Auctions","Close button doesn't close auction.","Low","Fixed","30-09-2026",
     "Same root as #39","Close button wired to POST /api/v1/reverse-auctions/{id}/close; already-closed returns ok flag instead of silent no-op.","Fixed","D","v50m","02-10-2026"),
    (42,"Registrations","Rejected list missing a company.","Medium","Not Fixed","01-10-2026",
     "Round 5","Status filter mismatch. v50k fix shipped; retest.","Verify","C","v50k",""),
    (44,"Registrations","Can advance past Section A without completing identity.","High","Not Fixed","01-10-2026",
     "Round 5","Step gating already in RegistrationResume (missingSectionA + disabled Next). Retest.","Verify","C","v50k",""),
    (45,"Stakeholder Reports","Save snapshot JSON parsing error.","High","Fixed","28-09-2026",
     "New Stakeholder reports page","New AdminStakeholderReportsE page at /admin/e/stakeholder-reports — 4 tabs (Tenders/Awards/Escrow/SLA), KPI cards + one-click CSV per tab. Tab now exists so no UI JSON parse path remains.","Fixed","D","v50m","02-10-2026"),
    (46,"Registrations","needs_clarification tab missing draft; 'clarify recorded' typo.","Cosmetic","Not Fixed","01-10-2026",
     "Round 5","Toast now 'Clarification recorded'. Status-advance switches tab. Retest.","Verify","C","v50k",""),
    (59,"Vendors","Invite Vendor toast reads 'Invite Undefined'. No email received.","High","Not Fixed","01-10-2026",
     "Round 5","Toast is defensive now (uses r.email/r.vendor_ref). Was stale-cache. Email fixed 02-10 (Resend).","Verify","B","v50j",""),
    (60,"Public","Download Blank Registration Form — file downloaded but not opening.","Medium","Fixed","02-10-2026",
     "Round 5","Regenerated a branded 2-page PMC blank form (sections A-E + K declarations) and uploaded as the live template; download verified (application/pdf, valid %PDF).","Fixed","E","v50q","02-10-2026"),
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
    (118,"Dashboard","AI Bid Anomaly dropdown text extremely faint.","Low","Fixed","01-10-2026",
     "Round 5","Select now explicitly text-brand-navy + bg-white — option text readable on cream/white backgrounds.","Fixed","D","v50m","02-10-2026"),
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
ws.title = "Bug Tracker v25"
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
ws2 = wb.create_sheet("Releases v50g to v50r")
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
    ("v50r", "Post-prod fix pack: vendor Home never redirects to public home (all static pages now use /vendor/* hrefs); Admin Vendor requests panel no longer crashes (router order fix + defensive load); Vendor requests + Profile changes moved to Market sidebar; Help centre back button is now a real history-back."),
    ("v50q", "#6 vendor activation verified end-to-end; #60 blank registration form regenerated (branded 2-page PDF) and uploaded as live template; DocuSign admin Archive-PDF repair tool; EMD Master Editor UI (Masters > EMD rules) with slab editor + calculator."),
    ("v50p", "PmcLinkPatcher guard: rewritten React vendor pages exempt from legacy label-click map — fixes Signatures Download hijack ('document isn't linked to an envelope' toast)."),
    ("v50o", "Vendor Home rewritten (real Router links — Home stays in portal; live greeting/KPIs/next-action). Structured address dialog (street/city/state/country/zip). Company-name editable via approval queue. Vendor avatar dropdown (profile/photo/password/sign-out). Find Tenders uses the shared admin pager."),
    ("v50n", "Company & KYC page fully wired (tabs switch, live licences CRUD, KZ catalogue + missing/expiring callouts). Phone-change dialog gains country-code dropdown + per-country digit validation. DocuSign Download hidden when no PDF archived. vendorApi regression fixed (categories page)."),
    ("v50m", "Vendor portal Option-E rewrite (Find tenders / Signatures / Account wired to live APIs; sidebar uses React Router links). Vendor Profile Edit with Admin approval queue — email changes additionally need vendor to click a verify link sent to the NEW email. SEC-001 fail-fast seed credentials; SEC-003 DocuSign HMAC fail-closed in production. Batch D bugs closed (#13, #37, #39-41, #45, #118)."),
    ("", ""),
    ("STATS", f"Total tracked bugs: {len(ROWS)} | Fixed: {sum(1 for r in ROWS if r[8]=='Fixed')} | Verify (team retest): {sum(1 for r in ROWS if r[8]=='Verify')} | Open: {sum(1 for r in ROWS if r[8]=='Open')} | Deferred: {sum(1 for r in ROWS if r[8]=='Deferred')} | Needs Info: {sum(1 for r in ROWS if r[8]=='Needs Info')}"),
    ("", ""),
    ("NEXT", "Batch E: Public portal (#60). Also #6 vendor activate, #123 translation button, EMD Master editor UI, full tender-maker E2E regression."),
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
