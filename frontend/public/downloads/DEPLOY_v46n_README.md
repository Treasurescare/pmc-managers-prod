# PMC Managers — Deploy v46n (Per-section AI hotfix, cumulative on v46m)

## What broke

Every Tender Builder section has a ✨ **AI** button that opens a small
Tone/Length menu → "Draft with AI". In production this button silently
failed with a **503 "AI copilot not configured (missing LLM_API_KEY)"**.

**Root cause.** Four backend routes were still reading only the legacy
`LLM_API_KEY` / `LEGACY_LLM_KEY` environment variables. Production only
has **`EMERGENT_LLM_KEY`** set — same key that the DPR pipeline uses
successfully. The migration to the Universal Key had missed these
routes.

## Fix

Widened the env lookup to include `EMERGENT_LLM_KEY` on all four:

| File | Endpoint |
|---|---|
| `backend/routers/tender_templates.py` L640 | `POST /api/v1/tender-templates/{tid}/sections/{code}/ai-draft` — the ✨ per-section drafter |
| `backend/routers/analytics_helpers.py` L61 | `llm_narrative()` (bid workflow copilot) |
| `backend/routers/analytics_helpers.py` L99 | `anomaly_llm_narrative()` (auction anomaly detector) |
| `backend/routers/bids_ai_compare.py` L61 | `POST /api/v1/bids/compare-ai` (bid-pair redline) |

Each site now reads:

```python
key = (os.environ.get("LLM_API_KEY", "")
       or os.environ.get("EMERGENT_LLM_KEY", "")
       or os.environ.get("LEGACY_LLM_KEY", ""))
```

That is the same triad-lookup `tender_pro.py` already used for DPR
(hence DPR worked while ✨ AI did not).

## Deploy

```bash
eb deploy --staged --label v46n
```

No frontend build needed for this fix; the v46m frontend already ships
the correct client wiring (`tenderProApi` → `POST …/ai-draft`).

## Verify

1. Log in as admin.
2. Open Tender Builder, load any draft with sections.
3. Click the ✨ **AI** button on a section, pick Formal / Medium, hit
   **Draft with AI**.
4. Section body populates within 5–15 seconds; the button briefly shows
   `…` while working. If it fails, check `EMERGENT_LLM_KEY` is set in
   EB environment properties.
