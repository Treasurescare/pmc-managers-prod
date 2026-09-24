# PMC Managers — Deploy v46o (Per-section AI hotfix Round Two)

## Why v46n was not enough

v46n only widened the env-var lookup to include `EMERGENT_LLM_KEY`.  But
the `ai_draft_section` route also used **`pmc_lib.llm.chat.LlmChat`**,
which builds a plain OpenAI call — it has no code path to route the
`sk-emergent-*` key through the Emergent integrations proxy at
`https://integrations.emergentagent.com/llm`.  Result: the key was
found, but the LLM call still failed silently (or 502'd).

## What v46o changes

`backend/routers/tender_templates.py::ai_draft_section` **no longer uses
pmc_lib**.  It now delegates to `tender_pro._llm_complete`, the same
proven helper the DPR pipeline uses — which explicitly sets

```python
params["api_base"] = "https://integrations.emergentagent.com/llm"
```

for keys starting with `sk-emergent-*` and

```python
params["api_base"] = INTEGRATION_PROXY_URL + "/llm"
```

for keys starting with `sk-managed-*`.

That is why the DPR ingestion worked while the per-section drafter did
not, on the same key, in the same process.

## Sanity-tested locally

Logged in as admin, called
`POST /api/v1/tender-templates/{tid}/sections/{code}/ai-draft` on a
real master, got a valid HTML body back within a few seconds. Endpoint
returns 401 without auth and 403 without CSRF — both expected. With
cookie + CSRF the draft populates.

## Deploy

```bash
eb deploy --staged --label v46o
```

No frontend rebuild required — the client wiring has been correct all
along; only the server LLM routing was wrong.

## Verify

1. Log in as admin.
2. Open Tender Builder, load any draft with sections.
3. Click the ✨ **AI** button on a section, pick Formal / Medium,
   hit **Draft with AI**.
4. Body should populate in 5–15 s.  If not:
   * confirm `EMERGENT_LLM_KEY` is set in EB env (it should be, DPR
     depends on it too);
   * check the request in the browser Network tab — a 502 with
     `LLM call failed: ...` names the underlying LiteLLM error.
