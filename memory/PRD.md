# PMC Managers v2 — Product Requirements & Roadmap

Last updated: 22 Feb 2026 — v45 preview (Tender Pro: AI DPR, filters, EMD & rating masters)

## Original Problem Statement
Global tender management platform (PMC Managers Limited v2) with full multi-role pipeline, dynamic Approval Matrices, Bidding & EMD, BOQ, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labeled AWS deployment.

## v45 — Preview (22 Feb 2026) — 4-phase Tender Pro release
Meeting-note-driven Tender Builder overhaul. All backend curl-verified on preview, UI wired.

### Phase C — AI DPR & full-doc generation
- `POST /api/v1/tender-pro/dpr/analyze` — upload PDF/DOCX/TXT, LLM extracts header + section bodies (JSON, non-persistent preview).
- `POST /api/v1/tender-pro/templates/{tid}/ai-fill-all` — one-shot AI draft for every empty section (`only_empty=True` by default) — audit-logged.
- Frontend: `DprGenerateModal` + `✨ AI Fill All` button on the header bar.

### Phase A — Filters, per-section save, auto tender-ref, dynamic covers
- `POST /api/v1/tender-pro/next-reference?country=KZ&industry=Construction&kind=rfp` → `PMC-KZ-CONS-RFP-26-00001` (per-country/kind Mongo sequence).
- `PATCH /api/v1/tender-pro/templates/{tid}/sections/{code}` — save one section without bumping the versions array.
- `TenderFilterBar` (search / country / industry / sort A-Z, Z-A, date) client-side filter on drafts.
- Dynamic covers already synced to `no_of_covers` in TenderHeaderForm.

### Phase B — Country templates, save-as-master, EMD master
- New `country` field on templates, `POST /api/v1/tender-pro/templates/{tid}/save-as-master` promotes a working draft into the master library under (country, industry).
- `emd_masters` collection with CRUD + `POST /emd-masters/compute` — country-scoped fee slabs, fixed OR percentage, with tender-value ranges (verified: fixed at 50k below 10M, 2% above → 1M on 50M).

### Phase D — Vendor rating criteria + multi-rater aggregate
- `rating_criteria_sets` CRUD (15-30 criteria, weights, scale min/max, is_default flag auto-uniqued).
- `POST /api/v1/tender-pro/ratings/multi` — per-criterion scores with rater type (admin/vendor/platform), auto-normalised to a 0-100 weighted score.
- `GET /api/v1/tender-pro/ratings/aggregate/{vendor_ref}` — aggregate across all raters.

### What's LIVE now (curl-verified on preview)
- next-reference → `PMC-KZ-CONS-RFP-26-00001`
- EMD master create + list + compute (fixed & percentage slabs)
- rating criteria create with default flag + aggregate endpoint

### Not yet in v45 (deferred to v46+)
- LSEG/Refinitiv KYC live integration (needs API keys)
- WhatsApp/WeChat/Telegram notifications
- Reverse auction rebuild
- Full multi-rater vendor blind rating UI (backend ready; UI is minimal)
- Country-first clone flow (backend accepts, UI still uses simple industry hint)

## v44 — LIVE on preview only (needs prod deploy)
- Vendor admin panel: inline Activate Now, auto-scroll + emerald ring highlight.
- Registration flow: Directors & Beneficial Owners tab (dynamic rows, EN/RU/KK).
- `POST /api/v1/vendors/{ref}/activate` (resend_link + set_password modes).
- v22h backend zip + v44b frontend zip both built and downloadable from preview URL.

## v43 — Production status (19 Feb 2026)
- Frontend `main.ac7e71b2.js` on `www.pmcmanagers.com`; backend `v22g-clean` on `pmc-backend-prod`.
- InfoDot tooltips across 26 admin panels + showApiError() global loud toasts.
- 32-shot per-modal User Manual v43 shipped.

## Backlog / follow-ups
- **P1 · v44 redeploy**: `pmc-frontend-v44b-build.zip` fixes prod backend URL — user hit truncated-download earlier; new slim 5.6 MB build ready with SHA `e8185592…`.
- **P2 · v44 backend**: `pmc-backend-v22h.zip` (SHA `a40a2621…`) — adds Activate Now endpoint.
- **P2 · v45 packaging**: not yet packaged for AWS — new endpoints + UI are on preview only.
- Static prod data: joint escrow account #1 still needs distinct officer email (manual DB edit).
- Route 53 SOA TTL 86400 → 60 (optional).

## Architecture
- `/app/backend` — FastAPI + MongoDB; new router `tender_pro.py` (v45).
- `/app/frontend` — React SPA; new components under `admin-console/tender/` (DprGenerateModal, TenderFilterBar).
- AWS: S3 + CloudFront (frontend), Elastic Beanstalk Docker (backend).
