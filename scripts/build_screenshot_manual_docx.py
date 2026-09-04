"""Build /app/deliverables/PMC_Screenshot_Training_Manual_v1.docx — a Word
counterpart to the PDF training + testing manual, using the same manifest.json
+ screenshots captured by capture_screenshot_manual.py.

Each screen becomes a page with:
  * numbered heading + URL
  * embedded screenshot (fits page width)
  * narrative
  * 3-column testing-checklist table (#, step, expected)
  * data-testid selector list
"""
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

SCREENSHOT_DIR = Path("/app/deliverables/manual_screenshots")
OUT = Path("/app/deliverables/PMC_Screenshot_Training_Manual_v1.docx")

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY_SOFT = RGBColor(0x5B, 0x7B, 0xA1)
GREY = RGBColor(0x64, 0x74, 0x8B)


def _set_cell_shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _run(paragraph, text, *, size=10, bold=False, italic=False, color=None,
          font="Calibri"):
    r = paragraph.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def _kicker(doc, text):
    p = doc.add_paragraph()
    _run(p, text.upper(), size=8, bold=True, color=NAVY_SOFT)


def _build_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _run(p, "PMC Managers v2 · Training & Testing Manual v1 · Confidential",
          size=8, color=GREY)
    # right-align page number on new run
    p.add_run("\t\t")
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r = p.add_run("").element
    r.append(fld_begin)
    r.append(instr)
    r.append(fld_sep)
    r.append(fld_end)


def build():
    if not SCREENSHOT_DIR.exists():
        raise SystemExit(f"Screenshot dir missing: {SCREENSHOT_DIR}")
    manifest_path = SCREENSHOT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.sort(key=lambda s: s["n"])

    doc = Document()

    # Page setup — A4 with tight margins so screenshots fit
    section = doc.sections[0]
    section.page_height = Inches(11.69)
    section.page_width = Inches(8.27)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(0.6))
    _build_footer(section)

    # ---- Cover -----------------------------------------------------------
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _run(p, "PMC Managers v2", size=32, bold=True, color=NAVY)
    p = doc.add_paragraph()
    _run(p, "Screenshot-based Training & Testing Manual · v1",
          size=18, italic=True, color=NAVY_SOFT)
    doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p,
          "Walkthrough of every substantive screen in the portal — public "
          "landing → tender board → vendor registration → admin login → each "
          "admin tab → sign out. Every page shows a live screenshot, a "
          "narrative, a step-by-step testing checklist, and the exact "
          "data-testid selectors your QA team or Playwright suite can hook into.",
          size=10.5, color=NAVY)
    doc.add_paragraph()
    p = doc.add_paragraph()
    _run(p, "Deliver this manual to:", size=10.5, bold=True, color=NAVY)
    for line in ("Trainee operations staff",
                  "External QA / penetration-testing teams",
                  "Investor code-review reviewers"):
        b = doc.add_paragraph(line, style="List Bullet")
        for r in b.runs:
            r.font.size = Pt(10.5)
            r.font.color.rgb = NAVY

    doc.add_page_break()

    # ---- TOC ---------------------------------------------------------------
    p = doc.add_paragraph()
    _run(p, "Contents", size=22, bold=True, color=NAVY)
    doc.add_paragraph()

    toc = doc.add_table(rows=1, cols=3)
    toc.style = "Light Grid Accent 1"
    hdr = toc.rows[0].cells
    hdr[0].text = "#"; hdr[1].text = "Screen"; hdr[2].text = "URL"
    for cell in hdr:
        _set_cell_shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for step in manifest:
        row = toc.add_row().cells
        row[0].text = str(step["n"])
        row[1].text = step["title"]
        row[2].text = step["url"]
        for cell in row:
            for para in cell.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(8.5)
                    r.font.color.rgb = NAVY

    toc.columns[0].width = Inches(0.35)
    toc.columns[1].width = Inches(3.0)
    toc.columns[2].width = Inches(3.8)

    doc.add_page_break()

    # ---- Per-step pages ---------------------------------------------------
    for step in manifest:
        p = doc.add_paragraph()
        _run(p, f"Step {step['n']} · {step['title']}",
              size=20, bold=True, color=NAVY)
        p = doc.add_paragraph()
        _run(p, f"URL  ·  {step['url']}", size=8, color=NAVY_SOFT,
              font="Consolas")

        img_path = SCREENSHOT_DIR / step["image"]
        if img_path.exists():
            doc.add_picture(str(img_path), width=Inches(7.0))
        else:
            p = doc.add_paragraph()
            _run(p, f"[missing screenshot: {step['image']}]", size=10,
                  italic=True, color=GREY)

        _kicker(doc, "What this screen is for")
        p = doc.add_paragraph()
        _run(p, step["narrative"], size=10, color=NAVY)

        # Testing checklist
        if step.get("test_steps"):
            _kicker(doc, "Testing checklist")
            tbl = doc.add_table(rows=1, cols=3)
            tbl.style = "Light Grid Accent 1"
            hdr = tbl.rows[0].cells
            hdr[0].text = "#"; hdr[1].text = "Test step"; hdr[2].text = "Expected outcome"
            for cell in hdr:
                _set_cell_shading(cell, "0B1F3A")
                for para in cell.paragraphs:
                    for r in para.runs:
                        r.font.bold = True
                        r.font.size = Pt(9)
                        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            for i, ts in enumerate(step["test_steps"], start=1):
                row = tbl.add_row().cells
                row[0].text = str(i)
                row[1].text = ts.get("step", "")
                row[2].text = ts.get("expected", "")
                for cell in row:
                    for para in cell.paragraphs:
                        for r in para.runs:
                            r.font.size = Pt(8.5)
                            r.font.color.rgb = NAVY
            tbl.columns[0].width = Inches(0.35)
            tbl.columns[1].width = Inches(3.3)
            tbl.columns[2].width = Inches(3.5)

        # data-testid references
        if step.get("test_ids"):
            _kicker(doc, "Playwright / data-testid references")
            p = doc.add_paragraph()
            _run(p, " · ".join(step["test_ids"]),
                  size=9, color=NAVY_SOFT, font="Consolas")

        doc.add_page_break()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"Written {OUT} · {OUT.stat().st_size / 1024:.1f} KB · "
          f"{len(manifest)} screens")


if __name__ == "__main__":
    build()
