"""Build /app/deliverables/PMC_Screenshot_Training_Manual_v1.pdf from the
manifest + screenshots captured by capture_screenshot_manual.py.

Uses ReportLab so we can bind large PNGs cleanly across pages (WeasyPrint's
HTML-image flow is brittle at this scale).
"""
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

SCREENSHOT_DIR = Path("/app/deliverables/manual_screenshots")
OUT_PDF = Path("/app/deliverables/PMC_Screenshot_Training_Manual_v1.pdf")

NAVY = HexColor("#0B1F3A")
NAVY_SOFT = HexColor("#5B7BA1")
GREY = HexColor("#64748B")
PALE = HexColor("#F1F5F9")
EMERALD = HexColor("#065F46")
AMBER = HexColor("#78350F")

# --- Styles ---
h_title = ParagraphStyle("HTitle", fontName="Helvetica-Bold", fontSize=22,
                          textColor=NAVY, leading=26, spaceAfter=6)
h_sub   = ParagraphStyle("HSub", fontName="Helvetica-Oblique", fontSize=11,
                          textColor=GREY, leading=14, spaceAfter=18)
h_step  = ParagraphStyle("HStep", fontName="Helvetica-Bold", fontSize=13,
                          textColor=NAVY, leading=16, spaceBefore=8, spaceAfter=6)
h_url   = ParagraphStyle("HURL", fontName="Courier", fontSize=8,
                          textColor=NAVY_SOFT, leading=10, spaceAfter=8)
p_body  = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5,
                          textColor=NAVY, leading=13, spaceAfter=6)
p_test  = ParagraphStyle("Test", fontName="Helvetica", fontSize=8.5,
                          textColor=NAVY, leading=12)
p_kicker = ParagraphStyle("Kick", fontName="Helvetica-Bold", fontSize=8,
                           textColor=NAVY_SOFT, leading=10, spaceAfter=4)


def _kicker(text): return Paragraph(f"<b>{text.upper()}</b>", p_kicker)


def _step_page(step: dict) -> list:
    story = []
    story.append(Paragraph(f"Step {step['n']} · {step['title']}", h_title))
    story.append(Paragraph(f"URL &nbsp;·&nbsp; {step['url']}", h_url))
    # Image (fit width ~ 175mm, keep aspect)
    img_path = SCREENSHOT_DIR / step["image"]
    if img_path.exists():
        img = Image(str(img_path), width=175 * mm)
        img._restrictSize(175 * mm, 105 * mm)
        story.append(img)
    else:
        story.append(Paragraph(f"[missing screenshot: {step['image']}]", p_body))
    story.append(Spacer(1, 6))
    story.append(_kicker("What this screen is for"))
    story.append(Paragraph(step["narrative"], p_body))
    # Test steps table
    rows = [["#", "Test step", "Expected outcome"]]
    for i, ts in enumerate(step.get("test_steps", []), start=1):
        rows.append([str(i), ts.get("step", ""), ts.get("expected", "")])
    if len(rows) > 1:
        tbl = Table(rows, colWidths=[8 * mm, 80 * mm, 87 * mm], hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), PALE]),
            ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#CBD5E1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(Spacer(1, 8))
        story.append(_kicker("Testing checklist"))
        story.append(tbl)
    # Test IDs
    if step.get("test_ids"):
        story.append(Spacer(1, 6))
        story.append(_kicker("Playwright / data-testid references"))
        story.append(Paragraph(
            " · ".join(f"<font face='Courier' color='#5B7BA1'>{tid}</font>"
                       for tid in step["test_ids"]),
            p_test))
    story.append(PageBreak())
    return story


def _cover() -> list:
    story = [Spacer(1, 60 * mm),
             Paragraph("PMC Managers v2", h_title),
             Paragraph("Screenshot-based Training &amp; Testing Manual · v1",
                       ParagraphStyle("Sub", fontName="Helvetica",
                                       fontSize=16, textColor=NAVY_SOFT,
                                       leading=20, spaceAfter=24)),
             Paragraph(
                 "Walkthrough of every substantive screen in the portal — public "
                 "landing → tender board → vendor registration → admin login → "
                 "each admin tab → sign out. Every page shows a live screenshot, "
                 "a narrative, a step-by-step testing checklist, and the exact "
                 "<font face='Courier'>data-testid</font> selectors your QA team "
                 "or Playwright suite can hook into.",
                 p_body),
             Spacer(1, 24),
             Paragraph(
                 "<b>Deliver this manual to:</b><br/>· Trainee operations staff<br/>"
                 "· External QA / penetration-testing teams<br/>"
                 "· Investor code review reviewers", p_body),
             PageBreak()]
    return story


def _toc(manifest: list) -> list:
    story = [Paragraph("Contents", h_title), Spacer(1, 12)]
    rows = [["#", "Screen", "URL"]]
    for s in manifest:
        rows.append([str(s["n"]), s["title"], s["url"]])
    tbl = Table(rows, colWidths=[8 * mm, 70 * mm, 97 * mm], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), PALE]),
        ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(PageBreak())
    return story


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(15 * mm, 10 * mm,
                       "PMC Managers v2 · Training & Testing Manual v1 · Confidential")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm,
                            f"Page {doc.page}")
    canvas.restoreState()


def build():
    manifest_path = SCREENSHOT_DIR / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest missing: {manifest_path} — run capture first")
    manifest = json.loads(manifest_path.read_text())
    manifest.sort(key=lambda s: s["n"])

    doc = BaseDocTemplate(str(OUT_PDF), pagesize=A4,
                           leftMargin=15 * mm, rightMargin=15 * mm,
                           topMargin=14 * mm, bottomMargin=15 * mm,
                           title="PMC Managers v2 Training & Testing Manual",
                           author="PMC Managers Ltd")
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                   doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_footer)])

    story = _cover() + _toc(manifest)
    for step in manifest:
        story.extend(_step_page(step))

    doc.build(story)
    print(f"Written {OUT_PDF}  size={OUT_PDF.stat().st_size / 1024:.1f} KB · "
          f"{len(manifest)} screens")


if __name__ == "__main__":
    build()
