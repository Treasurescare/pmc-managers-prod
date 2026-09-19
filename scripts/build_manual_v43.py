"""
build_manual_v43.py — Assembles PMC v2 User Manual (v43) as DOCX + PDF.

Extends build_manual_docx.py by adding the granular per-action screenshots
captured by capture_manual_v43.py (Playwright). For every admin action the
manual now embeds:
  1. The panel-level screenshot   (existing 69 shots)
  2. The action-specific modal shot from screenshots/action/

Output:
  /app/deliverables/manual/PMC_User_Manual_v43.docx
  /app/deliverables/manual/PMC_User_Manual_v43.pdf
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from manual_content import MODULES  # noqa: E402

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

SHOTS_DIR = Path("/app/deliverables/manual/screenshots")
ACTION_DIR = SHOTS_DIR / "action"
OUT_DIR = Path("/app/deliverables/manual")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUT_DIR / "PMC_User_Manual_v43.docx"
PDF_PATH = OUT_DIR / "PMC_User_Manual_v43.pdf"

NAVY = RGBColor(0x0B, 0x1E, 0x3F)
GREY = RGBColor(0x55, 0x55, 0x55)

# Map manual module_code → list of action shot files (from action/)
# Any file matching admin-{tab}-* is auto-associated to the module.
def _action_shots_for(code):
    # e.g. "admin-notices" → prefix "admin-notices-"
    prefix = f"{code}-"
    if not ACTION_DIR.exists():
        return []
    return sorted([p for p in ACTION_DIR.iterdir() if p.name.startswith(prefix)])


def _heading(doc, text, level=1):
    h = doc.add_heading("", level=level)
    r = h.add_run(text)
    r.font.color.rgb = NAVY


def _kv(doc, label, value):
    p = doc.add_paragraph()
    r = p.add_run(f"{label}: ")
    r.bold = True
    r.font.color.rgb = NAVY
    p.add_run(value or "")


def _panel_shot(doc, code):
    shot = SHOTS_DIR / f"{code}-panel.png"
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(6.0))


def _action_shot(doc, filename):
    shot = SHOTS_DIR / filename
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(5.8))


def build():
    doc = Document()

    cover = doc.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cover.add_run("PMC Managers v2\n")
    r.font.size = Pt(28); r.font.color.rgb = NAVY; r.bold = True
    r = cover.add_run("User Manual\n")
    r.font.size = Pt(22); r.font.color.rgb = NAVY
    r = cover.add_run(f"\nVersion 43 · {datetime.utcnow().strftime('%B %Y')}\n")
    r.font.size = Pt(12); r.font.color.rgb = GREY
    r = cover.add_run(
        "Comprehensive guide — every module, every action, every screen "
        "with per-modal screenshots and dense contextual tooltips.\n"
    )
    r.font.size = Pt(11); r.italic = True; r.font.color.rgb = GREY

    doc.add_page_break()

    _heading(doc, "Contents", level=1)
    for code, m in MODULES.items():
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{m['title']}  ").bold = True
        p.add_run(f"— {len(m.get('actions') or [])} action(s)").italic = True
    doc.add_page_break()

    for code, m in MODULES.items():
        _heading(doc, m["title"], level=1)
        _kv(doc, "Surface", m["surface"])
        _kv(doc, "URL path", m["url_path"])
        _kv(doc, "Purpose", m["purpose"])
        if m.get("prerequisites"):
            doc.add_paragraph().add_run("Prerequisites").bold = True
            for pr in m["prerequisites"]:
                doc.add_paragraph(pr, style="List Bullet")
        _panel_shot(doc, code)

        # v43 — per-modal action shots
        extras = _action_shots_for(code)
        if extras:
            doc.add_paragraph().add_run("Per-modal screenshots (v43)").bold = True
            for shot in extras:
                doc.add_picture(str(shot), width=Inches(5.8))
                cap = doc.add_paragraph()
                r = cap.add_run(shot.stem)
                r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GREY

        actions = m.get("actions") or []
        if not actions:
            p = doc.add_paragraph()
            p.add_run("Content in progress.").italic = True
            doc.add_page_break()
            continue

        for i, a in enumerate(actions, start=1):
            _heading(doc, f"{i}. {a['label']}", level=2)
            _kv(doc, "When to use", a.get("when", ""))
            doc.add_paragraph().add_run("Steps").bold = True
            for step in a.get("steps", []):
                doc.add_paragraph(step, style="List Number")
            _kv(doc, "Expected result", a.get("expected", ""))
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
                _action_shot(doc, a["screenshot"])

        doc.add_page_break()

    _heading(doc, "Appendix A — Live URLs", level=1)
    for label, url in [
        ("Public notice board", "https://www.pmcmanagers.com/"),
        ("Registration portal", "https://www.pmcmanagers.com/register"),
        ("Admin console", "https://www.pmcmanagers.com/admin"),
        ("Vendor portal", "https://www.pmcmanagers.com/vendor"),
        ("Staff portal", "https://www.pmcmanagers.com/staff"),
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{label}: ").bold = True
        p.add_run(url)

    doc.save(str(DOCX_PATH))
    print(f"DOCX → {DOCX_PATH} ({DOCX_PATH.stat().st_size // 1024} KB)")

    r = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(OUT_DIR), str(DOCX_PATH)],
        capture_output=True, text=True, timeout=240,
    )
    if r.returncode != 0:
        print("PDF conversion stderr:", r.stderr)
    if PDF_PATH.exists():
        print(f"PDF  → {PDF_PATH} ({PDF_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
