# PMC Managers v2 — Product Requirements & Roadmap

Last updated: 23 Sep 2026 — v46f DPR no-master workflow verified end-to-end (iteration_24, 100%); v46f frontend zip ready for user deploy; KMT DPR confirmed reading on production

## Original Problem Statement
Global tender management platform (PMC Managers Limited v2) with full multi-role pipeline, dynamic Approval Matrices, Bidding & EMD, BOQ, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labeled AWS deployment.

## Production status (verified 23 Sep 2026)
- Frontend v46e LIVE on pmcmanagers.com (main.ad632643.js). v46f zip ready (main.21ab3717.js) with editable name + real save-as-master persistence.
- **v46g backend NEW — DPR deep-dive (multi-pass). KMT PDF verified in preview: 26 sections discovered vs the old 5. Zip: /app/deliverables/v46c/pmc-backend-v46g.zip. AWAITING USER EB DEPLOY.**
- KMT DPR reads on prod (backend v46d, generic 5-section fallback until v46g deploys).
- Auth on prod confirmed working (cookie session, same-origin /api).

### Historical (Feb 2026)
- Frontend v45c: main.df887e6e.js on www.pmcmanagers.com (deployed via S3 console drag-drop)
- Backend v22i (WAF-safe flavor, SHA 0EA89170…) on pmc-backend-prod (EB console "Upload and deploy", label v22i-waf-fix)
- DPR AI extraction VERIFIED on prod: PDF → header + 5 section drafts + warnings in ~4.4s
- v46 rating portal — preview only, deployment deferred per user

## v46 — Vendor Ratings & Reviews portal (24 Feb 2026, preview)
User policy: reviewers = PMC management + verified peer vendors + public buyers. Reviewer identity = anonymous but verified. Backend/frontend both delivered and tested (24/24 backend pytest pass, all frontend UI flows verified).

New backend router `/api/v1/vendor-ratings/*`:
- `GET /public/rubric` — default rubric (public, no auth)
- `GET /public/top?limit=` — trust-badge listing for landing page
- `GET /public/{vendor_ref}` — anonymised aggregate + trust badge
- `POST /public/submit` — public buyer review (pending moderation, 3/email/day rate limit)
- `GET /directory` — vendor-scoped directory (peer directory for "Rate a vendor")
- `POST /peer/submit` — peer vendor rates another vendor (self-block, auto-approve if verified)
- `GET /peer/mine` — vendor's own reviews history
- `POST /admin/submit` — PMC admin scored review (auto-approved)
- `GET /admin/reviews?status=&vendor_ref=` — moderation list
- `POST /admin/reviews/{id}/moderate` — approve/hide
- `DELETE /admin/reviews/{id}` — permanent delete
- `GET /admin/pending-count` — for admin nav badge

New frontend:
- Landing "Trusted vendors" section (badge legend + top-rated cards)
- Public `/vendors/:ref` profile with badge, criteria averages, moderated comments, buyer review form
- Vendor Dashboard → new "Rate a vendor" tab (directory search, sliders, history)
- Admin Vendor-Intel → trust-badge column + full moderation panel (pending/approved/hidden/all + approve/hide/delete)
- New `VendorTrustBadge` component with Platinum/Gold/Silver/Bronze/None tiers

Trust badge thresholds (approved reviews only):
- Platinum: avg ≥ 85 AND count ≥ 10
- Gold: avg ≥ 70 AND count ≥ 5
- Silver: avg ≥ 55 AND count ≥ 3
- Bronze: count ≥ 1
- None: 0 approved

## CRITICAL AWS LEARNINGS (do not forget)
1. **AWS WAF `SizeRestrictions_BODY`** on the CloudFront-attached web ACL blocks request bodies > 8 KB. Symptom: POST returns SPA index.html with HTTP 200 in <100ms. FIXED by setting the rule to Count in the ACL (CreatedByCloudFront… on E2WZT1TMQ0EK9W). If binary uploads ever fail again with fast HTML responses, check WAF first.
2. **CloudFront 404/403 → SPA fallback** masks missing backend routes: probe routes with unauthenticated calls (401 JSON = route exists; HTML = route missing).
3. **LLM key routing**: `sk-emergent-*` keys MUST go via https://integrations.emergentagent.com/llm; `sk-managed-*` via white-label proxy. Vendored pmc_lib only proxies sk-managed-. tender_pro.py has `_llm_complete()` handling both.
4. **requirements.txt freeze discipline**: pip installs without pip freeze don't reach EB Docker builds (pypdf incident).
5. **Windows deploys**: PS scripts need profile auto-detect + $LASTEXITCODE checks (PS 5.1 doesn't stop on native command failure). Console upload (EB "Upload and deploy" + S3 drag-drop) works without AWS CLI.
6. **Public-facing pages must never depend on admin-scoped APIs** — silent 401s create dead-end UIs that pass visual QA but block the primary user action.

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
- P1: Public buyer email OTP verification (currently name+email only; moderation covers spam)
- P1: Trust badge threshold tuning after real-world data (currently 1 review = bronze — may want higher floor)
- P2: WhatsApp/Telegram notifications, reverse auction rebuild
- P2: Bulk vendor rating grid UI (backend ready), bidder watchlist auto-flag <40/100
- P2: Turkish/Russian/Kazakh manual translations
- P2: Refactor `tender_pro.py` into focused routers (DPR / references / fees / ratings) once P0 UX stable
- P2: `manualvendor` seed should flag `is_active=true` so verified peer reviews auto-publish in dev (currently pending)

## Architecture
- /app/backend — FastAPI + MongoDB; routers/tender_pro.py (v45) + routers/vendor_ratings.py (v46)
- /app/frontend — React SPA; admin-console/tender/ (DprGenerateModal, TenderFilterBar), notice/EmdMasterPicker, masters/RatingCriteriaTab, admin-console/vendor/ReviewModerationSection, shared/PublicVendorProfile, shared/TrustedVendorsSection, vendor-portal/RateAVendor, components/VendorTrustBadge
- AWS: S3+CloudFront (frontend, dist E2WZT1TMQ0EK9W), EB Docker (backend, pmc-backend-prod, eu-west-2)
