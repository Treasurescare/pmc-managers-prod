"""
PMC Managers v2 — Comprehensive User Manual · complete content model
====================================================================
Mirrored from backend/pmc_lib/help_content_data.py for local script tooling.
"""
from pathlib import Path
import sys

# Reference backend module directly
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
from pmc_lib.help_content_data import MODULES, list_modules, to_json_export

if __name__ == "__main__":
    print(f"Total modules: {len(MODULES)}")
    for code, m in MODULES.items():
        actions = len(m.get("actions") or [])
        marker = "✓" if actions else "…"
        print(f"  {marker} {code:24} · {m['title']:30} · {actions} actions authored")
