"""help_content.py — serves the manual content JSON to the in-app Help tab.

The frontend `<HelpPanel>` renders the same content authored in
`backend/pmc_lib/help_content_data.py` (mirrored from `scripts/manual_content.py`
for local development). Router prefers the in-package copy so the Elastic
Beanstalk archive — which only ships `backend/` — never ends up with an empty
`MODULES` and a blank Help tab in production (bug reported v46p).
"""
import sys
from pathlib import Path
from fastapi import APIRouter, Response

MODULES: dict = {}
# 1. Prefer in-package copy (survives every backend-only deployment).
try:
    from pmc_lib.help_content_data import MODULES  # type: ignore
except Exception:
    # 2. Fall back to /app/scripts for dev workstations that still edit there.
    _SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
    if _SCRIPTS.exists():
        sys.path.insert(0, str(_SCRIPTS))
        try:
            from manual_content import MODULES  # type: ignore
        except Exception:
            MODULES = {}

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/help")
async def help_content(response: Response):
    """Return the manual content used by the admin Help tab."""
    response.headers["Cache-Control"] = "public, max-age=300"
    out = {}
    for code, m in MODULES.items():
        out[code] = {
            "title":         m.get("title"),
            "surface":       m.get("surface"),
            "url_path":      m.get("url_path"),
            "purpose":       m.get("purpose"),
            "prerequisites": m.get("prerequisites", []),
            "actions":       m.get("actions", []),
        }
    return {"version": "v1", "modules": out}
