# PMC Managers v2 — Product Requirements & Roadmap

Last updated: 23 Feb 2026 — v45c LIVE ON PRODUCTION (DPR AI extraction verified end-to-end)

## Original Problem Statement
Global tender management platform (PMC Managers Limited v2) with full multi-role pipeline, dynamic Approval Matrices, Bidding & EMD, BOQ, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labeled AWS deployment.

## Production status (verified 23 Feb 2026)
- Frontend v45c: main.df887e6e.js on www.pmcmanagers.com (deployed via S3 console drag-drop)
- Backend v22i (WAF-safe flavor, SHA 0EA89170…) on pmc-backend-prod (EB console "Upload and deploy", label v22i-waf-fix)
- DPR AI extraction VERIFIED on prod: PDF → header + 5 section drafts + warnings in ~4.4s

## CRITICAL AWS LEARNINGS (do not forget)
1. **AWS WAF `SizeRestrictions_BODY`** on the CloudFront-attached web ACL blocks request bodies > 8 KB. Symptom: POST returns SPA index.html with HTTP 200 in <100ms. FIXED by setting the rule to Count in the ACL (CreatedByCloudFront… on E2WZT1TMQ0EK9W). If binary uploads ever fail again with fast HTML responses, check WAF first.
2. **CloudFront 404/403 → SPA fallback** masks missing backend routes: probe routes with unauthenticated calls (401 JSON = route exists; HTML = route missing).
3. **LLM key routing**: `sk-emergent-*` keys MUST go via https://integrations.emergentagent.com/llm; `sk-managed-*` via white-label proxy. Vendored pmc_lib only proxies sk-managed-. tender_pro.py has `_llm_complete()` handling both.
4. **requirements.txt freeze discipline**: pip installs without pip freeze don't reach EB Docker builds (pypdf incident).
5. **Windows deploys**: PS scripts need profile auto-detect + $LASTEXITCODE checks (PS 5.1 doesn't stop on native command failure). Console upload (EB "Upload and deploy" + S3 drag-drop) works without AWS CLI.

## v45/v45b/v45c — Delivered (all live on prod)
- Tender Pro: DPR batch upload (≤3) → AI header + section extraction → clone to draft
- AI Fill All sections, per-section save, auto tender-ref (PMC-{COUNTRY}-{IND}-{KIND}-{YY}-{SEQ})
- TenderFilterBar (search/country/industry/sort), dynamic covers
- EMD masters (country slabs, fixed/%), auto-prefill picker on Notice form
- Rating criteria master (Masters → Rating & Fees tab), multi-rater aggregate endpoints
- DPR warnings panel (modal + header banner)
- Save-as-master under country/industry

## Backlog
- P1: LSEG/Refinitiv KYC live integration (needs API keys)
- P1: OCR for scanned PDFs (current pypdf path needs text-layer PDFs)
- P2: WhatsApp/Telegram notifications, reverse auction rebuild
- P2: Bulk vendor rating grid UI (backend ready), bidder watchlist auto-flag <40/100
- P2: Turkish/Russian/Kazakh manual translations

## Architecture
- /app/backend — FastAPI + MongoDB; routers/tender_pro.py (v45)
- /app/frontend — React SPA; admin-console/tender/ (DprGenerateModal, TenderFilterBar), notice/EmdMasterPicker, masters/RatingCriteriaTab
- AWS: S3+CloudFront (frontend, dist E2WZT1TMQ0EK9W), EB Docker (backend, pmc-backend-prod, eu-west-2)
