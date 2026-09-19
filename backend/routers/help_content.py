"""help_content.py — serves the manual content JSON to the in-app Help tab.

The frontend `<HelpPanel>` renders the same content authored in
`scripts/manual_content.py` — but rather than couple the frontend to a
Python file, we expose a lightweight endpoint that emits it as JSON.
"""
import sys
from pathlib import Path
from fastapi import APIRouter, Response

# Import from /app/scripts
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
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
