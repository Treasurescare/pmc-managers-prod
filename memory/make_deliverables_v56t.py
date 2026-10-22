"""Generate the PMC Managers v56t deliverables (Word + Excel).

Reuses the v56s bug-sheet clearance content verbatim (same client references +
honest, preview-qualified statuses) and appends a "New capabilities in v56t"
section covering the homepage taxonomy search, the country-currency master,
the notice taxonomy backfill and the bid/EMD currency lock.
"""
import os
import sys
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

sys.path.insert(0, "/app/memory")
import make_deliverables_v56s as base  # noqa: E402

VERSION = "v56t"
base.VERSION = VERSION  # so reused builders title everything v56t
TODAY = date.today().strftime("%d %b %Y")
NAVY, BRASS = base.NAVY, base.BRASS
_set, _shade = base._set, base._shade

# name, what it does, where, status
NEW_CAPS = [
    ("Homepage taxonomy search",
     "The public homepage search now uses your primary taxonomy — Sector -> Contract type -> "
     "Category — plus the full 250-country master and a keyword box. Filters are optional and "
     "combine in any order; submitting deep-links to the live tender board and restores the same "
     "filters on a shareable URL.",
     "Public home / Tender board", "NEW"),
    ("Country <-> currency master",
     "Each country now has an editable set of accepted currencies with one marked primary/default "
     "(Admin -> Masters -> Country currencies). The notice budget-currency picker default-loads the "
     "delivery country's primary (accepted set shown first) while still allowing any active currency.",
     "Admin -> Masters -> Country currencies", "NEW"),
    ("Notice taxonomy backfill",
     "A new admin screen lists every notice with its Sector and Contract-type auto-guessed from the "
     "category/title text. Admins review, correct and Save in bulk so legacy notices get taxonomy "
     "codes and appear under the new homepage filters.",
     "Admin -> Taxonomy backfill", "NEW"),
    ("Bid & EMD currency locked to tender",
     "Vendor bid price and EMD are always quoted in the tender's own currency (no mismatched-currency "
     "bids). Combined with the country-currency default, the tender currency itself now follows the "
     "delivery country's primary.",
     "Vendor -> Submit a bid / EMD", "NEW"),
]
NEW_HEX = "E0E7FF"


def build_xlsx(path):
    base.build_xlsx(path)  # Bug Tracker + Summary (titled v56t)
    wb = openpyxl.load_workbook(path)
    ws = wb.create_sheet("New in v56t")
    border = Border(*(Side(style="thin", color="D4D4D4"),) * 4)
    hfill = PatternFill("solid", fgColor=NAVY)
    hfont = Font(bold=True, color="FFFFFF", size=11)
    ws.append([f"New capabilities added in {VERSION}"])
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws.append(["Generated", TODAY])
    ws.append([])
    headers = ["Capability", "What it does", "Where", "Status"]
    ws.append(headers)
    hrow = ws.max_row
    for i in range(1, len(headers) + 1):
        c = ws.cell(row=hrow, column=i)
        c.fill, c.font, c.border = hfill, hfont, border
        c.alignment = Alignment(horizontal="left", vertical="center")
    for name, desc, where, st in NEW_CAPS:
        ws.append([name, desc, where, st])
        r = ws.max_row
        for ci in range(1, 5):
            cell = ws.cell(row=r, column=ci)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
        ws.cell(row=r, column=4).fill = PatternFill("solid", fgColor=NEW_HEX)
        ws.cell(row=r, column=4).font = Font(bold=True)
    for col, w in zip("ABCD", [26, 78, 30, 10]):
        ws.column_dimensions[col].width = w
    wb.save(path)
    print("WROTE", path)


def build_docx(path):
    base.build_docx(path)  # full bug-sheet clearance report (titled v56t)
    doc = Document(path)
    doc.add_page_break()
    doc.add_heading("New capabilities in v56t", level=1)
    doc.add_paragraph(
        "Beyond the bug-sheet items above, this release adds the following new capabilities "
        "(preview-verified; pending production deploy + your sign-off):"
    )
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(["Capability", "What it does", "Where", "Status"]):
        _set(hdr[i], h, True, 9, "FFFFFF")
        _shade(hdr[i], NAVY)
    widths = [Inches(1.4), Inches(3.4), Inches(1.35), Inches(0.65)]
    for name, desc, where, st in NEW_CAPS:
        cells = table.add_row().cells
        _set(cells[0], name, True, 9)
        _set(cells[1], desc, False, 9)
        _set(cells[2], where, False, 8)
        _set(cells[3], st, True, 9)
        _shade(cells[3], NEW_HEX)
        for i, w in enumerate(widths):
            cells[i].width = w
    doc.save(path)
    print("WROTE", path)


if __name__ == "__main__":
    stamp = date.today().strftime("%Y%m%d")
    for d in ("/app/deliverables", "/app/frontend/public/downloads"):
        os.makedirs(d, exist_ok=True)
        build_xlsx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.xlsx"))
        build_docx(os.path.join(d, f"PMC_Bug_Clearance_{VERSION}_{stamp}.docx"))
