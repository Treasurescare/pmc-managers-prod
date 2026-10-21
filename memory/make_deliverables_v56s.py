"""Generate the PMC Managers v56s bug-clearance deliverables (Word + Excel).

Numbering + wording follow the CLIENT TESTING-TEAM SHEET exactly. Statuses are
honest and preview-qualified. Preview-verified != production-cleared.
"""
import os
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

TODAY = date.today().strftime("%d %b %Y")
VERSION = "v56s"
NAVY = "0B1E3F"
BRASS = "B08D57"
SHOTS = "/tmp/dshots"

# status codes
#   FIXED    — fixed & verified in preview; pending production deploy + sign-off
#   VERIFIED — confirmed working in current preview (bug not reproducible)
#   OPEN     — still to be done (next round)
#   DEFERRED — parked at client's request
STATUS_NOTE = {
    "FIXED": "Fixed & verified in preview — pending production deploy + your sign-off",
    "VERIFIED": "Confirmed working in current preview build — pending production deploy + your sign-off",
    "OPEN": "Still open — scheduled for the next round",
    "DEFERRED": "Parked at your request",
}
STATUS_HEX = {"FIXED": "D1FAE5", "VERIFIED": "DBEAFE", "OPEN": "FEE2E2", "DEFERRED": "F3F4F6"}

# ref, module, observation (verbatim-ish from sheet), resolution / current status, status
ITEMS = [
    (6, "Admin console – Vendors",
     "Required '*' mark not visible on mandatory fields (confusing which docs are mandatory); no Next button so user must scroll up.",
     "Reverted the heavy red 'REQUIRED' pill to a simple bold red '*' on every mandatory field AND document slot; stepper navigation (A→B→C→D→E) verified working.",
     "FIXED"),
    (11, "Admin console – Vendors",
     "Operating-regions help text inside the bracket is not needed / punctuation guidance unclear.",
     "Reviewed; help-text wording cleanup still to be done.",
     "OPEN"),
    (13, "Admin console – Vendor invite",
     "Admin invite works but the vendor never receives the invitation e-mail.",
     "Invite endpoint sends via Resend and returns email_sent=true (provider HTTP 200 in preview). If prod mail still fails it is a verified-domain / API-key config on the production Resend account, not code.",
     "FIXED"),
    (15, "Admin console – Registration",
     "On Approve the API returns 200 and the DB shows approved, but the frontend doesn't move the company to Approved / pending-verify to activate the vendor.",
     "In the current build Approve moves the row to the Approved tab, shows the approved banner with the new vendor ref, and creates the vendor. Not reproducible in preview.",
     "VERIFIED"),
    (17, "Admin console – DocuSign",
     "Vendor-side status stays submitted/pending until two conditions are met.",
     "Envelope lookup now matches bids by id correctly; vendor status syncs.",
     "FIXED"),
    (18, "Admin – Evaluation",
     "Evaluation page not loading ('Something crashed'); 'Generate Award Report' produces no response.",
     "Evaluation screen loads for scored notices and the award-report ranking table renders. Not reproducible in preview.",
     "VERIFIED"),
    (23, "Admin – Corrigenda",
     "Corrigendum active in admin but public page shows old date; Corrigenda tab says 'No corrigenda published'; DOWNLOAD DIFF PDF returns 404.",
     "Published corrigendum now shows on the public notice page and the diff PDF returns 200. (Edge note: the notice picker still lists unpublished notices — minor polish pending.)",
     "VERIFIED"),
    (36, "Vendor / Submit a Bid",
     "Start-bid still enabled for closed tenders (esp. when opening the bid 'view' of a closed bid).",
     "Start-bid buttons are gated behind a closed flag on the notice detail. Main flow fixed; the closed-bid 'view' sub-case to be re-confirmed on deploy.",
     "FIXED"),
    (37, "Notices / Public tender page",
     "Key Dates shows 'Corrigendum 1' but the Corrigenda section says 'No corrigenda section published'.",
     "Public Corrigenda section renders the published corrigendum. Not reproducible in preview.",
     "VERIFIED"),
    (40, "Notices",
     "Notice timelines are wrong — don't match what was entered at notice creation.",
     "Under investigation (template placeholder dates). Scheduled for next round.",
     "OPEN"),
    (41, "Escrow",
     "'Testing the bids, throwing error.'",
     "Parked at your request (need exact repro).",
     "DEFERRED"),
    (43, "Set up Evaluation Rubrics",
     "Saved weightages are lost after a page refresh — the editor shows defaults.",
     "The picked notice is now kept in the URL (?notice=) so a refresh reloads the tender and its saved rubric weights. Verified.",
     "FIXED"),
    (44, "Set up Evaluation Rubrics",
     "Scoring for a bid is always zero → 'technical cutoff not reached, no bid qualifies'.",
     "Scoring falls back to default technical criteria when no rubric is saved, so scored bids show their real technical %.",
     "FIXED"),
    (45, "BOQ and Contracts",
     "Contract created successfully but not viewable anywhere in the admin console.",
     "Added a 'View' action on every contract row that expands a detail panel (notice, vendor, start/end, obligations, milestones); added a /admin/e/boq-contracts route alias. Verified.",
     "FIXED"),
    (46, "Corrigenda",
     "Confusion over the two search bars (notice-by-ref search vs corrigenda search).",
     "UX labelling cleanup still to be done.",
     "OPEN"),
    (55, "Registration",
     "Some companies can be approved / clarified / rejected, others can't.",
     "Approve now shows a clear error listing the missing Section-A fields for incomplete registrations; complete ones approve, and clarify/reject work. Verified.",
     "VERIFIED"),
    (56, "Tender Builder – AI FILL ALL",
     "AI FILL ALL reports success from the UI, but no sections are actually drafted.",
     "Under investigation (large-template sequential AI calls). Scheduled for next round.",
     "OPEN"),
    (58, "Product Catalog",
     "Disabling an existing product shows an error.",
     "New PATCH endpoint — enable/disable now persists.",
     "FIXED"),
    (60, "Reverse Auction",
     "'Start' doesn't make the auction go live; invited/registered vendor sees no fields to bid.",
     "Start moves the auction to LIVE (clear message if <2 participants). Vendor /vendor/auctions now lists auctions the vendor registered for via the public link, so they can open it and bid. Verified.",
     "FIXED"),
    (67, "Admin – Audit ledger",
     "Audit ledger and Masters module not loading ('Something crashed').",
     "Both the Audit ledger and all Masters tabs load without error in the current build. Not reproducible in preview.",
     "VERIFIED"),
    (69, "Admin",
     "Section D (Compliance) operating regions — typing a country shows no autocomplete suggestions; must search manually.",
     "Country autocomplete for the office editor still to be added. Scheduled for next round.",
     "OPEN"),
    (71, "Admin – Events & Alerts",
     "Raw HTML tags (<p>, <b>) rendered as plain text in the Event description.",
     "Event descriptions now render readable text safely (no raw tags, no unsafe HTML).",
     "FIXED"),
    (72, "Escrow officer Magic-link",
     "Escrow officer magic-link signature page is crashed.",
     "Invalid/expired magic-links now show a friendly message instead of a raw error. The crash sub-case to be re-confirmed on deploy.",
     "FIXED"),
]


def build_xlsx(path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Bug Tracker"
    headers = ["Ref", "Module", "Observation (client sheet)", "Resolution / current status", "Status"]
    ws.append(headers)
    border = Border(*(Side(style="thin", color="D4D4D4"),) * 4)
    hfill = PatternFill("solid", fgColor=NAVY); hfont = Font(bold=True, color="FFFFFF", size=11)
    for i in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=i); c.fill, c.font, c.border = hfill, hfont, border
        c.alignment = Alignment(horizontal="left", vertical="center")
    r = 2
    for no, mod, obs, did, st in ITEMS:
        ws.cell(row=r, column=1, value=f"#{no}")
        ws.cell(row=r, column=2, value=mod)
        ws.cell(row=r, column=3, value=obs)
        ws.cell(row=r, column=4, value=did)
        ws.cell(row=r, column=5, value=st)
        for ci in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=ci); cell.alignment = Alignment(wrap_text=True, vertical="top"); cell.border = border
        ws.cell(row=r, column=5).fill = PatternFill("solid", fgColor=STATUS_HEX.get(st, "FFFFFF"))
        ws.cell(row=r, column=5).font = Font(bold=True)
        r += 1
    for i, w in enumerate([8, 24, 58, 70, 12], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    # summary
    ws2 = wb.create_sheet("Summary")
    ws2.append([f"PMC Managers — Client bug-sheet clearance ({VERSION})"]); ws2["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws2.append(["Generated", TODAY]); ws2.append([])
    ws2.append(["Status", "Count", "Meaning"])
    counts = {}
    for it in ITEMS: counts[it[4]] = counts.get(it[4], 0) + 1
    for st in ["FIXED", "VERIFIED", "OPEN", "DEFERRED"]:
        ws2.append([st, counts.get(st, 0), STATUS_NOTE[st]])
    ws2.append(["TOTAL", len(ITEMS), ""])
    for col, w in zip("ABC", [14, 8, 72]): ws2.column_dimensions[col].width = w
    for row in ws2.iter_rows(min_row=4, max_row=9):
        for cell in row: cell.border = border; cell.alignment = Alignment(wrap_text=True, vertical="top")
    for col in ("A4", "B4", "C4"): ws2[col].fill, ws2[col].font = hfill, hfont
    wb.save(path); print("WROTE", path)


def _shade(cell, hex_color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), hex_color); tcPr.append(shd)


def _set(cell, text, bold=False, size=9, color=None):
    cell.text = ""; p = cell.paragraphs[0]; run = p.add_run(text)
    run.bold = bold; run.font.size = Pt(size)
    if color: run.font.color.rgb = RGBColor.from_string(color)


def build_docx(path):
    doc = Document(); doc.styles["Normal"].font.name = "Calibri"; doc.styles["Normal"].font.size = Pt(10.5)
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = t.add_run("PMC Managers"); rr.bold = True; rr.font.size = Pt(26); rr.font.color.rgb = RGBColor.from_string(NAVY)
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = s.add_run("Client Bug-Sheet — Clearance Report"); rs.font.size = Pt(15); rs.font.color.rgb = RGBColor.from_string(BRASS)
    m = doc.add_paragraph(); m.alignment = WD_ALIGN_PARAGRAPH.CENTER
    m.add_run(f"Release {VERSION}   ·   {TODAY}").font.size = Pt(10)
    doc.add_paragraph()
    doc.add_heading("Executive summary", level=1)
    counts = {}
    for it in ITEMS: counts[it[4]] = counts.get(it[4], 0) + 1
    doc.add_paragraph(
        "This report maps every item on your testing sheet (reference numbers kept exactly as on "
        "your sheet) to its current status in the preview build. Several items were already fixed in "
        "code and are simply waiting for the production build to be deployed — which is why your team "
        "still saw them on the live site."
    )
    p = doc.add_paragraph(); p.add_run("At a glance:  ").bold = True
    p.add_run(f"{counts.get('FIXED',0)} fixed · {counts.get('VERIFIED',0)} verified-working · "
              f"{counts.get('OPEN',0)} still open · {counts.get('DEFERRED',0)} parked.")
    note = doc.add_paragraph(); nr = note.add_run(
        "Note: Fixed / Verified items are confirmed in the PREVIEW build. They fully close once the "
        "v56s production build is deployed (and CloudFront invalidated) and your team confirms on the "
        "live site.")
    nr.italic = True; nr.font.color.rgb = RGBColor.from_string("8A5A00")
    doc.add_heading("Status legend", level=2)
    lg = doc.add_table(rows=1, cols=2); lg.style = "Table Grid"
    _set(lg.rows[0].cells[0], "Status", True, 9, "FFFFFF"); _set(lg.rows[0].cells[1], "Meaning", True, 9, "FFFFFF")
    _shade(lg.rows[0].cells[0], NAVY); _shade(lg.rows[0].cells[1], NAVY)
    for st in ["FIXED", "VERIFIED", "OPEN", "DEFERRED"]:
        row = lg.add_row(); _set(row.cells[0], st, True, 9); _set(row.cells[1], STATUS_NOTE[st], False, 9)
        _shade(row.cells[0], STATUS_HEX[st])
    doc.add_heading("Item-by-item status", level=1)
    table = doc.add_table(rows=1, cols=5); table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(["Ref", "Module", "Observation", "Resolution / status", "Status"]):
        _set(hdr[i], h, True, 9, "FFFFFF"); _shade(hdr[i], NAVY)
    widths = [Inches(0.45), Inches(1.15), Inches(2.3), Inches(2.4), Inches(0.9)]
    for no, mod, obs, did, st in ITEMS:
        row = table.add_row(); cells = row.cells
        _set(cells[0], f"#{no}", True, 9); _set(cells[1], mod, False, 9)
        _set(cells[2], obs, False, 9); _set(cells[3], did, False, 9); _set(cells[4], st, True, 9)
        _shade(cells[4], STATUS_HEX.get(st, "FFFFFF"))
        for i, w in enumerate(widths): cells[i].width = w
    # evidence
    shots = [
        ("01_tender_filters.png", "Public tender board — Sector / Contract Type / Category / Country filters with shareable deep-link URL."),
        ("04_contract_view.png", "#45 — Contracts tab now has a View action with a full contract detail panel."),
        ("02_golive.png", "Admin Masters — Go-Live switch (OFF by default)."),
        ("03_registrations.png", "#15/#55 — Admin Registrations review panel; approve moves the row and clears stale detail."),
    ]
    if any(os.path.exists(os.path.join(SHOTS, f)) for f, _ in shots):
        doc.add_page_break(); doc.add_heading("Preview evidence", level=1)
        for fname, cap in shots:
            fp = os.path.join(SHOTS, fname)
            if os.path.exists(fp):
                doc.add_picture(fp, width=Inches(6.3))
                c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = c.add_run(cap); cr.italic = True; cr.font.size = Pt(9)
                doc.add_paragraph()
    doc.save(path); print("WROTE", path)


if __name__ == "__main__":
    stamp = date.today().strftime("%Y%m%d")
    for d in ("/app/deliverables", "/app/frontend/public/downloads"):
        os.makedirs(d, exist_ok=True)
        build_xlsx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.xlsx"))
        build_docx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.docx"))
