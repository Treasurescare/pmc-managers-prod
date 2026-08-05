# Stakeholder reports — Git-tracked snapshots

This folder holds the last snapshot of the "Asked vs Delivered" stakeholder
brief and the end-to-end platform flow chart, in five formats:

| File | Purpose |
|---|---|
| `PMC-v2-Asked-vs-Delivered.xlsx` | Row-per-scope-item, colour-coded by status. Best for edits. |
| `PMC-v2-Asked-vs-Delivered.docx` | Narrative Word doc — exec summary + comparison table + architecture guardrails. |
| `PMC-v2-Asked-vs-Delivered.pdf`  | A4-landscape boardroom handout (watermarked, page numbers). |
| `PMC-v2-Platform-Flowchart.svg`  | Vector flow chart (5 swim lanes) — infinitely scalable. |
| `PMC-v2-Platform-Flowchart.pdf`  | Same chart rendered A3-landscape for print/presentations. |

## Why these live in Git

The reports are generated on-demand by the backend
(`/api/v1/reports/comparative-statement.*` and `/api/v1/reports/flowchart.*`).
The endpoints stream files in memory only, so a plain **download** never
touches your repo.

To make the files visible in Git, run the snapshot from the admin console
(**Reports → Save snapshot to repo**) or hit the endpoint directly:

```bash
curl -X POST "$REACT_APP_BACKEND_URL/api/v1/reports/snapshot" \
     -H "Cookie: <your admin session cookie>"
```

The snapshot re-writes every file in this folder, then bump-commits them via
"Save to Github" in the chat input. `GENERATED_AT.txt` records the timestamp.

## Source of truth

The row data (Asked / Delivered / Notes) lives in
`backend/routers/reports.py` — variable `ROWS`. To change anything shown in
the exports, edit that list and re-snapshot.
