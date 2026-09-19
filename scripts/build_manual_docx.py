"""
build_manual_docx.py — Assembles the PMC v2 User Manual as DOCX + PDF.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from manual_content import MODULES  # noqa: E402

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SHOTS_DIR = Path("/app/deliverables/manual/screenshots")
OUT_DIR   = Path("/app/deliverables/manual")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUT_DIR / "PMC_User_Manual_v1.docx"
PDF_PATH  = OUT_DIR / "PMC_User_Manual_v1.pdf"

NAVY = RGBColor(0x0B, 0x1E, 0x3F)
GREY = RGBColor(0x55, 0x55, 0x55)


def _add_heading(doc, text, level=1):
    h = doc.add_heading("", level=level)
    r = h.add_run(text)
    r.font.color.rgb = NAVY
    return h


def _add_kv(doc, label, value):
    p = doc.add_paragraph()
    r = p.add_run(f"{label}: ")
    r.bold = True
    r.font.color.rgb = NAVY
    p.add_run(value)


def _add_panel_shot(doc, code):
    shot = SHOTS_DIR / f"{code}-panel.png"
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(6.0))


def _add_action_shot(doc, filename):
    shot = SHOTS_DIR / filename
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(5.8))


def build():
    doc = Document()

    # ---- Cover ----
    cover = doc.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cover.add_run("PMC Managers v2\n")
    r.font.size = Pt(28); r.font.color.rgb = NAVY; r.bold = True
    r = cover.add_run("User Manual\n")
    r.font.size = Pt(22); r.font.color.rgb = NAVY
    r = cover.add_run(f"\nVersion 1 · {datetime.utcnow().strftime('%B %Y')}\n")
    r.font.size = Pt(12); r.font.color.rgb = GREY
    r = cover.add_run("Comprehensive guide — every module, every action, every screen.\n")
    r.font.size = Pt(11); r.italic = True; r.font.color.rgb = GREY

    doc.add_page_break()

    # ---- Table of contents ----
    _add_heading(doc, "Contents", level=1)
    for code, m in MODULES.items():
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{m['title']}  ").bold = True
        p.add_run(f"— {len(m.get('actions') or [])} action(s)").italic = True
    doc.add_page_break()

    # ---- Modules ----
    for code, m in MODULES.items():
        _add_heading(doc, m["title"], level=1)
        _add_kv(doc, "Surface",  m["surface"])
        _add_kv(doc, "URL path", m["url_path"])
        _add_kv(doc, "Purpose",  m["purpose"])
        if m.get("prerequisites"):
            doc.add_paragraph().add_run("Prerequisites").bold = True
            for pr in m["prerequisites"]:
                doc.add_paragraph(pr, style="List Bullet")
        _add_panel_shot(doc, code)

        actions = m.get("actions") or []
        if not actions:
            p = doc.add_paragraph()
            p.add_run("Content in progress — see Phase 2 (this module's actions "
                      "will be authored in the next batch).").italic = True
            doc.add_page_break()
            continue

        for i, a in enumerate(actions, start=1):
            _add_heading(doc, f"{i}. {a['label']}", level=2)
            _add_kv(doc, "When to use", a.get("when", ""))
            doc.add_paragraph().add_run("Steps").bold = True
            for step in a.get("steps", []):
                doc.add_paragraph(step, style="List Number")
            _add_kv(doc, "Expected result", a.get("expected", ""))

            if a.get("controls"):
                doc.add_paragraph().add_run("Controls & fields").bold = True
                for c in a["controls"]:
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(c["name"] + ": ").bold = True
                    p.add_run(c["desc"])

            if a.get("errors"):
                doc.add_paragraph().add_run("Common errors & fixes").bold = True
                for e in a["errors"]:
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(f"{e['code']} — {e['msg']}").bold = True
                    doc.add_paragraph(f"Fix: {e['fix']}").paragraph_format.left_indent = Inches(0.5)

            if a.get("screenshot"):
                _add_action_shot(doc, a["screenshot"])

        doc.add_page_break()

    # ---- Appendix ----
    _add_heading(doc, "Appendix A — Live URLs", level=1)
    for label, url in [
        ("Public notice board", "https://www.pmcmanagers.com/"),
        ("Registration portal", "https://www.pmcmanagers.com/register"),
        ("Admin console",       "https://www.pmcmanagers.com/admin"),
        ("Vendor portal",       "https://www.pmcmanagers.com/vendor"),
        ("Staff portal",        "https://www.pmcmanagers.com/staff"),
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{label}: ").bold = True
        p.add_run(url)

    doc.save(str(DOCX_PATH))
    print(f"DOCX  → {DOCX_PATH}  ({DOCX_PATH.stat().st_size // 1024} KB)")

    # PDF via LibreOffice (headless)
    r = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(OUT_DIR), str(DOCX_PATH)],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        print("PDF conversion stderr:", r.stderr)
    if PDF_PATH.exists():
        print(f"PDF   → {PDF_PATH}  ({PDF_PATH.stat().st_size // 1024} KB)")
    else:
        print("PDF   → (conversion failed — DOCX is fine)")

    return DOCX_PATH, PDF_PATH


if __name__ == "__main__":
    build()
