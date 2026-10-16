# PMC v46p — Deliverables README

Everything below is served from `/downloads/` on the deployed site and is also mirrored under `/app/deliverables/v46_manual/build/`.

## Files

| Artefact | Path | Pages | Size |
|---|---|---|---|
| **Master Training Manual (PDF)** | `PMC_v46p_Master_Training_Manual.pdf` | 151 | 9.4 MB |
| Master Training Manual (DOCX) | `PMC_v46p_Master_Training_Manual.docx` | 151 | 8.2 MB |
| **Testing Manual (PDF)** | `PMC_v46p_Testing_Manual.pdf` | 33 | 128 KB |
| **Process Flow (PDF)** | `PMC_v46p_Process_Flow.pdf` | 1 (A3) | 112 KB |
| Process Flow (SVG) | `PMC_v46p_Process_Flow.svg` | — | 23 KB |
| **Data Flow (PDF)** | `PMC_v46p_Data_Flow.pdf` | 1 (A3) | 42 KB |
| Data Flow (SVG) | `PMC_v46p_Data_Flow.svg` | — | 13 KB |

## Regenerate

```bash
# Re-capture screenshots (only after material UI changes)
python3 /app/tools/manual/capture.py

# Rebuild the master training manual (151-page PDF + DOCX)
python3 /app/tools/manual/build.py

# Rebuild the testing manual (per-module test cases)
python3 /app/tools/manual/testing_manual.py

# Rebuild the data-flow diagram
python3 /app/tools/manual/data_flow.py

# Rebuild the process-flow diagram
python3 -c "
import sys; sys.path.insert(0,'/app/backend')
from pathlib import Path
from routers.reports import _build_flowchart_svg, _flowchart_pdf_bytes
OUT = Path('/app/deliverables/v46_manual/build')
(OUT/'PMC_v46p_Process_Flow.svg').write_text(_build_flowchart_svg())
(OUT/'PMC_v46p_Process_Flow.pdf').write_bytes(_flowchart_pdf_bytes())
"
```

## PWA (v46p — new)

The frontend is now an installable Progressive Web App on Android + iOS.

| File | Purpose |
|---|---|
| `frontend/public/manifest.json` | 4 icons (192/512 · any + maskable), 4 launcher shortcuts, sovereign navy splash. |
| `frontend/public/service-worker.js` | Stale-while-revalidate app-shell cache. `/api/*` is **never** cached. Nukes older caches on activate. |
| `frontend/src/index.js` | Registers `/service-worker.js` after `window.load`. |
| `frontend/public/index.html` | Already carries the required `apple-mobile-web-app-*` meta tags for iOS. |

### Verify

```bash
curl -s https://<host>/manifest.json | jq .
curl -s -o /dev/null -w "%{http_code}\n" https://<host>/service-worker.js   # 200
```

On Android Chrome: address bar menu → *Install app*.
On iOS Safari 16.4+: Share → *Add to Home Screen*.

## What v46p contains

- 5-portal login (Admin, Management, Partners, Agents, Vendors) — sovereign navy + gold.
- Async unlimited DPR pipeline (200 MB / 500+ pages) with polling worker.
- Per-section AI drafter routed via Emergent LLM proxy.
- Bug Blitz Round Two shipped:
  1. Registration step gate (Section A → B/C/D/directors/E blocked until complete).
  2. Reports snapshot always returns valid JSON.
  3. Rubric max defensively vetoes keyboard / programmatic saves.
  4. Locked evaluations auto-load saved report + turn scoring read-only.
  5. Reverse-auction toolbar wraps cleanly on mobile (`flex-wrap gap-y-2`).
- PWA install support (Android + iOS).
- 151-page master training manual + 33-page testing manual + process + data flowcharts.
