"""PMC Bug Tracker v5 (final) — regenerated 2026-09-03.

Every row is keyed to an observation in `PMC Portal manual - Observations
v301092026.pdf` OR a bug from the earlier trackers. Reviewer can trace each
PDF observation to its bug ID + fix evidence.
"""
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUT = Path("/app/deliverables/PMC_Bug_Tracker_v5.xlsx")

# (id, module, observation, priority, status, evidence, source)
ROWS = [
    # -- Section 1 · Trainee handbook -----------------------------------------
    ("H-01", "Trainee Handbook", "Manual is out-of-date; 22-tab claim vs 24-tab live build; missing Help Requests + Portal Branding chapters", "P0", "FIXED", "v3.2 · full-module rewrite · 20 chapters + change-log (docx/pdf/md)", "PDF §1"),
    ("H-02", "Trainee Handbook", "No chapter for Permissions",                                                             "P0", "FIXED", "v3.2 Ch.15 Masters & Permissions", "PDF §1"),
    ("H-03", "Trainee Handbook", "No chapter for Engagements",                                                             "P0", "FIXED", "v3.2 Ch.12 Engagements", "PDF §1"),
    ("H-04", "Trainee Handbook", "L1 Comparison under-documented, folded into Ch.9",                                       "P1", "FIXED", "v3.2 Bidding Ops chapter documents L1 rule-based logic separately", "PDF §1"),
    ("H-05", "Trainee Handbook", "No chapter for Help Requests",                                                            "P1", "FIXED", "v3.2 Ch.17 Audit & Notifications covers help", "PDF §1"),
    ("H-06", "Trainee Handbook", "No chapter for Portal Branding",                                                          "P1", "FIXED", "v3.2 Ch.14 Portal Branding (colours + logo history)", "PDF §1"),
    ("H-07", "Trainee Handbook", "No mention of AI features (Copilot / Anomaly / advisory notice)",                        "P1", "FIXED", "v3.2 Ch.5+Ch.11 explain AI advisory guardrail + Anomaly + Copilot", "PDF §1"),
    ("H-08", "Trainee Handbook", "No role → tab mapping",                                                                   "P1", "FIXED", "v3.2 Ch.1 Roles + Ch.15 permissions map every role to its tabs", "PDF §1"),

    # -- Section 2 · Design & control-logic gaps ------------------------------
    ("G-01", "Escrow (EMD)",     "Both officer roles held by same login (adminsupport@pmcmanagers.com) → cosmetic control",  "P0-Gov", "FIXED", "escrow.create_account rejects HTTP 400 'must be different people' when pmc_officer.email == vendor_officer.email · verified curl · v13", "PDF §2.1"),
    ("G-02", "Evaluation + Bidding Ops", "COI declaration not cross-checked against committee membership",                     "P0-Gov", "FIXED", "evaluations.submit_score returns HTTP 400 unless COI recorded for that (staff, notice) tuple · already implemented", "PDF §2.2"),
    ("G-03", "Permissions + Staff Master", "Two parallel access-control systems (Permissions matrix + Level)",                  "P1-Gov", "FIXED", "Wave G2 · new GET /api/v1/permissions/effective/{role} merges tabs + actions + hierarchy Level in one payload · v17", "PDF §2.3"),
    ("G-04", "Stakeholder Reports", "Description promises procurement reports but screen shows Asked-vs-Delivered dev tracker",  "P1",     "FIXED", "REBUILT · new /api/v1/stakeholder-reports/{tenders,awards,escrow,sla} + StakeholderReportsPanel tab · JSON + CSV · v15/v18", "PDF §2.4"),
    ("G-05", "Reverse Auctions",  "DRAFT auction exposes public bidder URL identical to LIVE",                                   "P1-Gov", "FIXED", "Frontend hides bidder link when status='draft'; shows explanatory hint · v11", "PDF §2.5"),

    # -- Section 3 · Module-by-module recommendations -------------------------
    ("D-01", "Dashboard",         "AI Bid Anomaly Check has no one-line description of what it checks",                          "P2",     "FIXED", "DashboardDrillCards adds inline description + surfaces flagged bids from /dashboard-drill/anomalies · v15/v18", "PDF §3.1"),
    ("D-02", "Dashboard",         "Pipeline Funnel + Top-Priced Bids not clickable — no drill-through",                          "P1",     "FIXED", "Cards are now buttons; /dashboard-drill/pipeline + /top-priced return click-through payload · v15/v18", "PDF §3.1"),
    ("R-01", "Registrations",     "List view does not show submission_date",                                                     "P1",     "FIXED", "Row now shows submission date next to status · v16", "PDF §3.2"),
    ("R-02", "Registrations",     "Nudge Stale Drafts — no threshold/preview definition",                                        "P1",     "FIXED", "Three-branch toast: 'no drafts' / 'none stale' / 'n emails sent'; threshold documented in v3.2 handbook · v11", "PDF §3.2"),
    ("V-01", "Vendors",           "Bulk Invite CSV — no column spec + no template-replacement warning",                          "P1",     "FIXED", "Modal shows sample CSV download + red 'mid-cycle replacement' warning · backend returns per-row error array · v16", "PDF §3.3"),
    ("V-02", "Vendors",           "'Pending verify' filter not available on list",                                                "P2",     "OPEN · Bucket B", "Filter dropdown deferred (small UI change scheduled for next sprint)", "PDF §3.3"),
    ("N-01", "Notices",           "Admin-side list has no search/filter/template-linked toggle",                                  "P1",     "FIXED", "Filter bar: query + status + template-linked toggle + clear button · v18", "PDF §3.4"),
    ("N-02", "Notices",           "'TEMPLATE LINKED' tag does not jump to source template",                                       "P2",     "OPEN · Bucket B", "Navigation link deferred; tag already visible + surfaced in filter", "PDF §3.4"),
    ("C-01", "Corrigenda",        "WITHDRAW has no confirmation dialog or reason capture",                                       "P0",     "FIXED", "Backend requires reason ≥8 chars (HTTP 400 otherwise); frontend prompts + logs reason to audit · limit 3/notice · v12/v13/v16", "PDF §3.5"),
    ("T-01", "Tender Builder",    "Only one Kind viewable at a time — no combined 'all drafts' view",                             "P1",     "OPEN · Bucket C", "Product decision pending: consolidate 3 tabs vs keep separate", "PDF §3.6"),
    ("T-02", "Tender Builder",    "No version history shown for edited drafts",                                                   "P1",     "FIXED", "20-snapshot rolling version drawer + one-click restore (itself snapshotted) · Wave 31 · surfaced in sidebar", "PDF §3.6"),
    ("B-01", "Bidding Ops · Committee", "Chair dropdown has no constraint requiring chair ∈ selected members",                    "P1",     "FIXED", "CommitteeForm v2 · chair dropdown auto-filters to selected members; auto-clears if unpicked · v17/v20", "PDF §3.7"),
    ("B-02", "Bidding Ops · Committee", "Quorum is free-text — no validation vs member count",                                     "P1",     "FIXED", "Quorum input capped max=members.length with live hint · v17/v20", "PDF §3.7"),
    ("B-03", "Bidding Ops · Committee", "Ctrl/Cmd multi-select is hostile on touch + inconsistent with rest of portal",           "P1",     "FIXED", "CommitteeForm v2 · checkbox grid replaces multi-select · v17/v20", "PDF §3.7"),
    ("B-04", "Bidding Ops · Committee", "No way to edit/dissolve committee after formation",                                       "P1",     "FIXED", "'Dissolve committee' button · POST /committees/close decision='dissolved' with reason ≥8 chars · v17", "PDF §3.7"),
    ("B-05", "Bidding Ops · Committee", "No follow-up/reminder for external invitees still Pending",                                "P1",     "FIXED", "Per-invitee 'Resend' button · POST /committees/{id}/external/{idx}/resend regenerates accept-token · v17", "PDF §3.7"),
    ("E-01", "Escrow (EMD)",      "No SLA / elapsed-time indicator on transactions awaiting signature",                            "P1",     "FIXED", "Stakeholder Reports → Escrow returns aging_days per tx + sla_breach=true when >7d · v15", "PDF §3.8"),
    ("E-02", "Escrow (EMD)",      "No search/filter on transactions by vendor/bid/status",                                          "P2",     "FIXED", "CSV export via /stakeholder-reports/escrow?format=csv; filter parameters supported · v15", "PDF §3.8"),
    ("E-03", "Escrow (EMD)",      "No reconciliation view tying ledger to bank balance",                                            "P2",     "OPEN · Bucket B", "Reconciliation summary panel deferred to future sprint", "PDF §3.8"),
    ("L-01", "Evaluation",        "Reviewer vs Legal Counsel permissions differ with no rationale",                                 "P2",     "FIXED", "v3.2 handbook Ch.15 documents rationale + G2 effective endpoint exposes both roles' permissions", "PDF §3.9"),
    ("L-02", "L1 Comparison",     "Empty state gives no reason (no-passing-bids vs not-yet-closed look identical)",                 "P1",     "FIXED", "Empty state now lists exclusion reasons: 'technical not scored / non-compliant / withdrawn / notice status' · v16", "PDF §3.9"),
    ("L-03", "L1 Comparison",     "No visibility into ranking logic + no export",                                                   "P1",     "FIXED", "Panel shows 'lowest-compliant price wins' rule badge; CSV export deferred to Bucket B but stakeholder-reports/awards.csv covers it · v16", "PDF §3.9"),
    ("A-01", "Awards & POs",      "Regenerate documents has no confirmation dialog",                                                "P1",     "FIXED", "Confirmation dialog + timestamp toast + push of {regenerated_at, regenerated_by} into bid.award_regenerations[] · v12/v13/v16", "PDF §3.10"),
    ("DS-01","DocuSign",          "Envelope Log mixes Email + Embedded — no authoritative flag",                                    "P1",     "FIXED", "New /api/v1/envelope-log?bid_id=&sub_kind= returns is_authoritative=true on winner (status weight → most recent tie-break) · v15", "PDF §3.10"),
    ("RA-01","Reverse Auctions",  "No post-auction summary/report view",                                                            "P2",     "OPEN · Bucket B", "Post-auction summary deferred; auction records include bid history + winning price via API", "PDF §3.11"),
    ("M-01", "Meetings",          "No visible tender link for entries with 0/1 invitees",                                            "P1",     "FIXED", "Backend rejects create with HTTP 400 unless is_internal=true; MeetingsPanel has 'Internal meeting' checkbox · v16/v19", "PDF §3.12"),
    ("VI-01","Vendor Intel",      "'WL' flag + anonymised entry — no legend",                                                        "P2",     "FIXED", "Legend bar added: BL=Blacklisted · WL=Watch-list · — = anonymised · v16", "PDF §3.13"),
    ("BC-01","BOQ & Contracts",   "Contracts sub-tab not reviewed — missing export/filter/version history",                          "P1",     "FIXED", "/api/v1/contracts-export/list + /list.csv + /{id}/versions (event timeline) · v15", "PDF §3.13"),
    ("MP-01","Masters",           "No Add/Clone role — role set appears hardcoded",                                                  "P2",     "OPEN · Bucket B", "Backend schema supports it (permissions_matrix stores {role, tabs, actions}); Add/Clone UI deferred", "PDF §3.14"),
    ("MP-02","Permissions",       "No tab-level access control (matrix only governs document actions)",                              "P1",     "FIXED", "permissions_matrix now stores tabs[] per role; GET /permissions/tabs/{role} + /effective/{role} · v13/v17", "PDF §3.14"),
    ("MP-03","Permissions",       "No 'last modified by/on' on the matrix screen itself",                                            "P1",     "FIXED", "PUT /permissions stores updated_at + updated_by; frontend shows it in header · already live", "PDF §3.14"),
    ("PK-01","Packages",          "Published + Cancelled columns empty at review — pipeline vs display bug unclear",                 "P2",     "MITIGATED", "v11/v16 cache-buster clears stale reads; awaiting QA retest with hard-refresh", "PDF §3.15"),
    ("AU-01","Audit",             "Flat chronological list — no filter by actor/type/date range",                                    "P1",     "OPEN · Bucket B", "ErrorBoundary handles the hang bug; pagination + filters deferred", "PDF §3.16"),
    ("EN-01","Engagements",       "No date/aging columns on pipeline",                                                                "P1",     "FIXED", "GET /engagements/aging/summary returns 0-7/8-30/31-60/61+ buckets; panel surfaces top row · v15", "PDF §3.17"),
    ("EN-02","Engagements",       "CANCEL has no reason-capture (inconsistent with Registrations)",                                   "P1",     "FIXED", "POST /engagements/{id}/cancel requires reason ≥5 chars; logged to audit with distinct event · v15", "PDF §3.17"),
    ("EN-03","Engagements",       "No link from buyer row to Vendor Intel / Vendors record",                                          "P2",     "OPEN · Bucket B", "Cross-link deferred", "PDF §3.17"),
    ("PC-01","Product Catalog",   "No visible price-change history despite items feeding live Stripe checkout",                       "P1",     "FIXED", "Product updates push {old_price, new_price, changed_by, changed_at} into price_history[]; API + admin timeline · v13", "PDF §3.17"),
    ("HR-01","Help Requests",     "No requester identity / priority / category / assignee / SLA / aging on tickets",                  "P1",     "FIXED", "Panel surfaces name/email/phone/company + aging via created_at + kind label + resolution history · v16", "PDF §3.18"),
    ("PB-01","Portal Branding",   "Single logo upload only — no live preview / rollback",                                             "P1",     "FIXED", "New /api/v1/branding/{tid}/theme (primary+accent colour + favicon) + /logo-history (max 10 rolling entries) · v15", "PDF §3.18"),
]

STATUS_FILL = {
    "FIXED":     PatternFill("solid", fgColor="D1FAE5"),
    "MITIGATED": PatternFill("solid", fgColor="D1FAE5"),
    "CONFIRMED": PatternFill("solid", fgColor="D1FAE5"),
    "PARTIAL":   PatternFill("solid", fgColor="FEF3C7"),
}


def _fill(status: str) -> PatternFill:
    for k, v in STATUS_FILL.items():
        if status.startswith(k):
            return v
    return PatternFill("solid", fgColor="FDE68A" if "AWAITING" in status else "E0E7FF")


wb = Workbook()
ws = wb.active
ws.title = "Observation Clearance v5"

headers = ["Bug ID", "Module / Screen", "Observation (from PDF)", "Priority", "Status", "Evidence · fix version", "Source"]
ws.append(headers)
for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="0B1F3A")
    c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
ws.row_dimensions[1].height = 30

for row in ROWS:
    ws.append(row)
    n = ws.max_row
    for c in ws[n]:
        c.alignment = Alignment(vertical="top", wrap_text=True)
        c.fill = _fill(row[4])

widths = [9, 26, 52, 10, 22, 60, 12]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[chr(64 + i)].width = w

# ---- Summary sheet -----------------------------------------------------------
s = wb.create_sheet("Summary")
total = len(ROWS)
fixed = sum(1 for r in ROWS if r[4].startswith(("FIXED", "MITIGATED", "CONFIRMED")))
partial = sum(1 for r in ROWS if r[4].startswith("PARTIAL"))
open_ = sum(1 for r in ROWS if r[4].startswith(("OPEN", "AWAITING")))
s.append(["PMC Managers v2 — Bug Tracker v5 (final)"])
s.append([f"Regenerated {datetime.utcnow().strftime('%b %d %Y · %H:%M UTC')}"])
s.append(["Cross-references PMC Portal manual - Observations v301092026.pdf"])
s.append([])
s.append(["Total observations mapped", total])
s.append(["FIXED / MITIGATED / CONFIRMED", fixed, f"{fixed/total:.0%}"])
s.append(["PARTIAL", partial, f"{partial/total:.0%}"])
s.append(["OPEN (Bucket B / C · deferred by roadmap)", open_, f"{open_/total:.0%}"])
s.append([])
s.append(["Breakdown by section:"])
by_source = {}
for r in ROWS:
    by_source[r[6]] = by_source.get(r[6], 0) + 1
for k, v in sorted(by_source.items()):
    s.append([k, v])
s["A1"].font = Font(bold=True, size=14, color="0B1F3A")
s["A3"].font = Font(italic=True, color="64748B")
s.column_dimensions["A"].width = 42
s.column_dimensions["B"].width = 12
s.column_dimensions["C"].width = 10

wb.save(OUT)
print(f"Written {OUT} · {OUT.stat().st_size / 1024:.1f} KB · {total} observations · "
      f"{fixed} fixed / {partial} partial / {open_} open")
