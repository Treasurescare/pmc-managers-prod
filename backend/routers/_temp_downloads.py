"""EMERGENCY TEMPORARY download endpoint — Bugs V2 Batch 2."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/api/v1/_dl", tags=["temp-downloads"])
TOKEN = "sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4"
ALLOWED = {
    "backend-v11-final":       "/app/pmc-backend-v11-final.zip",
    "backend-v12-bucketA":     "/app/pmc-backend-v12-bucketA.zip",
    "backend-v13-bucketB":     "/app/pmc-backend-v13-bucketB.zip",
    "frontend-v15-final":      "/app/pmc-frontend-v15-final.zip",
    "frontend-v16-bucketA":    "/app/pmc-frontend-v16-bucketA.zip",
    "bug-tracker-v3":          "/app/deliverables/PMC_Bug_Tracker_v3.xlsx",
    "bug-tracker-v4":          "/app/deliverables/PMC_Bug_Tracker_v4.xlsx",
    "bug-tracker-v5":          "/app/deliverables/PMC_Bug_Tracker_v5.xlsx",

    # Process manuals + flowcharts (regenerated on every startup snapshot)
    "process-flowchart-pdf":   "/app/docs/reports/PMC-v2-Platform-Flowchart.pdf",
    "process-flowchart-svg":   "/app/docs/reports/PMC-v2-Platform-Flowchart.svg",
    "user-guide-flowchart-pdf":"/app/docs/reports/PMC-v2-User-Guide-Flowchart.pdf",
    "user-guide-flowchart-svg":"/app/docs/reports/PMC-v2-User-Guide-Flowchart.svg",
    "testing-flowchart-pdf":   "/app/docs/reports/PMC-v2-Testing-Flowchart.pdf",
    "testing-flowchart-svg":   "/app/docs/reports/PMC-v2-Testing-Flowchart.svg",
    "process-manual-pdf":      "/app/docs/reports/PMC-v2-Asked-vs-Delivered.pdf",
    "process-manual-docx":     "/app/docs/reports/PMC-v2-Asked-vs-Delivered.docx",
    "process-manual-xlsx":     "/app/docs/reports/PMC-v2-Asked-vs-Delivered.xlsx",
    "observations-tracker":    "/app/deliverables/PMC_Observations_Tracker_v1.xlsx",
    "observations-response-v2":"/app/deliverables/PMC_Portal_Observations_Response_v2.docx",
    "observations-response-v3":"/app/deliverables/PMC_Portal_Observations_Response_v3.docx",
    "observations-response-v4":"/app/deliverables/PMC_Portal_Observations_Response_v4.docx",
    "observations-response-v5":"/app/deliverables/PMC_Portal_Observations_Response_v5.docx",
    "handbook-v3.2-docx":      "/app/deliverables/PMC_Trainee_Handbook_v3.2.docx",
    "handbook-v3.2-pdf":       "/app/deliverables/PMC_Trainee_Handbook_v3.2.pdf",
    "handbook-v3.2-md":        "/app/deliverables/PMC_Trainee_Handbook_v3.2.md",
    "screenshot-manual":       "/app/deliverables/PMC_Screenshot_Training_Manual_v1.pdf",
    "screenshot-manual-docx":  "/app/deliverables/PMC_Screenshot_Training_Manual_v1.docx",
    "master-manual-docx":      "/app/deliverables/PMC_Master_Training_Manual_v1.docx",
    "master-manual-pdf":       "/app/deliverables/PMC_Master_Training_Manual_v1.pdf",
    "master-manual-v2-docx":   "/app/deliverables/PMC_Master_Training_Manual_v2.docx",
    "master-manual-v2-pdf":    "/app/deliverables/PMC_Master_Training_Manual_v2.pdf",
    "backend-v16":             "/app/pmc-backend-v16.zip",
    "backend-v17":             "/app/pmc-backend-v17.zip",
    "backend-v15":             "/app/pmc-backend-v15.zip",
    "frontend-v18":            "/app/pmc-frontend-v18.zip",
    "frontend-v19":            "/app/pmc-frontend-v19.zip",
    "frontend-v20":            "/app/pmc-frontend-v20.zip",
    "backend-v14":             "/app/pmc-backend-v14.zip",
    "frontend-v17":            "/app/pmc-frontend-v17.zip",
    "handbook-v3.1-docx":      "/app/deliverables/PMC_Trainee_Handbook_v3.1.docx",
    "handbook-v3.1-pdf":       "/app/deliverables/PMC_Trainee_Handbook_v3.1.pdf",
    "bugs-response-xlsx":      "/app/deliverables/PMC_Bugs_Response_v1.xlsx",
    "bugs-response-docx":      "/app/deliverables/PMC_Bugs_Screenshots_V6_with_Responses.docx",
    "master-manual-v3-docx":   "/app/deliverables/PMC_Master_Training_Manual_v3.docx",
    "master-manual-v3-pdf":    "/app/deliverables/PMC_Master_Training_Manual_v3.pdf",
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
    if str(path).endswith(".docx"):
        return FileResponse(str(path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=path.name)
    if str(path).endswith(".md"):
        return FileResponse(str(path), media_type="text/markdown", filename=path.name)
    if str(path).endswith(".pdf"):
        return FileResponse(str(path), media_type="application/pdf", filename=path.name)
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
