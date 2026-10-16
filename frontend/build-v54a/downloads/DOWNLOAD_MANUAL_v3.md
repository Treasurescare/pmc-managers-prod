# PMC Manual v3 — Scrubbed Release

Manual v3 supersedes all v46p documents. Every reference to third-party
platform names has been removed; the AI layer is described neutrally as the
**Managed AI Gateway (universal LLM key)**. Verified programmatically:
**zero occurrences** of the removed terms in the extracted text of every PDF.

## Download links

| Document | Link | Pages | Size |
|---|---|---|---|
| **Master Training Manual v3 (PDF)** | [PMC_v3_Master_Training_Manual.pdf](./PMC_v3_Master_Training_Manual.pdf) | 151 | 9.4 MB |
| Master Training Manual v3 (DOCX) | [PMC_v3_Master_Training_Manual.docx](./PMC_v3_Master_Training_Manual.docx) | 151 | 8.2 MB |
| **Testing Manual v3** | [PMC_v3_Testing_Manual.pdf](./PMC_v3_Testing_Manual.pdf) | 33 | 130 KB |
| **Data Flow diagram v3** | [PMC_v3_Data_Flow.pdf](./PMC_v3_Data_Flow.pdf) · [.svg](./PMC_v3_Data_Flow.svg) | 1 (A3) | 42 KB |
| Process Flow diagram | [PMC_v46p_Process_Flow.pdf](./PMC_v46p_Process_Flow.pdf) · [.svg](./PMC_v46p_Process_Flow.svg) | 1 (A3) | 112 KB |

## What changed vs the previous edition

- 16 occurrences across 13 pages scrubbed in the Master Training Manual
  (architecture, governance, BCP, cybersecurity, risk-register chapters).
- AI copilot surfaces now described as "Managed AI Gateway / AI Gateway proxy"
  — no vendor brand names, no internal env-var names, no proxy hostnames.
- Testing Manual updated identically (regression notes now read "managed AI
  key" instead of naming the key family or endpoint).
- Data Flow diagram node renamed "AI Gateway (LLM Proxy)".
- The Process Flow diagram never contained the term (verified) and is carried
  over unchanged.

## Regenerate

```bash
python3 /app/tools/manual/build.py            # master manual (PDF + DOCX)
python3 /app/tools/manual/testing_manual.py   # testing manual (PDF)
python3 /app/tools/manual/data_flow.py        # data-flow diagram (PDF + SVG)
```

Old v46p manual files have been removed from `/downloads/` so nobody ships
the un-scrubbed edition by mistake.
