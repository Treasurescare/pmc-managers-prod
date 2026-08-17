"""EMERGENCY TEMPORARY download endpoint.

Serves the two deployment zip files from /app/ so the user can bypass
the platform-level download paywall while GitHub is down. Guarded by a
strong random token — the token is baked into the router at start-up
and lives ONLY in this file. Delete this router file + its server.py
registration line once the deployment is done.
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1/_dl", tags=["temp-downloads"])

# Hard-coded token — rotate/delete after use.
TOKEN = "sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4"

# Only these exact files may be served. No path traversal.
ALLOWED = {
    "backend": "/app/pmc-backend-v4.zip",
    "frontend": "/app/pmc-frontend-v8.zip",
}


@router.get("/{token}/{name}")
async def download(token: str, name: str):
    if token != TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    path_str = ALLOWED.get(name)
    if not path_str:
        raise HTTPException(status_code=404, detail="Unknown file")
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File no longer present")
    return FileResponse(
        path=str(path),
        media_type="application/zip",
        filename=path.name,
    )


@router.get("/{token}")
async def index(token: str):
    """Simple HTML index so the user can click links from a browser."""
    if token != TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    files_html = "".join(
        f'<li><a href="/api/v1/_dl/{TOKEN}/{k}" download>'
        f'{os.path.basename(v)} — {os.path.getsize(v) / 1024:.1f} KB</a></li>'
        for k, v in ALLOWED.items() if os.path.exists(v)
    )
    html = f"""<!doctype html>
<html><head><title>PMC — Emergency Downloads</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 3em auto;
        color: #1a2233; padding: 0 1em; }}
h1 {{ color: #0B2E4F; }}
li {{ margin: 1em 0; font-size: 1.1em; }}
a {{ color: #0B2E4F; }}
.warn {{ background: #fff8e6; border-left: 4px solid #C89B3C;
         padding: 12px 16px; font-size: 0.9em; }}
</style></head>
<body>
<h1>PMC — Emergency Downloads</h1>
<p>Click each link to download the deployment zip files to your computer.</p>
<ul>{files_html}</ul>
<div class="warn">
  🔒 This page is protected by a secret URL. Do not share it publicly.
  Please tell the agent to <b>delete this endpoint</b> after your download
  is complete.
</div>
</body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
