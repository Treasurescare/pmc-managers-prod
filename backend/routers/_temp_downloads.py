"""EMERGENCY TEMPORARY download endpoint — Bugs V2 Batch 2."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/api/v1/_dl", tags=["temp-downloads"])
TOKEN = "sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4"
ALLOWED = {
    "backend-v6":              "/app/pmc-backend-v6.zip",
    "backend-v7-hardened":     "/app/pmc-backend-v7-hardened.zip",
    "backend-v7.1-mongo-guard":"/app/pmc-backend-v7.1-mongo-guard.zip",
    "backend-v8-bug5-fix":     "/app/pmc-backend-v8-bug5-fix.zip",
    "frontend-v11":            "/app/pmc-frontend-v11.zip",
    "frontend-v12-bug5-fix":   "/app/pmc-frontend-v12-bug5-fix.zip",
}


@router.get("/{token}/{name}")
async def download(token: str, name: str):
    if token != TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    path = Path(ALLOWED.get(name, ""))
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
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
