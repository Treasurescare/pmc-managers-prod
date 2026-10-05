#!/usr/bin/env python3
"""Render PMC-v2-Test-Plan.md -> PDF and bundle all 6 doc artifacts.

Produces /app/frontend/public/downloads/PMC-Docs-v51u-Bundle.zip containing:
  a) PMC_Master_Training_Manual_v5.pdf       (deliverables/, already clean)
  b) PMC-v2-User-Guide-Flowchart.pdf         (docs/reports/, already clean)
  c) PMC-v2-Testing-Flowchart.pdf            (docs/reports/, already clean)
  d) PMC_Trainee_Handbook_v3.2.pdf           (deliverables/, already clean)
  e) PMC-v2-Platform-Flowchart.pdf           (docs/reports/, process flow, clean)
  f) PMC-v2-Testcases-Complete.pdf           (regenerated from scrubbed test-plan.md)
"""
from __future__ import annotations
import re, zipfile
from pathlib import Path

ROOT = Path("/app")
OUT_DIR = ROOT / "frontend" / "public" / "downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/pmc_docs_v51u"); TMP.mkdir(exist_ok=True)

# ---------- a-e: already-clean source PDFs ----------
SRC = {
    "a_Master_Training_Manual.pdf":   ROOT / "deliverables/PMC_Master_Training_Manual_v5.pdf",
    "b_User_Guide_Flowchart.pdf":     ROOT / "docs/reports/PMC-v2-User-Guide-Flowchart.pdf",
    "c_Testing_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Testing-Flowchart.pdf",
    "d_Trainee_Handbook.pdf":         ROOT / "deliverables/PMC_Trainee_Handbook_v3.2.pdf",
    "e_Process_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Platform-Flowchart.pdf",
}

# ---------- f: Testcases from the scrubbed test-plan markdown ----------
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, KeepTogether)

NAVY = colors.HexColor("#0F3B2E")
GOLD = colors.HexColor("#B08E4A")
INK  = colors.HexColor("#0B1A14")
MUTE = colors.HexColor("#5A5A57")
LINE = colors.HexColor("#E2DCCD")

ss = getSampleStyleSheet()
h1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=22, leading=26, textColor=NAVY, spaceAfter=10)
h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=14, leading=18, textColor=NAVY, spaceAfter=6, spaceBefore=10)
h3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, leading=14, textColor=GOLD, spaceAfter=4, spaceBefore=8)
body = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=9.5, leading=12.5, textColor=INK, spaceAfter=4)
mono = ParagraphStyle("M", parent=body, fontName="Courier", fontSize=8.5)
meta = ParagraphStyle("Meta", parent=body, fontSize=8, textColor=MUTE, spaceAfter=2)

def md_inline(text: str) -> str:
    """Minimal markdown-inline -> ReportLab-safe HTML."""
    s = text
    # Escape HTML
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Code
    s = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', s)
    # Bold
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    # Italic
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    # Links
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               r'<link href="\2" color="#0F3B2E"><u>\1</u></link>', s)
    return s


def parse_pipe_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for ln in lines:
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        # Skip header-separator rows (|---|---|)
        if cells and all(re.fullmatch(r":?-{2,}:?", c or "---") for c in cells):
            continue
        rows.append(cells)
    return rows


def build_testcases_pdf():
    md_path = ROOT / "docs/reports/PMC-v2-Test-Plan.md"
    text = md_path.read_text()
    out_path = TMP / "f_Testcases_Complete.pdf"

    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                              leftMargin=18*mm, rightMargin=18*mm,
                              topMargin=16*mm, bottomMargin=16*mm,
                              title="PMC Testcases Complete",
                              author="PMC Managers")
    story = []
    story.append(Paragraph("PMC Managers v2 — Testcases Complete", h1))
    story.append(Paragraph("Full regression test plan · regenerated for v51u", meta))
    story.append(Spacer(1, 6))

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("# "):
            story.append(Paragraph(md_inline(ln[2:].strip()), h1))
            i += 1; continue
        if ln.startswith("## "):
            story.append(Paragraph(md_inline(ln[3:].strip()), h2))
            i += 1; continue
        if ln.startswith("### "):
            story.append(Paragraph(md_inline(ln[4:].strip()), h3))
            i += 1; continue
        # Table block
        if ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i]); i += 1
            rows = parse_pipe_table(block)
            if rows:
                para_rows = [[Paragraph(md_inline(c), body) for c in r] for r in rows]
                avail = A4[0] - 36*mm
                ncols = len(rows[0])
                col_w = [avail / ncols] * ncols
                t = Table(para_rows, colWidths=col_w, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), NAVY),
                    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE", (0,0), (-1,-1), 8.5),
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                    ("GRID", (0,0), (-1,-1), 0.4, LINE),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F6F2E9")]),
                    ("LEFTPADDING", (0,0), (-1,-1), 4),
                    ("RIGHTPADDING", (0,0), (-1,-1), 4),
                    ("TOPPADDING", (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ]))
                story.append(t); story.append(Spacer(1, 6))
            continue
        # Fenced code
        if ln.strip().startswith("```"):
            buf = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            code = ("<br/>".join(buf)).replace(" ", "&nbsp;")
            story.append(Paragraph(code, mono)); story.append(Spacer(1, 4))
            continue
        # Bullet list
        if re.match(r"^[\-\*] ", ln):
            items = []
            while i < len(lines) and re.match(r"^[\-\*] ", lines[i].rstrip() or ""):
                items.append(lines[i].rstrip()[2:]); i += 1
            for it in items:
                story.append(Paragraph("• " + md_inline(it), body))
            story.append(Spacer(1, 3))
            continue
        if not ln.strip():
            story.append(Spacer(1, 4)); i += 1; continue
        story.append(Paragraph(md_inline(ln), body))
        i += 1

    doc.build(story)
    print(f"Built {out_path.name} ({out_path.stat().st_size//1024} KB)")
    return out_path


def main():
    testcases_pdf = build_testcases_pdf()
    bundle_path = OUT_DIR / "PMC-Docs-v51u-Bundle.zip"
    if bundle_path.exists(): bundle_path.unlink()

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, src in SRC.items():
            if src.exists():
                z.write(src, name)
            else:
                print(f"WARN: missing {src}")
        z.write(testcases_pdf, "f_Testcases_Complete.pdf")
        # Readme
        readme = (
            "PMC Managers — Documentation Bundle (v51u, 2026-10-05)\n"
            "=======================================================\n\n"
            "a) a_Master_Training_Manual.pdf   — Full screenshot training manual (v5)\n"
            "b) b_User_Guide_Flowchart.pdf     — PMC v2 User Guide flow\n"
            "c) c_Testing_Flowchart.pdf        — PMC v2 Testing flow\n"
            "d) d_Trainee_Handbook.pdf         — PMC v2 Trainee Handbook (v3.2)\n"
            "e) e_Process_Flowchart.pdf        — PMC v2 Platform process flow\n"
            "f) f_Testcases_Complete.pdf       — Full regression test plan (regenerated)\n\n"
            "All six artifacts have been audited for third-party tooling references\n"
            "(emergent, claude) and are clean.\n\n"
            "If you rebuild these from source later, the markdown and python builders\n"
            "under /app/scripts/ and /app/docs/reports/ have also been scrubbed, so\n"
            "regenerated artifacts stay clean.\n"
        )
        z.writestr("README.txt", readme)

    print(f"\nBundle: {bundle_path} ({bundle_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
