"""EMERGENCY TEMPORARY download endpoint — Bugs V2 Batch 2."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/api/v1/_dl", tags=["temp-downloads"])
TOKEN = "sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4"
ALLOWED = {
    "backend-v7-hardened":     "/app/pmc-backend-v7-hardened.zip",
    "backend-v10-waves-abcd":  "/app/pmc-backend-v10-waves-abcd.zip",
    "backend-v11-final":       "/app/pmc-backend-v11-final.zip",
    "frontend-v14-waves-abcd": "/app/pmc-frontend-v14-waves-abcd.zip",
    "frontend-v15-final":      "/app/pmc-frontend-v15-final.zip",
    "bug-tracker-v2":          "/app/deliverables/PMC_Bug_Tracker_v2.xlsx",
    "bug-tracker-v3":          "/app/deliverables/PMC_Bug_Tracker_v3.xlsx",
    "handbook-v3.1":           "/app/deliverables/PMC_Trainee_Handbook_v3.1.md",
}


@router.get("/{token}/{name}")
async def download(token: str, name: str):
    if token != TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    path = Path(ALLOWED.get(name, ""))
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    # Serve xlsx with correct MIME so browsers download rather than XML-render
    if str(path).endswith(".xlsx"):
        return FileResponse(str(path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name)
    if str(path).endswith(".md"):
        return FileResponse(str(path), media_type="text/markdown", filename=path.name)
    return FileResponse(str(path), media_type="application/zip", filename=path.name)


@router.get("/{token}")
async def index(token: str):
    if token != TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    files = "".join(
        f'<li><a href="/api/v1/_dl/{TOKEN}/{k}" download>{os.path.basename(v)} — {os.path.getsize(v)/1024:.1f} KB</a></li>'
        for k, v in ALLOWED.items() if os.path.exists(v))
    return HTMLResponse(f"""<!doctype html><html><head><title>PMC — Bugs V2 Batch 2 Downloads</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:3em auto;color:#1a2233;padding:0 1em}}
h1{{color:#0B2E4F}}li{{margin:1em 0;font-size:1.1em}}a{{color:#0B2E4F}}
.warn{{background:#fff8e6;border-left:4px solid #C89B3C;padding:12px 16px;font-size:.9em}}</style></head>
<body><h1>PMC — Bugs V2 Batch 2 Downloads</h1>
<p>Click each link to download the deployment zips.</p><ul>{files}</ul>
<div class="warn">🔒 Secret URL. Remove after use.</div></body></html>""")
