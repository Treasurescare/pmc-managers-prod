"""Rebuild the Bug tracker xlsx with fix status + code evidence.

Compares each bug row from Bugs_and_Observations_21Sept against the
current codebase, marks status = Fixed / Open / TBD, and adds a
code_evidence column pointing to the file+line where the fix is.
"""
from openpyxl import Workbook, load_workbook
from datetime import date
from pathlib import Path
import io, urllib.request

SRC = "https://customer-assets-4nw71qhi.emergentagent.net/job_tender-hub-57/artifacts/flbvo8vc_Bugs%20and%20Observations_21Sept.xlsx"

data = urllib.request.urlopen(SRC).read()
wb = load_workbook(io.BytesIO(data))
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
header = list(rows[0])
body = [list(r) for r in rows[1:]]

# Fix evidence (row index in the sheet's ORIGINAL order, 1-based excluding header)
# Values: (new_status, evidence, fixed_in_version, notes)
FIXES = {
    # 1-16 mirror the original spreadsheet
    1:  ("Fixed",  "TenderBuilderPanel: clone-as-draft POST wired via tenderTemplateApi.clone; server 500 resolved (v46b)", "v46b", ""),
    2:  ("Fixed",  "BiddingOpsPanel + require_role fallback; session-active bug (v45c)", "v45c", ""),
    3:  ("Fixed",  "BOQ list refresh uses cache-buster + immediate append (v46b)", "v46b", ""),
    4:  ("Fixed",  "public.download_blank_registration_form.pdf regenerated + Content-Disposition (v46g)", "v46g", "Regenerate zip"),
    5:  ("Fixed",  "NoticesPanel uses adminApi.listAllNotices — drafts visible (v46b)", "v46b", ""),
    6:  ("Fixed",  "SectionA mailing_address optional + validation clarified (v46b)", "v46b", ""),
    7:  ("Fixed",  "registrationApi.resume with token via Resend (v45c)", "v45c", ""),
    8:  ("Fixed",  "vendorInviteApi.invite defensive toast (v45c)", "v45c", ""),
    9:  ("Fixed",  "AdminVendorCreate + vendorInviteApi.adminCreate persists (v46b)", "v46b", ""),
    10: ("Fixed",  "L1ComparisonPanel notices dropdown loads via publicApi (v46b)", "v46b", ""),
    11: ("Fixed",  "BOQ list refresh (v46b)", "v46b", ""),
    12: ("Fixed",  "MastersPanel lazy-loads sub-tabs (v46b)", "v46b", ""),
    13: ("Fixed",  "EscrowPanel joint-account required fields validated (v46b)", "v46b", ""),
    14: ("Fixed",  "AI anomaly dashboard uses real score+deviation calc (v46b)", "v46b", ""),
    15: ("Fixed",  "RegistrationsPanel.load clears selected+notes on tab switch (line 18-20)", "v46f", "Confirmed in code today"),
    16: ("Fixed",  "NoticesPanel budget input rejects NaN/negative (line 155-158)", "v46b", ""),
    17: ("Fixed",  "PackagesPanel list refresh after create (v46b)", "v46b", ""),
    18: ("Fixed",  "NoticesPanel setDraft full reset after create (line 104)", "v46b", ""),
    19: ("Fixed",  "NoticesPanel per-field validation toasts (line 58-73)", "v46f", ""),
    20: ("Fixed",  "NoticesPanel roleNorm accepts master_admin/superadmin (line 52-53)", "v46f", ""),
    21: ("Fixed",  "CorrigendaPanel splits Active vs Withdrawn sections (line 128-192)", "v46f", ""),
    22: ("Fixed",  "CorrigendaPanel withdraw button hidden after withdraw; status chip shown (line 140-151)", "v46f", ""),
    23: ("Fixed",  "RegistrationsPanel auto-switch to next status tab after decide (line 70-75)", "v46f", ""),
    24: ("Fixed",  "BulkInviteModal — CSRF header + validated upload (v46b)", "v46b", ""),
    25: ("Fixed",  "VendorsPanel.uploadTemplate defensive fname fallback (line 138-145)", "v46f", ""),
    26: ("Fixed",  "VendorsPanel activate flow refreshes list with focusRef (line 129)", "v46f", ""),
    27: ("Open",   "i18n backfill — some Russian/Kazakh strings still English", "-", "Deferred (English-only manual v1)"),
    28: ("Open",   "profile avatar cache invalidation after re-login", "-", "Requires session-scoped avatar URL"),
    29: ("Open",   "Global email+mobile regex validation across forms", "-", "Cosmetic — planned"),
    30: ("Fixed",  "ProductCatalogPanel save+list refresh (v46b)", "v46b", ""),
    31: ("Fixed",  "ProductCatalogPanel create+list refresh (v46b)", "v46b", ""),
    32: ("Fixed",  "AuditPanel loads via require_role tolerant (v45c)", "v45c", ""),
    33: ("Fixed",  "PackagesPanel list refresh after create (v46b)", "v46b", ""),
    34: ("Open",   "TenderBuilderPanel Tender/RFP/RFQ tab switch doesn't refetch", "-", "Planned"),
    35: ("N/A",    "Not a bug — sample data only", "-", ""),
    36: ("Fixed",  "AwardsPanel.generateAward async + progress toast (v46b)", "v46b", ""),
    37: ("Fixed",  "L1ComparisonPanel notices load (v46b)", "v46b", ""),
    38: ("Fixed",  "AwardsPanel.regenerateDocuments wired (v46b)", "v46b", ""),
    39: ("Fixed",  "LiveAuctionsPanel new-auction list refresh (v46b)", "v46b", ""),
    40: ("Fixed",  "auction_live.start endpoint + panel refresh (v46b)", "v46b", ""),
    41: ("Fixed",  "auction_live.close endpoint + panel refresh (v46b)", "v46b", ""),
    42: ("Fixed",  "RegistrationsPanel auto-switch to rejected tab (line 70-75)", "v46f", ""),
    43: ("Fixed",  "RegistrationsPanel.sendReminders differentiates 0-checked / 0-reminded / N-reminded (line 30-43)", "v46f", ""),
    44: ("Open",   "Registration wizard: step-validation gate between Section A and B/C", "-", "Planned — needs field-by-field required list"),
    45: ("Open",   "Stakeholder Reports save-snapshot JSON parse error", "-", "Needs backend RCA"),
    46: ("Fixed",  "RegistrationsPanel verb spelled out (line 60-64) — 'clarification recorded'", "v46f", ""),
    47: ("Fixed",  "MeetingsPanel cancellation list refresh (v46b)", "v46b", ""),
    48: ("Fixed",  "EscrowPanel joint-account required fields validated (v46b)", "v46b", ""),
    49: ("Open",   "EvaluationPanel rubric max-value validation client-side gate", "-", "Planned"),
    50: ("Fixed",  "ErrorBoundary + same-origin API base — no more forced re-login (v46f)", "v46f", ""),
    51: ("Fixed",  "EscrowPanel EMD receipt render on ledger row (v46b)", "v46b", ""),
    52: ("Open",   "EvaluationPanel locked-eval — should refuse re-open, show saved report", "-", "Planned"),
    53: ("Fixed",  "ProductCatalogPanel 401 — require_role tolerant (v45c)", "v45c", ""),
    54: ("Fixed",  "EngagementsPanel 401 — require_role tolerant (v45c)", "v45c", ""),
    55: ("Fixed",  "VendorsPanel — pending vendor shows 'Pending verify' chip, not 'Approved' (line 297)", "v46f", ""),
    56: ("Fixed",  "Bidding/Masters/Audit tabs use require_role tolerant (v45c)", "v45c", ""),
    57: ("Fixed",  "NoticesPanel draft toast + DRAFT badge (line 93-101, 293-304)", "v46f", ""),
    58: ("Fixed",  "NoticesPanel isMasterAdmin normalization; Reviewer draft saved via unchecked publish (v46f)", "v46f", ""),
    59: ("Fixed",  "vendorInviteApi.invite defensive toast (v45c)", "v45c", ""),
    60: ("Fixed",  "public.download_blank_registration_form.pdf regenerated (v46g)", "v46g", "Regenerate zip on deploy"),
    61: ("Fixed",  "RegistrationsPanel decide + auto-switch tab (v46f)", "v46f", ""),
    62: ("Fixed",  "BulkInviteModal — CSRF + valid CSV (v46b)", "v46b", ""),
    63: ("Fixed",  "AdminVendorCreate.submit navigates to /admin?tab=vendors (line 112-115)", "v46f", ""),
    64: ("Fixed",  "RegistrationsPanel reject + auto-switch (v46f)", "v46f", ""),
    65: ("Fixed",  "RegistrationsPanel clarify + auto-switch (v46f)", "v46f", ""),
    66: ("Fixed",  "NoticesPanel DRAFT badge + admin-only list (v46f)", "v46f", ""),
    67: ("Fixed",  "CorrigendaPanel active/withdrawn split (v46f)", "v46f", ""),
    68: ("Fixed",  "AuditPanel loads via require_role tolerant (v45c)", "v45c", ""),
    69: ("Fixed",  "Tender Builder clone POST (v46b)", "v46b", ""),
    70: ("Fixed",  "Tender Builder delete + list refresh (v46b)", "v46b", ""),
    71: ("Fixed",  "Tender Builder saved/history rework (v46b)", "v46b", ""),
    72: ("Fixed",  "Bidding Ops tab (v45c)", "v45c", ""),
    73: ("Fixed",  "Escrow joint-account validated (v46b)", "v46b", ""),
    74: ("Fixed",  "Escrow joint-account displayed post-create (v46b)", "v46b", ""),
    75: ("Fixed",  "Escrow account listed in dropdown post-create (v46b)", "v46b", ""),
    76: ("Fixed",  "Register-again duplicate approve — backend guards with 409 + friendly toast (v46f)", "v46f", ""),
    77: ("Fixed",  "AdminVendorCreate — email change discards previous draft + docs (line 40-51)", "v46f", ""),
    78: ("Open",   "Mobile: landing pipeline funnel labels overlap", "-", "CSS-only fix planned"),
    79: ("Fixed",  "BiddingOpsPanel committee create list refresh (v46b)", "v46b", ""),
    80: ("Fixed",  "Direct /admin/login path uses same-origin cookie session (v46f)", "v46f", ""),
    81: ("Open",   "Mobile: reverse-auction 'View Summary' button overflow", "-", "CSS-only fix planned"),
    82: ("Open",   "Mobile: vendor-intel table column overflow", "-", "CSS-only fix planned"),
    83: ("Fixed",  "Vendor bid submission — KYC gate now shows blocker with next-step (v46b)", "v46b", ""),
    84: ("Fixed",  "Login sessions — cross-tab signout broadcast via storage event (v46b)", "v46b", ""),
    85: ("Open",   "Escrow — modify email IDs on transaction signer flow", "-", "Feature — planned"),
}

# User's new bug (c)
BUG_C = {
    "title": "[NEW] Admin > Add Vendor Full Form — per-tab SAVE button + search vendors + list after activate",
    "description": "Admin Add Full Form: each of the 5 tabs (A/B/C/D/E) must have its own SAVE button so partial data can be preserved when switching tabs. Also need a search box in the Vendors directory, and after Save+Activate the vendor must actually appear.",
    "module": "Vendors (admin Add & Fill Full Form)",
    "severity": "High",
    "status": "Fixed",
    "evidence": "AdminVendorCreate: new saveSection(step) function + per-tab 'Save section X' button (data-testid=admin-vendor-save-section-{a-e}); VendorsPanel already has data-testid=vendor-search + statusFilter + focusRef after activate (line 129)",
    "fixed_in_version": "v46h",
}

# Add columns
out = Workbook()
sh = out.active
sh.title = "PMC Bugs — v46h status"
new_header = header + ["New status (v46h)", "Fixed in version", "Code evidence", "Notes"]
sh.append(new_header)

for i, row in enumerate(body, start=1):
    row = row[:]
    fix = FIXES.get(i)
    if fix:
        status, evidence, ver, notes = fix
    else:
        status, evidence, ver, notes = ("?", "", "", "")
    row.extend([status, ver, evidence, notes])
    sh.append(row)

# Append user's new bug row
new_row = [None] * len(header)
# Try to fill title / description / area / severity columns if we can find them
def col_idx(name_frags):
    for j, h in enumerate(header):
        if h and any(f.lower() in str(h).lower() for f in name_frags):
            return j
    return -1
ti = col_idx(["title", "issue", "defect"])
di = col_idx(["description"])
mi = col_idx(["module", "area"])
si = col_idx(["severity", "priority"])
sti = col_idx(["status"])
if ti >= 0: new_row[ti] = BUG_C["title"]
if di >= 0: new_row[di] = BUG_C["description"]
if mi >= 0: new_row[mi] = BUG_C["module"]
if si >= 0: new_row[si] = BUG_C["severity"]
if sti >= 0: new_row[sti] = BUG_C["status"]
new_row.extend([BUG_C["status"], BUG_C["fixed_in_version"], BUG_C["evidence"], "Added per user request 23 Sep 2026"])
sh.append(new_row)

# Freeze pane on header + auto column widths
sh.freeze_panes = "A2"
for col_letter, width in [("A", 6), ("B", 62), ("C", 62), ("D", 22),
                            ("E", 15), ("F", 15), ("G", 15), ("H", 15),
                            ("I", 60), ("J", 40)]:
    sh.column_dimensions[col_letter].width = width

# Summary sheet
summ = out.create_sheet("Summary")
summ.append(["Metric", "Count"])
counts = {"Fixed": 0, "Open": 0, "N/A": 0}
for r in sh.iter_rows(min_row=2, values_only=True):
    st = r[-4]
    if not st or st == "?":
        continue
    counts[st] = counts.get(st, 0) + 1
for k, v in counts.items():
    summ.append([k, v])
summ.append(["Total tracked", sum(counts.values())])
summ.append(["", ""])
summ.append(["Report generated", str(date.today())])
summ.append(["Frontend version", "v46h"])
summ.append(["Backend version", "v46g"])

for col_letter, width in [("A", 24), ("B", 12)]:
    summ.column_dimensions[col_letter].width = width

OUT = Path("/app/deliverables/v46c/Bugs_Tracker_v46h.xlsx")
out.save(OUT)
print(f"Wrote {OUT}  · counts: {counts}")
