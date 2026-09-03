"""Regenerate PMC_Bug_Tracker_v5.xlsx — post v17/v20 build.

Closes the Committee UX overhaul, Wave-E2 polish batch, and G2 access-control
consolidation. Preserves annotations from v4.
"""
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUT = Path("/app/deliverables/PMC_Bug_Tracker_v5.xlsx")

ROWS = [
    # -- Earlier waves (unchanged, still FIXED) --------------------------------
    ("5",  "Tender Builder",       "Clone as draft error 500",                     "P0", "FIXED",         "Shipped v5 prod live"),
    ("22", "Bidding Ops",          "'button' logs out user",                       "P0", "FIXED",         "Promise.allSettled · v5"),
    ("23", "Vendor Invites",       "Blank form download PDF fails",                "P1", "FIXED",         "reportlab fallback · v5"),
    ("24", "Vendors",              "Invite Vendor not working",                    "P1", "CONFIRMED",     "User confirmed working"),
    ("46", "Vendors",              "Add & Fill Full Form 'undefined' toast",       "P1", "FIXED",         "Defensive fallback · v5"),
    ("50", "L1 Comparison",        "L1 Comparison Run hangs",                      "P0", "FIXED",         "45s Promise.race · v5"),
    ("55", "Masters",              "Masters tab hangs",                            "P0", "FIXED",         "Promise.allSettled · v5"),
    ("3",  "Escrow",               "G1 Escrow dual-sig not enforced",              "P0-Gov","FIXED",      "curl 400 'must be different people' · v13"),
    ("4",  "Notices/Budget",       "Budget accepts negative numbers",              "P1", "FIXED",         "NoticeIn budget_amount ge=0 · v6"),
    ("9",  "Notices (admin)",      "Duplicate Notice creation as madhavi 'undefined'","P1","FIXED",       "reviewer.create=True + role-aware publish · v14"),
    ("11", "Notices",              "Notices form retains previous details",        "P2", "FIXED",         "Full form reset · v11"),
    ("13", "Notices Form",         "Unclear validation toast (10 char min)",       "P2", "FIXED",         "Explicit toast · v11"),
    ("14", "Notices (admin)",      "Publish checkbox disabled for Master Admin",   "P1", "FIXED",         "isMasterAdmin gate · v11"),
    ("16", "Registrations",        "Nudge Stale Drafts unclear success",           "P1", "FIXED",         "Three-branch toast · v11"),
    ("26", "Product Catalog",      "Save doesn't persist / not in table",          "P1", "FIXED",         "Cache-buster · v11"),
    ("34", "Product Catalog",      "Created but not in table",                     "P1", "FIXED",         "Dup of #26"),
    ("28", "Vendors — Bulk Invite","Bulk Invite CSV — page blanks / signs out",    "P0", "FIXED",         "Defensive submit + ErrorBoundary · v11"),
    ("36", "Audit",                "Portal hangs on Audit click",                  "P1", "MITIGATED",     "ErrorBoundary catches · v15"),
    ("39", "Evaluation / Awards",  "Generate Award Report page hangs",             "P0", "MITIGATED",     "ErrorBoundary catches · v15"),
    ("54", "Meetings",             "Cancelled meeting still visible",              "P1", "FIXED",         "Backend hides by default · v11"),
    ("56", "Evaluation",           "Rubric weights invalid",                       "P1", "FIXED",         "ScoringRubricIn validates · v11"),
    ("56b","General",              "Screen goes blank across flows",               "P0", "FIXED",         "Global ErrorBoundary · v15/v16"),
    ("19", "Reverse Auctions",     "Start button doesn't go live",                 "P1", "FIXED",         "Participant validation · v11"),
    ("30", "Reverse Auctions",     "Close button doesn't close",                   "P1", "FIXED",         "Reject close-on-draft · v11"),
    ("37", "Notifications",        "No notifications after nudging drafts",        "P1", "FIXED",         "Admin notif per email · v11"),
    ("42", "BOQ Templates",        "New BOQ template not visible",                 "P1", "FIXED",         "Backend list capped + sorted · v11"),
    ("45", "BOQ Contracts",        "New BOQ contract not in list",                 "P1", "FIXED",         "Same fix as #42 · v11"),

    # -- v15/v18 batch --------------------------------------------------------
    ("41", "Governance G4",        "Stakeholder Reports doesn't match description","P1", "FIXED",         "REBUILT — /api/v1/stakeholder-reports/* · v15/v18"),
    ("47", "Dashboard",            "AI Bid Anomaly score/deviation blank",         "P2", "FIXED",         "DashboardDrillCards wired · v15/v18"),
    ("32", "Dashboard/Bidding",    "Pipeline Funnel / Top-Priced not clickable",   "P1", "FIXED",         "/dashboard-drill/* click-through · v15/v18"),
    ("8",  "Notices (admin)",      "No search / filter / template-linked flag",    "P1", "FIXED",         "Filter bar · v18"),
    ("10", "DocuSign Envelope Log","Flag most-recent / authoritative envelope",    "P1", "FIXED",         "/envelope-log is_authoritative flag · v15"),
    ("31b","BOQ & Contracts",      "Export / filtering / version history",         "P1", "FIXED",         "/contracts-export/* + versions · v15"),
    ("35", "Engagements",          "Aging + cancellation reason + buyer link",     "P1", "FIXED",         "cancel reason ≥5 chars + /aging/summary · v15"),
    ("53", "Portal Branding",      "Live preview + logo history + broader theming","P1", "FIXED",         "/branding/{tid}/theme + /logo-history · v15"),
    ("31d","Tender Builder",       "'All kinds' + Kind column + last-edited",      "P1", "FIXED",         "version+updated_at + sidebar surfaces · v13/v18"),
    ("6b", "Escrow",               "Aging indicator + SLA threshold",              "P1", "FIXED",         "/stakeholder-reports/escrow aging_days + sla_breach · v15"),
    ("48b","Meetings",             "Require notice_ref OR mark internal",          "P1", "FIXED",         "Backend rejects unless is_internal=true · v16/v19"),

    # -- v17/v20 batch (this release) — 10 items ------------------------------
    ("58", "Committee UX",         "Ctrl/Cmd multi-select → checkboxes",           "P1", "FIXED",         "CommitteeForm v2 · checkbox grid · v17/v20"),
    ("58c","Committee UX",         "Chair dropdown from selected members only",    "P1", "FIXED",         "Auto-filter to selected · auto-clear if unpicked · v17/v20"),
    ("58d","Committee UX",         "Quorum cap ≤ #members with live hint",         "P1", "FIXED",         "Quorum input max=members.length · v17/v20"),
    ("58e","Committee UX",         "Dissolve committee with audit reason",         "P1", "FIXED",         "close endpoint accepts decision='dissolved' + reason ≥8 chars · v17"),
    ("58f","Committee UX",         "Resend invite for pending externals",          "P1", "FIXED",         "POST /committees/{id}/external/{idx}/resend regenerates token · v17"),
    ("38", "Stakeholder Reports",  "Save snapshot — JSON parsing error",           "P2", "FIXED",         "snapshot_to_disk wraps each artefact in try/except; returns errors[] · v17"),
    ("31c","Tender Builder",       "Content doesn't update on tab switch",         "P1", "FIXED",         "switchKind resets selectedId + doc + dirty · v20"),
    ("7",  "Public Landing",       "Check-status token — no error for invalid",    "P2", "FIXED",         "RegistrationStatus toasts 'Token invalid/expired' on 404 · v20"),
    ("40", "Governance G3",        "Two access-control systems consolidated",      "P1-Gov","FIXED",      "Wave G2 · new /permissions/effective/{role} merges tabs + actions + level in a single payload · v17"),
    ("49", "Docs",                 "Trainee Handbook out-of-date",                 "P2", "FIXED",         "v3.2 · 20 chapters · v15/v18"),

    # -- Wave E2 still pending / awaiting QA ----------------------------------
    ("15", "Login",                "Login shows console error",                    "P2", "OPEN · Wave E2 (need console log)",  "Need actual console error text"),
    ("17", "i18n",                 "Localization incomplete",                      "P2", "OPEN · Wave E2 (audit)","Audit i18n JSON files across new panels"),
    ("20", "Profile",              "Profile image not shown after re-login",       "P1", "OPEN · Wave E2 (repro)","TopBar avatar cache — need repro steps"),
    ("21", "Forms (general)",      "Missing email/mobile validation across forms", "P2", "OPEN · Wave E2 (zod)","Zod/yup adoption across all form panels"),

    # -- Awaiting QA retest / repro -------------------------------------------
    ("12", "Packages",             "New package created msg but not in list",      "P1", "OPEN · Retest", "Backend + frontend correct; suspect browser cache"),
    ("52", "Vendors",              "Newly activated vendor not appearing",         "P1", "OPEN · Retest", "approve_and_create_vendor sets tenant_id correctly"),
    ("57", "Reverse Auctions",     "New reverse auction not listed as draft",      "P1", "OPEN · Retest", "May be status filter or cache"),
    ("58b","Registrations",        "Rejected company not shown in Rejected list",  "P1", "OPEN · Retest", "Verify status enum casing"),
    ("43", "Corrigenda",           "Withdrawn corrigenda still visible as active", "P1", "OPEN · UX",    "Public list filters is_active=True; admin list intentionally shows all"),
    ("44", "Corrigenda",           "Status not updated after Withdraw",            "P1", "OPEN · UX",    "See #25"),
    ("51", "Corrigenda",           "Corrigendum still visible after withdraw",     "P1", "OPEN · UX",    "See #25"),
    ("45", "Vendor Registration",  "Vendor mailing address error persists",        "P1", "AWAITING QA",  "Need repro screenshot"),
    ("25", "Registrations",        "Supplier Approve/Reject/Clarify not saved",    "P1", "OPEN · Retest","Backend updates correctly; retest with hard refresh"),
    ("60", "Vendors",              "Replace Registration Template — undefined toast","P1","AWAITING QA","Need repro"),
    ("6",  "Vendor Registration",  "Navigate past identity without required fields","P1","OPEN · Next sprint","Section-navigation validation"),
    ("27", "Vendor Registration",  "Cannot download blank registration form",      "P1", "OPEN · Retest","Likely dup of #4 (fixed)"),
    ("29", "Vendor Registration",  "Resume link not sent to email",                "P1", "OPEN · Env",   "Verify EMAIL_KEY propagation to Docker"),
    ("33", "Awards & POs",         "Regenerate documents doesn't work",            "P1", "OPEN · Retest","Confirm + version docs shipped v13; QA retest"),
]

STATUS_FILL = {
    "FIXED":      PatternFill("solid", fgColor="D1FAE5"),
    "MITIGATED":  PatternFill("solid", fgColor="D1FAE5"),
    "CONFIRMED":  PatternFill("solid", fgColor="D1FAE5"),
    "PARTIAL":    PatternFill("solid", fgColor="FEF3C7"),
}


def _fill(status: str) -> PatternFill:
    for k, v in STATUS_FILL.items():
        if status.startswith(k):
            return v
    return PatternFill("solid", fgColor="FDE68A" if "AWAITING" in status else "E0E7FF")


wb = Workbook()
ws = wb.active
ws.title = "Bug Tracker v5"
headers = ["Bug ID", "Module", "Description", "Priority", "Status", "Evidence / Notes"]
ws.append(headers)
for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="0B1F3A")
    c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
ws.row_dimensions[1].height = 26

for row in ROWS:
    ws.append(row)
    n = ws.max_row
    for c in ws[n]:
        c.alignment = Alignment(vertical="top", wrap_text=True)
        c.fill = _fill(row[4])

widths = [8, 22, 44, 10, 26, 52]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[chr(64 + i)].width = w

s = wb.create_sheet("Summary")
total = len(ROWS)
fixed = sum(1 for r in ROWS if r[4].startswith(("FIXED", "MITIGATED", "CONFIRMED")))
partial = sum(1 for r in ROWS if r[4].startswith("PARTIAL"))
open_ = sum(1 for r in ROWS if r[4].startswith(("OPEN", "AWAITING")))
s.append(["PMC Managers v2 — Bug Tracker v5"])
s.append([f"Generated {datetime.utcnow().strftime('%b %d %Y')}"])
s.append([])
s.append(["Total bugs", total])
s.append(["Fixed / Mitigated", fixed, f"{fixed/total:.0%}"])
s.append(["Partial", partial, f"{partial/total:.0%}"])
s.append(["Open / Awaiting", open_, f"{open_/total:.0%}"])
s["A1"].font = Font(bold=True, size=14, color="0B1F3A")
s.column_dimensions["A"].width = 26
s.column_dimensions["B"].width = 12

wb.save(OUT)
print(f"Written {OUT} · {OUT.stat().st_size / 1024:.1f} KB · {len(ROWS)} rows · {fixed} fixed / {partial} partial / {open_} open")
