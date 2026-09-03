"""Build the master PMC Managers bug tracker Excel — status of every bug
reported in QA rounds V1-V6, with fix approach + wave classification.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

OUT = Path("/app/deliverables/PMC_Bug_Tracker_v1.xlsx")
OUT.parent.mkdir(exist_ok=True)

# ---- Data ----
# Columns: ID, Title, Module, Severity, Status, Fix, Wave, Ship, Owner Notes
ROWS = [
    # ---- FIXED / SHIPPED (in v4b/v8c prod, plus Bug #5 in v8/v12 ready to deploy) ----
    (1,  "Clone as draft error 500", "Tender Builder", "P0", "FIXED", "order field auto-assigned in tender_templates.create_from_master", "Shipped v5/v10", "Prod live"),
    (3,  "Bidding Ops button logs out user", "Bidding Ops", "P0", "FIXED", "Promise.allSettled in BiddingOpsPanel.load — non-admin 403s no longer break chain", "Shipped v5/v10", "Prod live"),
    (4,  "Blank form download PDF fails", "Vendor Invites", "P1", "FIXED", "reportlab fallback PDF in vendor_invites.download_registration_template", "Shipped v5/v10", "Prod live"),
    (5,  "Notice creation as madhavi shows 'undefined'", "Notices (Admin)", "P1", "FIXED", "permissions.py DEFAULT_MATRIX reviewer.create=True; NoticesPanel defensive notice_ref + role-aware publish checkbox", "READY v8/v12", "In this zip"),
    (8,  "Invite Vendor not working", "Vendors", "P1", "CONFIRMED WORKING", "User confirmed 26-Aug — email working", "N/A", "No action"),
    (9,  "Vendor Add & Fill Full Form 'undefined' toast", "Vendors", "P1", "FIXED", "Defensive undefined fallback in AdminVendorCreate.submit", "Shipped v5/v10", "Prod live"),
    (11, "L1 Comparison Run hangs", "L1 Comparison", "P0", "FIXED", "45-sec Promise.race timeout in L1ComparisonPanel.run", "Shipped v5/v10", "Prod live"),
    (13, "Masters tab hangs", "Masters", "P0", "FIXED", "Promise.allSettled in MastersPanel.load", "Shipped v5/v10", "Prod live"),
    (14, "Escrow joint account created without officer info", "Escrow", "P1", "FIXED", "escrow.py strict role + email uniqueness validation", "Shipped v6", "Prod live"),
    (16, "Budget accepts negative numbers", "Notices/Budget", "P1", "FIXED", "NoticeIn budget_amount ge=0 + frontend min='0' + NaN guard", "Shipped v6/v11", "Prod live"),
    (24, "Publish checkbox disabled for Master Admin", "Notices (Admin)", "P1", "FIXED", "v12 gates disabled state on isMasterAdmin (=me.role==='admin')", "READY v8/v12", "In this zip"),
    (55, "Duplicate of #14 (Escrow blank joint account)", "Escrow", "P1", "FIXED", "See Bug 14", "Shipped v6", "Duplicate"),

    # ---- WAVE A: 'Created but not in list' pattern ----
    (2,  "New BOQ template not visible after submission", "BOQ Templates", "P1", "OPEN", "Investigate tenant_id scoping on boqs.list_boq_templates; verify BOQTemplatesTab calls onReload correctly after boqApi.createTemplate", "Wave A", "Backend + frontend"),
    (12, "New BOQ contract not showing in list", "BOQ Contracts", "P1", "OPEN", "Investigate contract_ref generation, tenant_id filter on contracts list; add cache-bust", "Wave A", "Backend"),
    (19, "New package shows created msg but not in list", "Packages", "P1", "OPEN", "createPackage returns 201 but load() may query wrong status. Force reload with 'all' filter, ensure default status='backlog'", "Wave A", "Frontend"),
    (30, "Newly activated vendor not appearing in Vendors table", "Vendors", "P1", "OPEN", "vendors.py list default filter may exclude 'pending_verify'. Add explicit status filter UI", "Wave A", "Backend + frontend"),
    (35, "Product catalog created but not in table", "Product Catalog", "P1", "OPEN", "ProductCatalogPanel.reload() runs after save, but if is_active default differs. Check product_id vs id normalization", "Wave A", "Frontend"),
    (37, "Package created but not in table (dup of #19)", "Packages", "P1", "OPEN", "See Bug 19", "Wave A", "Duplicate"),
    (42, "New reverse auction not listed as draft", "Reverse Auctions", "P1", "OPEN", "reverseAuctionApi.create returns id, but list() may not include it. Check tenant scoping in auction_live.list_reverse_auctions", "Wave A", "Backend"),
    (45, "Rejected company not shown in Rejected list", "Registrations", "P1", "OPEN", "adminApi.listRegistrations({status:'rejected'}) — verify backend accepts this filter. Status may be stored as 'rejected' vs 'REJECTED'", "Wave A", "Backend"),
    (50, "Draft not shown in needs_clarification tab; typo 'clarify recorded'", "Registrations", "P1", "OPEN", "Backend: /decision endpoint saves status='needs_clarification' but list filter case mismatch. Fix toast text 'clarify recorded' → 'clarification recorded'", "Wave A", "Backend + frontend"),

    # ---- WAVE B: Blank screen / re-login bugs ----
    (28, "Bulk Invite CSV — page goes blank or signs out", "Vendors — Bulk Invite", "P0", "OPEN", "BulkInviteModal.submit lacks catch on 403/500 → unhandled promise rejection. Wrap in try/catch + toast; ensure CSRF token present", "Wave B", "Frontend"),
    (39, "Generate Award Report page hangs", "Evaluation / Awards", "P0", "OPEN", "Long-running backend call needs Promise.race timeout + spinner; likely PDF generation timeout", "Wave B", "Backend + frontend"),
    (52, "Screen goes blank after bulk invite (dup of 28)", "Vendors — Bulk Invite", "P0", "OPEN", "See Bug 28", "Wave B", "Duplicate"),
    (57, "Screen goes blank after Generate Award Report (dup of 39)", "Awards & POs", "P0", "OPEN", "See Bug 39", "Wave B", "Duplicate"),
    (58, "Screen goes blank across flows, requires re-login", "General", "P0", "OPEN", "Add React error boundary at root; on unhandled rejection show toast + preserve auth. Root cause: unhandled thrown errors in async handlers", "Wave B", "Frontend"),
    (36, "Portal hangs on Audit click", "Audit", "P1", "OPEN", "AuditPanel probably paginating over all audit_events. Add server-side pagination + limit=100", "Wave B", "Backend + frontend"),

    # ---- WAVE C: Corrigenda + notice lifecycle ----
    (25, "Withdrawn corrigenda still visible as active", "Corrigenda / Notices", "P1", "OPEN", "corrigenda.py withdraw endpoint sets is_active=False but the public notice detail still shows. Fix: filter public /notices/{ref} to exclude is_active=False corrigenda", "Wave C", "Backend"),
    (26, "Corrigenda status not updated after Withdraw", "Corrigenda", "P1", "OPEN", "CorrigendaPanel refreshes list after withdraw, but item still shows Withdraw btn if is_active isn't returned. Confirm response body includes is_active", "Wave C", "Backend + frontend"),
    (43, "Reverse auction Start button doesn't go live", "Reverse Auctions", "P1", "OPEN", "auction_live.start endpoint may not set status='live' atomically. Add explicit status update + return updated doc", "Wave C", "Backend"),
    (44, "Reverse auction Close button doesn't close", "Reverse Auctions", "P1", "OPEN", "Similar to 43 — close endpoint status update", "Wave C", "Backend"),
    (60, "Corrigendum still visible after withdrawing (dup of 25)", "Corrigenda", "P1", "OPEN", "See Bug 25", "Wave C", "Duplicate"),

    # ---- WAVE D: Vendor + registration + supplier actions ----
    (6,  "Vendor mailing address error persists after entered", "Vendor Registration", "P1", "OPEN", "SectionB/C validation runs on stale state. Force controlled input + trim; validate mailing address separately", "Wave D", "Frontend"),
    (27, "Supplier Approve/Reject/Clarify actions not saved", "Registrations", "P1", "OPEN", "registrations.decide endpoint may return 200 but status not updated. Investigate _out() + audit_log ordering", "Wave D", "Backend"),
    (29, "Replace Registration Template — 'undefined' toast + no template name", "Vendors", "P1", "OPEN", "vendor_invites.replace_template response doesn't include template_name. Add fallback in frontend toast", "Wave D", "Backend + frontend"),
    (46, "Nudge Stale Drafts shows success but incorrect", "Registrations", "P1", "OPEN", "send-reminders returns reminded=0 but toast shows success. Show clearer message when no drafts qualify", "Wave D", "Frontend"),
    (47, "Can navigate past identity section without filling required fields", "Vendor Registration", "P1", "OPEN", "Section navigation should validate current section before allowing next. Add required-field guard in Section A/B", "Wave D", "Frontend"),
    (48, "Unable to download blank registration form (dup of #4?)", "Vendor Registration", "P1", "OPEN", "Verify with QA if this differs from Bug 4 which was fixed", "Wave D", "Investigate"),
    (51, "No notifications sent after nudging stale drafts", "Notifications", "P1", "OPEN", "send-reminders should push notifications alongside email. Add notify.push_admin() call", "Wave D", "Backend"),

    # ---- WAVE E: Validations, i18n, blank state, misc ----
    (7,  "Resume link not sent to email despite success message", "Vendor Registration / Email", "P1", "OPEN", "Resend integration — verify EMAIL_KEY env var propagates to Docker container. Add error log + toast on failure", "Wave E", "Backend"),
    (15, "AI Bid Anomaly score/deviation blank", "Dashboard", "P2", "OPEN", "bids_ai_compare.anomaly_check may return empty. Add default 'no anomalies detected' state + explain what it checks", "Wave E", "Backend + frontend"),
    (17, "Error clicking 'Review document' from DocuSign email", "DocuSign", "P1", "OPEN", "Docusign embedded signing URL expiry. Add error page + retry", "Wave E", "Backend"),
    (20, "Check status token — no error for invalid token", "Public Landing", "P2", "OPEN", "registrations.status endpoint returns 404 but frontend swallows. Show toast on invalid token", "Wave E", "Frontend"),
    (21, "Login shows console error", "Login", "P2", "OPEN", "Need actual console error text from QA. Likely a benign CORS or 401 preflight", "Wave E", "Investigate"),
    (22, "Notices form retains previous details", "Notices", "P2", "OPEN", "NoticesPanel setDraft resets title+description only. Full reset needed", "Wave E", "Frontend"),
    (23, "Unclear validation toast (10 char min)", "Notices Form", "P2", "OPEN", "Change toast to explicit 'Title needs 3+ chars, Description needs 10+ chars'", "Wave E", "Frontend"),
    (31, "Localization incomplete", "i18n", "P2", "OPEN", "Audit /app/frontend/src/i18n/*.json — fill missing keys in ru/kz", "Wave E", "Frontend"),
    (32, "Profile image not shown after re-login", "Profile", "P1", "OPEN", "admin/auth/me returns avatar_data_url but frontend may cache stale. Verify TopBar reloads on route change", "Wave E", "Frontend"),
    (33, "Missing email/mobile validation across forms", "Forms (general)", "P2", "OPEN", "Add zod/yup validation to Section A/B/C — email regex + phone digits-only", "Wave E", "Frontend"),
    (34, "Product catalog save doesn't persist", "Product Catalog", "P1", "OPEN", "PATCH /products/{id} returns 200 but 'Saved' toast fires without reload. Add reload() call", "Wave E", "Frontend"),
    (38, "Tender Builder content doesn't update on tab switch", "Tender Builder", "P1", "OPEN", "State not cleared between Tender/RFP/RFQ tabs. Reset activeTemplate on tab change", "Wave E", "Frontend"),
    (40, "L1 Comparison dropdown empty", "L1 Comparison", "P1", "OPEN", "Filter for notices with awarded bids. Verify status filter", "Wave E", "Frontend"),
    (41, "Regenerate documents doesn't work under Awards & POs", "Awards & POs", "P1", "OPEN", "awards.regenerate endpoint returns 200 but no visible change. Add version + timestamp on regenerated docs", "Wave E", "Backend"),
    (49, "Save snapshot to repo — JSON parsing error", "Stakeholder Reports", "P2", "OPEN", "reports.snapshot returns non-JSON on error. Wrap in try/catch, return JSON error body", "Wave E", "Backend"),
    (54, "Cancelled meeting still visible", "Meetings", "P1", "OPEN", "meetings.cancel sets status='cancelled' but list default doesn't filter. Add filter + hide by default", "Wave E", "Backend + frontend"),
    (56, "Rubric saved even with values > max", "Evaluation", "P1", "OPEN", "evaluations.save_rubric doesn't validate weights sum. Add server-side + client-side range check", "Wave E", "Backend + frontend"),

    # ---- WAVE F: Handbook (from PDF observations) ----
    ("F1","Trainee Handbook out-of-date (missing chapters)", "Docs", "P2", "OPEN", "Rewrite chapters for Permissions, Engagements, Help Requests, Portal Branding, AI features, role-to-tab map", "Wave F", "Docs"),

    # ---- WAVE G: Governance (from PDF observations) ----
    ("G1","Escrow dual-signature not enforced — same login can sign both", "Escrow", "P0-Governance", "OPEN", "Enforce at escrow.create_account: pmc_officer.email != escrow_officer.email AND neither login should hold both roles. Extend to sign-off: verify signer's user_id ≠ other officer's user_id", "Wave G", "Backend"),
    ("G2","COI not cross-checked against committee membership", "Evaluation / Committee", "P0-Governance", "OPEN", "Before evaluations.submit_scores: check db.coi_declarations for that committee_member + notice_ref. Block if missing", "Wave G", "Backend"),
    ("G3","Two access-control systems (Permissions vs Level) — no defined relationship", "Governance", "P1", "OPEN", "Document: Permissions matrix governs actions; Level is legacy from Wave 7 hierarchy. Consolidate or clarify in handbook", "Wave G", "Docs + Backend"),
    ("G4","Stakeholder Reports doesn't match description", "Reports", "P1", "OPEN", "Rename module or build the described procurement reports", "Wave G", "Product decision"),
    ("G5","Reverse Auction DRAFT exposes public link", "Reverse Auctions", "P1", "OPEN", "Hide bidder-URL until status='live'; verify draft link is 404 if visited before start", "Wave G", "Frontend + backend"),
]

# ---- Build workbook ----
wb = Workbook()
ws = wb.active
ws.title = "Bug Tracker"

HEADERS = ["Bug ID", "Title", "Module", "Severity", "Status", "Fix Approach", "Wave", "Ship / Notes"]
FILLS = {
    "FIXED": PatternFill("solid", fgColor="C6EFCE"),
    "CONFIRMED WORKING": PatternFill("solid", fgColor="C6EFCE"),
    "READY v8/v12": PatternFill("solid", fgColor="FFEB9C"),
    "OPEN": PatternFill("solid", fgColor="FFC7CE"),
    "Duplicate": PatternFill("solid", fgColor="E7E6E6"),
}
HEADER_FILL = PatternFill("solid", fgColor="0F1B3D")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
CELL_FONT = Font(size=10)
BORDER = Border(*[Side(style="thin", color="D0D0D0")] * 4)

# Header
for c, h in enumerate(HEADERS, 1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.fill = HEADER_FILL
    cell.font = HEADER_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER

# Rows
for r, row in enumerate(ROWS, 2):
    for c, val in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=val)
        cell.font = CELL_FONT
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = BORDER
    # Colour by status
    status = row[4]
    fill = FILLS.get(status) or FILLS.get(row[7]) if row[7] == "Duplicate" else FILLS.get(status)
    if fill:
        for c in range(1, 9):
            ws.cell(row=r, column=c).fill = fill

# Column widths
widths = [10, 55, 24, 14, 22, 70, 14, 26]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.row_dimensions[1].height = 32
ws.freeze_panes = "A2"

# ---- Second sheet: Wave summary ----
ws2 = wb.create_sheet("Wave Summary")
ws2.column_dimensions["A"].width = 12
ws2.column_dimensions["B"].width = 45
ws2.column_dimensions["C"].width = 15
ws2.column_dimensions["D"].width = 60

ws2.append(["Wave", "Theme", "Bug count", "Deploy plan"])
for c in range(1, 5):
    ws2.cell(row=1, column=c).fill = HEADER_FILL
    ws2.cell(row=1, column=c).font = HEADER_FONT
    ws2.cell(row=1, column=c).alignment = Alignment(horizontal="center", wrap_text=True)

waves = [
    ("Shipped", "Bugs 1, 3, 4, 8, 9, 11, 13, 14, 16, 55 — live on prod", 10, "Already live at www.pmcmanagers.com"),
    ("v8/v12", "Bug 5 (madhavi notice) + Bug 24 (publish checkbox) + Mongo/env guards + _temp_downloads stripped", 2, "In v8/v12 zips — deploy per README included"),
    ("Wave A", "Created-but-not-in-list pattern — 9 bugs (2, 12, 19, 30, 35, 37, 42, 45, 50)", 9, "Next wave — backend list filter audits + frontend reload() adds"),
    ("Wave B", "Blank-screen / re-login — 6 bugs (28, 36, 39, 52, 57, 58)", 6, "React error boundary + Promise.allSettled where missing"),
    ("Wave C", "Corrigenda withdraw + notice lifecycle — 5 bugs (25, 26, 43, 44, 60)", 5, "Backend status-update fixes"),
    ("Wave D", "Vendor + registration + supplier actions — 7 bugs (6, 27, 29, 46, 47, 48, 51)", 7, "Backend + frontend validation batch"),
    ("Wave E", "Validations, i18n, misc — 15 bugs", 15, "Small individual fixes; can ship rolling"),
    ("Wave F", "Handbook rewrite", 1, "Docs sprint — after all code fixes"),
    ("Wave G", "Governance (dual-sig enforcement, COI, RBAC) — 5 items", 5, "Investor-critical before code review"),
]
for w in waves:
    ws2.append(w)
    row_idx = ws2.max_row
    for c in range(1, 5):
        ws2.cell(row=row_idx, column=c).font = CELL_FONT
        ws2.cell(row=row_idx, column=c).alignment = Alignment(vertical="top", wrap_text=True)
        ws2.cell(row=row_idx, column=c).border = BORDER

# ---- Third sheet: Structural observations from PDF ----
ws3 = wb.create_sheet("Structural Observations")
ws3.column_dimensions["A"].width = 30
ws3.column_dimensions["B"].width = 100
ws3.append(["Module / Screen", "Recommendation"])
for c in range(1, 3):
    ws3.cell(row=1, column=c).fill = HEADER_FILL
    ws3.cell(row=1, column=c).font = HEADER_FONT

obs = [
    ("Dashboard", "AI Bid Anomaly Check — add one-line description above control + show what was flagged after run"),
    ("Dashboard", "Pipeline Funnel + Top-Priced Bids — make clickable → drill through to filtered Bidding Ops"),
    ("Registrations", "List view: surface submission_date; Nudge Stale Drafts — show threshold + preview count"),
    ("Vendors", "Bulk Invite: link sample CSV; warn about mid-registration template replacement; add status filter for 'pending_verify'"),
    ("Notices (admin)", "Add search/filter by status, closing date, template-linked flag; TEMPLATE LINKED tag → jump to template"),
    ("Corrigenda", "Require reason on Withdraw; log distinctly in Audit"),
    ("Tender Builder", "'All kinds' view or Kind column; show last-edited timestamp + revision indicator"),
    ("Bidding Ops — Committee", "Chairperson dropdown populate from selected Members only; validate quorum ≤ #members; replace Ctrl/Cmd multi-select with checkbox list; edit/dissolve committee actions; resend invite for pending externals"),
    ("Escrow", "Aging indicator + SLA alert threshold; filter transactions by vendor/bid/status; reconciliation summary vs bank balance"),
    ("Evaluation", "Add rationale note next to non-obvious role/permission combos"),
    ("L1 Comparison", "Empty state: state count + why excluded; surface active ranking rule; add PDF/Excel export"),
    ("Awards & POs", "Add confirmation on Regenerate + version documents"),
    ("DocuSign", "Envelope Log — flag most recent/authoritative envelope per doc type per award"),
    ("Reverse Auctions", "Post-auction summary/report; bid history; winning price"),
    ("Meetings", "Require notice_ref when scheduling OR clearly mark meetings as internal/not tender-linked"),
    ("Vendor Intel", "Legend for WL flag; clarify anonymized entry"),
    ("BOQ & Contracts", "Contracts sub-tab needs same review — export, filtering, version history"),
    ("Masters / Permissions", "Add/Clone role for org-specific narrower roles; extend matrix to cover tab-level visibility; show last-modified metadata on Permissions screen"),
    ("Packages", "Empty-column messages consistent with rest of app"),
    ("Audit", "Add filters by actor/type/date range"),
    ("Engagements", "Date/aging columns for receivables; require cancellation reason (Registrations pattern); link buyer name → vendor record"),
    ("Product Catalog", "Log price-change history per product"),
    ("Help Requests", "Requester identity, priority, category, assignee, aging fields"),
    ("Portal Branding", "Live preview + logo history + broader theming (color, favicon)"),
]
for o in obs:
    ws3.append(o)
    row_idx = ws3.max_row
    for c in range(1, 3):
        ws3.cell(row=row_idx, column=c).font = CELL_FONT
        ws3.cell(row=row_idx, column=c).alignment = Alignment(vertical="top", wrap_text=True)
        ws3.cell(row=row_idx, column=c).border = BORDER

wb.save(OUT)
print(f"Written {OUT}")
print(f"Size: {OUT.stat().st_size / 1024:.1f} KB")
print(f"Bug rows: {len(ROWS)}  ·  Waves: {len(waves)}  ·  Structural obs: {len(obs)}")
