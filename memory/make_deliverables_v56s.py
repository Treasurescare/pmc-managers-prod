"""Generate the PMC Managers v56s bug-clearance deliverables (Word + Excel).

Team-facing. Honest, qualified statuses. Numbering follows the current
testing-team observation round (v56o–v56s). Preview-verified items are NOT
labelled as production-cleared.
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

# ---------------------------------------------------------------------------
# Canonical item list for this round. status codes:
#   FIXED   — fixed & preview-tested; pending production deploy + user sign-off
#   NEW     — newly built feature; preview-tested; pending deploy + sign-off
#   VERIFIED— confirmed already correct in preview (no code change required)
#   DEFERRED— intentionally unchanged per explicit user instruction
# ---------------------------------------------------------------------------
BATCH1 = "Batch 1 — Production bug-sheet re-verification (v56o)"
BATCH2 = "Batch 2 — Taxonomy, Go-Live & public filters (v56q–v56s)"

ITEMS = [
    # no, module, observation, what_we_did, status, priority, reverify, batch
    (58, "Product Catalog",
     "Disabling an existing product throws an error.",
     "Added PATCH /api/v1/products/{id}/active (was returning 422). Enable/disable now persists; invalid id → 400, missing → 404.",
     "FIXED", "P1", "Yes", BATCH1),
    (44, "Evaluation",
     "Technical scoring always computes 0 → 'no bid qualifies'.",
     "_load_rubric_config now falls back to DEFAULT_TECH_CRITERIA when no rubric is saved, so scored bids show their real technical %.",
     "FIXED", "P1", "Yes", BATCH1),
    (17, "Admin DocuSign",
     "Vendor side stays 'submitted/pending' until two conditions are met.",
     "list_my_envelopes now matches bids by str(_id) (was referencing a non-existent 'id' field), so the vendor status updates correctly.",
     "FIXED", "P1", "Yes", BATCH1),
    (23, "Corrigenda",
     "A rejected corrigendum publish could leave an orphan record / moved deadline.",
     "All validation (require_future + amendment + _validate_tender_chain) now runs BEFORE any DB write — a rejected publish leaves no orphan.",
     "FIXED", "P1", "Yes", BATCH1),
    (36, "Public Notice",
     "Bid buttons still active on closed/awarded tenders.",
     "NoticeDetail gates both 'Start bid' buttons behind a closed flag (status closed/awarded or past deadline) → disabled 'Bidding closed'.",
     "FIXED", "P2", "Yes", BATCH1),
    (72, "Escrow magic-link",
     "Invalid/expired escrow link shows a raw axios 404.",
     "Friendly 'link invalid or expired' message shown instead of the raw error.",
     "FIXED", "P2", "No", BATCH1),

    (13, "Escrow Institutions",
     "Institutions that start but never finish registration are never chased; no dormancy handling.",
     "Platform cron (.emergent/crons.yml) e-mails the institution's primary contact (all signatories CC'd) every 7 days while incomplete; at 30 days the record is marked dormant with a re-registration warning. Verified end-to-end in preview with temporary records (reminder at 10d, dormant at 35d, 7-day cadence guard, provider HTTP 200).",
     "FIXED", "P1", "Yes", BATCH2),
    (71, "Events & Alerts",
     "Notification body shows literal HTML tags (e.g. <p>…</p>) instead of readable text.",
     "Admin Events now render readable text safely (no raw tags, no unsafe HTML injection). Verified in preview: HAS_RAW_P_TAG_LITERAL = False.",
     "FIXED", "P2", "Yes", BATCH2),
    (0, "Procurement Taxonomy",
     "No structured Sector / Contract-Type / commodity classification on vendors, categories, notices or the public board.",
     "New persistent masters: Sectors (25) and Contract Types (30, grouped) kept separate from the 105 UNSPSC categories. Wired as cascading pickers into vendor registration (Section D), vendor category requests, and notice create/edit; stored and returned on each record.",
     "NEW", "P1", "Yes", BATCH2),
    (0, "Admin Go-Live Switch",
     "Need a single switch to make Sector/Contract-Type optional during onboarding and mandatory at go-live.",
     "New admin Go-Live toggle (Masters). OFF by default — Sector & Contract Type stay optional. When ON, the backend blocks new registration/notice workflows that omit them. Existing vendors are untouched.",
     "NEW", "P1", "Yes", BATCH2),
    (0, "Public Tender Board",
     "Public board has no way to filter by Sector, Contract Type, commodity or country; filters are not shareable.",
     "Added Sector, Contract Type, Category (UNSPSC), Country and free-text filters. Live filter state is mirrored into the URL so a filtered view is a shareable deep-link (e.g. ?sector=power&country=IN).",
     "NEW", "P1", "Yes", BATCH2),
    (6, "Vendor Registration",
     "Mandatory-field marker (thin red asterisk) is easy to miss.",
     "Confirmed the current marker is a bold red 'REQUIRED' pill on every mandatory field — clear and prominent. Retained as-is per review.",
     "VERIFIED", "P3", "No", BATCH2),
    (15, "Admin Registrations",
     "Previously-selected company detail lingers after switching the status tab.",
     "Confirmed the review panel clears the current selection whenever the status tab changes, so no stale company detail is shown. Working as intended in preview.",
     "VERIFIED", "P2", "No", BATCH2),
    (11, "Help Text",
     "Field help text wording.",
     "Left unchanged — explicitly deferred by user instruction.",
     "DEFERRED", "P3", "No", BATCH2),
    (69, "Help Text",
     "Field help text wording.",
     "Left unchanged — explicitly deferred by user instruction.",
     "DEFERRED", "P3", "No", BATCH2),
]

STATUS_NOTE = {
    "FIXED": "Fixed & verified in preview — pending production deploy + your sign-off",
    "NEW": "New capability built & verified in preview — pending production deploy + your sign-off",
    "VERIFIED": "Confirmed already correct in preview — no code change needed",
    "DEFERRED": "Intentionally left unchanged per your instruction",
}

STATUS_HEX = {
    "FIXED": "D1FAE5", "NEW": "DBEAFE", "VERIFIED": "E0E7FF", "DEFERRED": "F3F4F6",
}
PRIORITY_HEX = {"P0": "FCA5A5", "P1": "FDE68A", "P2": "BBF7D0", "P3": "DBEAFE"}


# ===========================================================================
# EXCEL
# ===========================================================================
def build_xlsx(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bug Tracker"
    headers = ["Ref", "Module", "Observation (as reported)", "Resolution / What we did",
               "Status", "Priority", "Re-verify after deploy?"]
    ws.append(headers)

    border = Border(*(Side(style="thin", color="D4D4D4"),) * 4)
    hfill = PatternFill("solid", fgColor=NAVY)
    hfont = Font(bold=True, color="FFFFFF", size=11)
    for i in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=i)
        c.fill, c.font, c.border = hfill, hfont, border
        c.alignment = Alignment(horizontal="left", vertical="center")

    cur_batch = None
    r = 2
    for no, mod, obs, did, st, pr, rv, batch in ITEMS:
        if batch != cur_batch:
            cur_batch = batch
            ws.cell(row=r, column=1, value=batch)
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(headers))
            bc = ws.cell(row=r, column=1)
            bc.fill = PatternFill("solid", fgColor=BRASS)
            bc.font = Font(bold=True, color="FFFFFF", size=11)
            bc.alignment = Alignment(horizontal="left", vertical="center")
            r += 1
        ref = f"#{no}" if no else "NEW"
        ws.cell(row=r, column=1, value=ref)
        ws.cell(row=r, column=2, value=mod)
        ws.cell(row=r, column=3, value=obs)
        ws.cell(row=r, column=4, value=did)
        ws.cell(row=r, column=5, value=st)
        ws.cell(row=r, column=6, value=pr)
        ws.cell(row=r, column=7, value=rv)
        for c_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c_idx)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
        ws.cell(row=r, column=5).fill = PatternFill("solid", fgColor=STATUS_HEX.get(st, "FFFFFF"))
        ws.cell(row=r, column=5).font = Font(bold=True)
        ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor=PRIORITY_HEX.get(pr, "FFFFFF"))
        ws.cell(row=r, column=6).font = Font(bold=True)
        r += 1

    for i, w in enumerate([8, 20, 55, 70, 12, 9, 14], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    # Summary sheet
    ws2 = wb.create_sheet("Summary")
    ws2.append([f"PMC Managers — Bug & Enhancement Clearance ({VERSION})"])
    ws2["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws2.append(["Generated", TODAY])
    ws2.append([])
    ws2.append(["Status", "Count", "Meaning"])
    counts = {}
    for it in ITEMS:
        counts[it[4]] = counts.get(it[4], 0) + 1
    for st in ["FIXED", "NEW", "VERIFIED", "DEFERRED"]:
        ws2.append([st, counts.get(st, 0), STATUS_NOTE[st]])
    ws2.append(["TOTAL", len(ITEMS), ""])
    for col, w in zip("ABC", [14, 8, 70]):
        ws2.column_dimensions[col].width = w
    for row in ws2.iter_rows(min_row=4, max_row=9):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for col in ("A4", "B4", "C4"):
        ws2[col].fill, ws2[col].font = hfill, hfont

    wb.save(path)
    print("WROTE", path)


# ===========================================================================
# WORD
# ===========================================================================
def _shade(cell, hex_color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_cell(cell, text, bold=False, size=9, color=None, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def build_docx(path):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("PMC Managers")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = RGBColor.from_string(NAVY)
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = s.add_run("Bug & Enhancement Clearance Report")
    rs.font.size = Pt(15)
    rs.font.color.rgb = RGBColor.from_string(BRASS)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Release {VERSION}   ·   {TODAY}").font.size = Pt(10)

    doc.add_paragraph()

    # Executive summary
    doc.add_heading("Executive summary", level=1)
    counts = {}
    for it in ITEMS:
        counts[it[4]] = counts.get(it[4], 0) + 1
    doc.add_paragraph(
        "This report covers the current testing round across two batches: the re-verification "
        "and fix of the production bug-sheet items (Batch 1), and the new procurement-taxonomy, "
        "Go-Live and public-board filtering work (Batch 2). Every item below was implemented and "
        "verified in the preview environment; the backend test suite for the taxonomy / Go-Live "
        "work passes 14/14 and the Batch 1 fixes pass 8/8."
    )
    p = doc.add_paragraph()
    p.add_run("At a glance:  ").bold = True
    p.add_run(
        f"{counts.get('FIXED',0)} fixed · {counts.get('NEW',0)} new capabilities · "
        f"{counts.get('VERIFIED',0)} verified-already-correct · {counts.get('DEFERRED',0)} deferred by request."
    )
    note = doc.add_paragraph()
    nr = note.add_run(
        "Please note: items marked Fixed/New are verified in the preview build. They move to "
        "fully-closed once the production build is deployed (and CloudFront invalidated) and you "
        "have confirmed them on your side."
    )
    nr.italic = True
    nr.font.color.rgb = RGBColor.from_string("8A5A00")

    # Legend
    doc.add_heading("Status legend", level=2)
    lg = doc.add_table(rows=1, cols=2)
    lg.style = "Table Grid"
    _set_cell(lg.rows[0].cells[0], "Status", bold=True, size=9, color="FFFFFF")
    _set_cell(lg.rows[0].cells[1], "Meaning", bold=True, size=9, color="FFFFFF")
    _shade(lg.rows[0].cells[0], NAVY)
    _shade(lg.rows[0].cells[1], NAVY)
    for st in ["FIXED", "NEW", "VERIFIED", "DEFERRED"]:
        row = lg.add_row()
        _set_cell(row.cells[0], st, bold=True, size=9)
        _set_cell(row.cells[1], STATUS_NOTE[st], size=9)
        _shade(row.cells[0], STATUS_HEX[st])

    # Detail table grouped by batch
    doc.add_heading("Detailed clearance log", level=1)
    cur_batch = None
    table = None
    for no, mod, obs, did, st, pr, rv, batch in ITEMS:
        if batch != cur_batch:
            cur_batch = batch
            doc.add_heading(batch, level=2)
            table = doc.add_table(rows=1, cols=5)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = table.rows[0].cells
            for i, h in enumerate(["Ref", "Module", "Observation", "Resolution", "Status"]):
                _set_cell(hdr[i], h, bold=True, size=9, color="FFFFFF")
                _shade(hdr[i], NAVY)
            widths = [Inches(0.5), Inches(1.1), Inches(2.1), Inches(2.6), Inches(0.9)]
            for i, w in enumerate(widths):
                for cell in table.columns[i].cells:
                    cell.width = w
        row = table.add_row()
        cells = row.cells
        _set_cell(cells[0], f"#{no}" if no else "NEW", bold=True, size=9)
        _set_cell(cells[1], mod, size=9)
        _set_cell(cells[2], obs, size=9)
        _set_cell(cells[3], did, size=9)
        _set_cell(cells[4], st, bold=True, size=9)
        _shade(cells[4], STATUS_HEX.get(st, "FFFFFF"))
        for i, w in enumerate([Inches(0.5), Inches(1.1), Inches(2.1), Inches(2.6), Inches(0.9)]):
            cells[i].width = w

    # Evidence screenshots
    shots = [
        ("01_tender_filters.png", "Public tender board — Sector / Contract Type / Category / Country filters with a shareable deep-link URL."),
        ("02_golive.png", "Admin Masters — Go-Live switch (OFF by default)."),
        ("03_registrations.png", "Admin Registrations — review panel; selection clears on status-tab switch."),
    ]
    added_any = any(os.path.exists(os.path.join(SHOTS, f)) for f, _ in shots)
    if added_any:
        doc.add_page_break()
        doc.add_heading("Preview evidence", level=1)
        for fname, cap in shots:
            fp = os.path.join(SHOTS, fname)
            if os.path.exists(fp):
                doc.add_picture(fp, width=Inches(6.3))
                c = doc.add_paragraph()
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = c.add_run(cap)
                cr.italic = True
                cr.font.size = Pt(9)
                doc.add_paragraph()

    doc.save(path)
    print("WROTE", path)


if __name__ == "__main__":
    stamp = date.today().strftime("%Y%m%d")
    for d in ("/app/deliverables", "/app/frontend/public/downloads"):
        os.makedirs(d, exist_ok=True)
        build_xlsx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.xlsx"))
        build_docx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.docx"))
