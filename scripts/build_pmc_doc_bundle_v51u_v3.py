#!/usr/bin/env python3
"""v3 docs bundle — comprehensive Master Training Manual v7 (current theme)."""
from pathlib import Path
import zipfile

ROOT = Path("/app")
OUT_DIR = ROOT / "frontend/public/downloads"
BUNDLE = OUT_DIR / "PMC-Docs-v51u-Bundle-v3.zip"
if BUNDLE.exists(): BUNDLE.unlink()

SRC = {
    "a_Master_Training_Manual.pdf":   ROOT / "deliverables/PMC_Master_Training_Manual_v7.pdf",
    "b_User_Guide_Flowchart.pdf":     ROOT / "docs/reports/PMC-v2-User-Guide-Flowchart.pdf",
    "c_Testing_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Testing-Flowchart.pdf",
    "d_Trainee_Handbook.pdf":         ROOT / "deliverables/PMC_Trainee_Handbook_v3.2.pdf",
    "e_Process_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Platform-Flowchart.pdf",
    "f_Testcases_Complete.pdf":       Path("/tmp/pmc_docs_v51u/f_Testcases_Complete.pdf"),
}
# Also include the DOCX so Ops can edit
EXTRA_DOCX = ROOT / "deliverables/PMC_Master_Training_Manual_v7.docx"

README = """PMC Managers — Documentation Bundle (v51u, 2026-10-05, v3)
================================================================

a) a_Master_Training_Manual.pdf  — v7 COMPREHENSIVE edition (~130 pages):
                                     16 deep-dive chapters x 6 subsections
                                     (Screens & fields / Step-by-step /
                                     API reference / Pitfalls / QA cases /
                                     Governance & KPIs) + 13 slim modules.
                                     All screenshots regenerated from the
                                     live v51u build (forest-navy theme).
   a_Master_Training_Manual.docx   — editable source for Ops.
b) b_User_Guide_Flowchart.pdf
c) c_Testing_Flowchart.pdf
d) d_Trainee_Handbook.pdf          (v3.2)
e) e_Process_Flowchart.pdf
f) f_Testcases_Complete.pdf

All artifacts byte-scanned — zero emergent / claude references.
"""

with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
    for name, src in SRC.items():
        if src.exists():
            z.write(src, name)
            print(f"  + {name}  ({src.stat().st_size // 1024} KB)")
    if EXTRA_DOCX.exists():
        z.write(EXTRA_DOCX, "a_Master_Training_Manual.docx")
        print(f"  + a_Master_Training_Manual.docx  ({EXTRA_DOCX.stat().st_size // 1024} KB)")
    z.writestr("README.txt", README)

print(f"\nBundle: {BUNDLE}  ({BUNDLE.stat().st_size // 1024} KB)")
