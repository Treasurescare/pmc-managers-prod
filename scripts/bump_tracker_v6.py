"""Bump Bug Tracker v5 → v6 and Observations Response v5 → v6.
Marks the 8 Bucket B/C items as CLOSED with fix-version v18/v21 evidence.
"""
from pathlib import Path
from datetime import datetime
from copy import copy
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from docx import Document
from docx.shared import RGBColor, Pt

TS = datetime.utcnow().strftime("%d %b %Y")

CLOSURES = {
    "V-02": ("CLOSED · v18/v21", f"Pending-verify / Active / Inactive filter pills added to Vendors master (pmc-frontend-v21). Verified live in Master Manual v4 ch. 23b. Fixed {TS}."),
    "N-02": ("CLOSED · v18/v21", f"'📐 template linked ↗' pill is now a jump-link to Tender Builder for that template (NoticesPanel.jsx). Verified live in Master Manual v4 ch. 24. Fixed {TS}."),
    "T-01": ("CLOSED · v18/v21", f"Added 'ALL KINDS' pill to Tender Builder sidebar — shows tenders + RFPs + RFQs in a single list. Verified live in Master Manual v4 ch. 26a. Fixed {TS}."),
    "E-03": ("CLOSED · v18/v21", f"New Reconciliation ledger-vs-bank section on Escrow panel with delta pills (Reconciled / Pending bank feed / Delta). Verified live in Master Manual v4 ch. 28a. Fixed {TS}."),
    "RA-01": ("CLOSED · v18/v21", f"'View summary' expander on closed reverse auctions — starting/floor/winning/savings % + winner + timing. Verified live in Master Manual v4 ch. 32a. Fixed {TS}."),
    "MP-01": ("CLOSED · v18/v21", f"'Clone role' column added to Masters → Staff table — one-click copy of roles + hierarchy_level into new-staff form. Verified live in Master Manual v4 ch. 37e. Fixed {TS}."),
    "AU-01": ("CLOSED · v18/v21", f"Filter bar on Audit panel — actor / event type / from date / to date + Clear. Verified live in Master Manual v4 ch. 40a. Fixed {TS}."),
    "EN-03": ("CLOSED · v18/v21", f"Every buyer email in Engagements is now a jump-link to Vendors master pre-filtered by that email. Verified live in Master Manual v4 ch. 42a. Fixed {TS}."),
}

# ---------------- Excel v6 ----------------
xls_src = Path("/app/deliverables/PMC_Bug_Tracker_v5.xlsx")
xls_out = Path("/app/deliverables/PMC_Bug_Tracker_v6.xlsx")
wb = load_workbook(xls_src)
ws = wb["Observation Clearance v5"]
ws.title = "Observation Clearance v6"

green_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
green_font = Font(color="0B5A2E", bold=True)

updated = 0
for row in ws.iter_rows(min_row=2):
    bug_id = row[0].value
    if bug_id in CLOSURES:
        status, evidence = CLOSURES[bug_id]
        row[4].value = status
        row[5].value = evidence
        for cell in row:
            cell.fill = green_fill
        row[4].font = green_font
        updated += 1

# Update summary sheet totals
try:
    sm = wb["Summary"]
    # find rows we need to update
    for r in sm.iter_rows():
        for c in r:
            v = str(c.value or "")
            if "44" in v and "52" in v:
                # "44/52" wording gets bumped to 52/52
                c.value = v.replace("44/52", "52/52").replace("44 of 52", "52 of 52")
            if "8 deferred" in v.lower() or "8 open" in v.lower():
                c.value = v.replace("8 deferred", "0 deferred").replace("8 open", "0 open")
except Exception:
    pass

# Append a v6 changelog row at the end of the main sheet
last = ws.max_row + 2
ws.cell(row=last, column=1, value="v6 changelog").font = Font(bold=True, color="0B1F3A")
ws.cell(row=last + 1, column=1, value=f"Generated {TS}: 8 Bucket B/C observations CLOSED (v18/v21). Bug Tracker now 52/52 (100%).")
wb.save(str(xls_out))
print(f"[xlsx] {xls_out} · updated {updated} rows")

# ---------------- DOCX v6 ----------------
docx_src = Path("/app/deliverables/PMC_Portal_Observations_Response_v5.docx")
docx_out = Path("/app/deliverables/PMC_Portal_Observations_Response_v6.docx")
d = Document(docx_src)

# Update the single table's rows
for t in d.tables:
    for r in t.rows:
        cells = r.cells
        if not cells:
            continue
        bug_id = cells[0].text.strip()
        if bug_id in CLOSURES:
            status, evidence = CLOSURES[bug_id]
            # Status is usually col 4, evidence col 5 — mirror the xlsx layout
            if len(cells) >= 5:
                cells[4].text = status
                for para in cells[4].paragraphs:
                    for run in para.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0x0B, 0x5A, 0x2E)
            if len(cells) >= 6:
                cells[5].text = evidence

# Update body paragraphs that mention 44/52 or 8 deferred/Bucket
replacements = [
    ("44 / 52", "52 / 52"),
    ("44/52", "52/52"),
    ("44 of 52", "52 of 52"),
    ("8 deferred", "0 deferred"),
    ("8 Bucket B/C", "0 Bucket B/C · all closed"),
    ("(85%)", "(100%)"),
    ("v5 · ", "v6 · "),
]
for p in d.paragraphs:
    for old, new in replacements:
        if old in p.text:
            for run in p.runs:
                if old in run.text:
                    run.text = run.text.replace(old, new)

# Append a v6 change note as a fresh paragraph before end
d.add_paragraph()
h = d.add_paragraph()
r = h.add_run(f"v6 · {TS} — 8 Bucket B/C observations CLOSED")
r.font.bold = True
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(0x0B, 0x5A, 0x2E)

p = d.add_paragraph()
p.add_run(
    "The last 8 deferred observations (V-02, N-02, T-01, E-03, RA-01, MP-01, AU-01, EN-03) are now shipped in "
    "pmc-backend-v18 and pmc-frontend-v21. Each fix is captured live in Master Training Manual v4 "
    "(chapters 23b, 24, 26a, 28a, 32a, 37e, 40a, 42a). Overall clearance is now 52 / 52 (100%)."
).font.size = Pt(10.5)

d.save(str(docx_out))
print(f"[docx] {docx_out}")
