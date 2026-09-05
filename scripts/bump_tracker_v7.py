"""Bump Bug Tracker v6 → v7 · pilot-hiding note added.

Docs the fact that Stakeholder Reports, Help Requests and Portal Branding
have been HIDDEN in the admin UI during external pilot testing (backend
routes still exist — this is a UI-only feature-flag).
"""
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from docx import Document
from docx.shared import RGBColor, Pt

TS = datetime.utcnow().strftime("%d %b %Y")

xls_src = Path("/app/deliverables/PMC_Bug_Tracker_v6.xlsx")
xls_out = Path("/app/deliverables/PMC_Bug_Tracker_v7.xlsx")
docx_src = Path("/app/deliverables/PMC_Portal_Observations_Response_v6.docx")
docx_out = Path("/app/deliverables/PMC_Portal_Observations_Response_v7.docx")

# -------------- Excel v7 --------------
wb = load_workbook(xls_src)
ws = wb.active
if "v6" in ws.title:
    ws.title = ws.title.replace("v6", "v7")

# Append the pilot-hiding notice as fresh rows
last = ws.max_row + 2
grey = PatternFill(start_color="E8ECF3", end_color="E8ECF3", fill_type="solid")

hdr = ws.cell(row=last, column=1, value="v7 pilot-testing note")
hdr.font = Font(bold=True, color="0B1F3A", size=12)
last += 1
ws.cell(row=last, column=1, value=(
    f"{TS} · During external pilot testing the following admin panels are HIDDEN in the UI: "
    "Stakeholder Reports (tab=stakeholder), Help Requests (tab=help), Portal Branding (tab=branding). "
    "Backend routes remain intact and covered by v4/v5 test cycles. Re-enable by un-commenting three "
    "pairs of lines in AdminDashboard.jsx. Not a defect — an intentional feature-flag."
))
for c in ws[last]:
    c.fill = grey

# Also append rows so they show as ordered items
pilot_hidden = [
    ("PILOT-01", "Admin console · Stakeholder Reports", "Panel hidden during pilot testing (backend intact).", "Feature-flag", "HIDDEN · pilot", "AdminDashboard.jsx lines 26, 67, 197-201"),
    ("PILOT-02", "Admin console · Help Requests",       "Panel hidden during pilot testing (backend intact).", "Feature-flag", "HIDDEN · pilot", "AdminDashboard.jsx lines 36, 68, 197-201"),
    ("PILOT-03", "Admin console · Portal Branding",     "Panel hidden during pilot testing (backend intact).", "Feature-flag", "HIDDEN · pilot", "AdminDashboard.jsx lines 37, 69, 197-201"),
]
last += 2
for row in pilot_hidden:
    for i, v in enumerate(row, start=1):
        ws.cell(row=last, column=i, value=v).fill = grey
    last += 1

wb.save(str(xls_out))
print(f"[xlsx] {xls_out}")

# -------------- DOCX v7 --------------
d = Document(docx_src)
# Replace v6 mentions with v7 in-place
for p in d.paragraphs:
    for run in p.runs:
        if "v6" in run.text:
            run.text = run.text.replace("v6 · ", "v7 · ")

# Append pilot-hiding note as a new section
d.add_paragraph()
h = d.add_paragraph()
r = h.add_run(f"v7 · {TS} — Pilot-testing UI feature-flag (3 panels hidden)")
r.font.bold = True
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(0x0B, 0x1F, 0x3A)

d.add_paragraph(
    "During external pilot testing the following admin panels are intentionally hidden "
    "in the UI. Backend routes remain in place and are covered by the v4/v5 test cycles."
).runs[0].font.size = Pt(10.5)

tbl = d.add_table(rows=1, cols=3)
hdr_cells = tbl.rows[0].cells
for i, txt in enumerate(("ID", "Panel", "Note")):
    p = hdr_cells[i].paragraphs[0]
    rr = p.add_run(txt)
    rr.font.bold = True
    rr.font.size = Pt(10)
    rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "0B1F3A")
    tcPr.append(shd)

for pid, panel, note in [
    ("PILOT-01", "Stakeholder Reports (tab=stakeholder)", "Hidden in admin UI; backend routes untouched."),
    ("PILOT-02", "Help Requests (tab=help)",              "Hidden in admin UI; backend routes untouched."),
    ("PILOT-03", "Portal Branding (tab=branding)",        "Hidden in admin UI; backend routes untouched."),
]:
    row = tbl.add_row().cells
    row[0].text = pid
    row[1].text = panel
    row[2].text = note

d.save(str(docx_out))
print(f"[docx] {docx_out}")
