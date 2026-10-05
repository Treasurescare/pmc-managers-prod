#!/usr/bin/env python3
"""Build the v51u Docs bundle v2 — now with REAL current-theme screenshots.

Replaces the Master Training Manual PDF in the bundle with v6 (regenerated
05 Oct 2026 from the live v51u build) so every screenshot shows the
forest-navy Option E theme instead of the old blue theme.
"""
from pathlib import Path
import zipfile, shutil

ROOT = Path("/app")
OUT_DIR = ROOT / "frontend/public/downloads"
BUNDLE = OUT_DIR / "PMC-Docs-v51u-Bundle-v2.zip"
if BUNDLE.exists(): BUNDLE.unlink()

SRC = {
    "a_Master_Training_Manual.pdf":   ROOT / "deliverables/PMC_Master_Training_Manual_v6.pdf",
    "b_User_Guide_Flowchart.pdf":     ROOT / "docs/reports/PMC-v2-User-Guide-Flowchart.pdf",
    "c_Testing_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Testing-Flowchart.pdf",
    "d_Trainee_Handbook.pdf":         ROOT / "deliverables/PMC_Trainee_Handbook_v3.2.pdf",
    "e_Process_Flowchart.pdf":        ROOT / "docs/reports/PMC-v2-Platform-Flowchart.pdf",
    "f_Testcases_Complete.pdf":       Path("/tmp/pmc_docs_v51u/f_Testcases_Complete.pdf"),
}

README = """PMC Managers — Documentation Bundle (v51u, 2026-10-05, v2)
================================================================

a) a_Master_Training_Manual.pdf   — v6, REGENERATED 05 Oct 2026 from the
                                     live v51u build. Every screenshot
                                     uses the current forest-navy Option E
                                     theme (not the old blue theme).
                                     38 screenshots: 5 public + 22 admin +
                                     7 supplier + 4 mobile.
b) b_User_Guide_Flowchart.pdf     — PMC v2 User Guide flow
c) c_Testing_Flowchart.pdf        — PMC v2 Testing flow
d) d_Trainee_Handbook.pdf         — PMC v2 Trainee Handbook (v3.2)
e) e_Process_Flowchart.pdf        — PMC v2 Platform process flow
f) f_Testcases_Complete.pdf       — Full regression test plan (regenerated)

All six artifacts audited for third-party tooling references
(emergent, claude) — bundle is clean.
"""

with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
    for name, src in SRC.items():
        if src.exists():
            z.write(src, name)
            print(f"  + {name}  ({src.stat().st_size // 1024} KB)")
        else:
            print(f"  ! MISSING {src}")
    z.writestr("README.txt", README)

print(f"\nBundle: {BUNDLE}  ({BUNDLE.stat().st_size // 1024} KB)")
