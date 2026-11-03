"""Rebuild the master training manual appendix from the live help modules + video manifest.

Usage: python3 scripts/help_videos/manual_appendix.py
Keeps the original manual body in scripts/help_videos/manual_base.pdf and writes
frontend/public/downloads/manual/PMC_v4_Master_Training_Manual.pdf = base + "Appendix: Module guide & video index".
"""
import json
import os
import re
import shutil
from datetime import datetime, timezone

import dxpdf
import pymupdf
import requests
from docx import Document
from docx.shared import Pt, RGBColor

BASE_URL = os.environ["PMC_BASE"].rstrip("/")
SITE = "https://www.pmcmanagers.com"
HERE = os.path.dirname(__file__)
BASE_PDF = os.path.join(HERE, "manual_base.pdf")
LIVE = "/app/frontend/public/downloads/manual/PMC_v4_Master_Training_Manual.pdf"
MANIFEST = "/app/frontend/public/help-videos/manifest.json"
GREEN = RGBColor(0x16, 0x29, 0x21)


def clean(s):
    return re.sub(r"[*`]", "", s or "")


def main():
    if not os.path.exists(BASE_PDF):
        shutil.copy(LIVE, BASE_PDF)
    mods = requests.get(f"{BASE_URL}/api/v1/meta/help", timeout=30).json()["modules"]
    vids = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)
    h = doc.add_paragraph().add_run("Appendix — Module guide & video index")
    h.bold, h.font.size, h.font.color.rgb = True, Pt(22), GREEN
    doc.add_paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d} from the live help content. "
                      f"{len(mods)} modules · {len(vids)} with video walkthroughs.")
    for slug, m in mods.items():
        r = doc.add_paragraph().add_run(m["title"])
        r.bold, r.font.size, r.font.color.rgb = True, Pt(14), GREEN
        doc.add_paragraph(f"Where: {m['url_path']}   ·   Help page: {SITE}/help/{slug}")
        if slug in vids:
            doc.add_paragraph(f"Video ({vids[slug]['seconds']} s, updated {vids[slug]['updated']}): {SITE}{vids[slug]['file']}")
        doc.add_paragraph(clean(m["purpose"]))
        for a in m.get("actions", [])[:3]:
            doc.add_paragraph().add_run(clean(a["label"])).bold = True
            for st in a.get("steps", []):
                doc.add_paragraph(clean(st), style="List Number")
    tmp_docx, tmp_pdf = "/tmp/manual_appendix.docx", "/tmp/manual_appendix.pdf"
    doc.save(tmp_docx)
    dxpdf.convert_file(tmp_docx, tmp_pdf)
    out = pymupdf.open(BASE_PDF)
    out.insert_pdf(pymupdf.open(tmp_pdf))
    out.save(LIVE + ".tmp")
    os.replace(LIVE + ".tmp", LIVE)
    print("manual pages:", out.page_count)


if __name__ == "__main__":
    main()
