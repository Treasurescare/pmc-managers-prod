# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform. Multi-role approval pipeline, dynamic
Approval Matrices, Bidding & EMD payments, BOQ, Evaluations, Contract Award, MFA,
Multi-Tenant portals, AI Audit Copilot, KYC integration. Built "for Portability" —
Emergent MVP now, AWS Phase 2 later; also shipped as PWA + Capacitor mobile app.

## User Personas
- **Master Admin** — full RBAC.
- **Staff** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — self-registers OR admin-invited (magic email, CSV bulk, or **full form fill-in on behalf**).
- **External Committee Invitee** — non-staff experts invited by email.

## Core Modules
- **Wave 1-13** (previous waves) — Auth, Bidding + EMD, Evaluations, BOQ, Contracts, Vendor Intel, Analytics, MFA, Tenants, GDPR, Workflow Matrix, AI Copilot, Permissions Matrix, KYC-Checks client, Registration docs, Mobile PWA + Capacitor scaffold, Unified mobile login `/m`
- **Wave 14 (Prod-parity)** — Fixed `admin@pmcmanagers.com` legacy default in `config.py` (now `adminsupport@pmcmanagers.com`), deleted stale `backend/tests/backend_test.py`, added self-heal endpoint `POST /api/v1/admin/heal/rename-admin` for prod cleanup, added **Unified web login `/login`** (same auto-detect as mobile `/m`), added **Admin creates vendor with full Sections A–E form** at `/admin/vendors/new` with two modes (`activate` immediately with admin-set password OR `verify` via magic-link email). Vendors panel gains "Add & fill full form" button.

## Roadmap

### P0 — Verified this session ✅
- **Wave 38 (Quote pipeline — 2026-08-05)** — new `engagements` router + `EngagementsPanel.jsx`. Every "Request quote" click from `/services` and `/vendor/services` creates a persistent engagement (quote_requested → quoted → invoiced → paid, or cancelled). Admin sets amount + currency, generates a Stripe pay-link in one click. Full audit trail on every transition. End-to-end verified: $40k Strategic Advisory engagement created anon, quoted by admin, `cs_test_...` Stripe URL issued.
- **Refactor wave (2026-08-05)** — `EscrowPanel.jsx` split 303→36 lines with two new components (`escrow/EscrowAccountsSection.jsx`, `escrow/EscrowTransactionsSection.jsx`); `award_report()` in `evaluations.py` decomposed into 4 pure helpers (`_load_rubric_config`, `_pct_technical`, `_pct_commercial`, `_group_scores_by_bid`, `_bid_row`) — main handler down to ~25 lines. `PurchaseGrid.jsx` quote-request handler now hits the real engagements endpoint instead of a client-side toast + audit stub.
- **Wave 35f (Reports refresh — 2026-08-05)** — regenerated all 5 stakeholder artefacts against the current 44-row wave table (38 delivered / 1 partial / 5 planned). Updated flowchart adds a full Revenue lane (Product Catalog · Client & Supplier purchase · Stripe Checkout · Webhook/Ledger · Quote→Engagement) and expands the Escrow lane with the magic-link portal. Files in `/app/docs/reports/` — all validated by magic-byte sniff.
- **Wave 36/37 (Client + Supplier Purchase Surfaces — 2026-08-05)** — public price pages driven by the catalog. New shared `PurchaseGrid` component (category filter, price display per pricing_model, quote-vs-subscribe CTA). Routes `/services` (client, 34 products) + `/vendor/services` (supplier, 21 products). Checkout endpoint relaxed to accept admin, vendor OR anonymous auth (server still owns the price). Stripe redirect handled by `/billing/success` + `/billing/cancel` with 2-sec polling until webhook confirms. Verified: anon checkout for Silver ($8,000 USD) returned a real Stripe URL.
- **Escrow Magic-Link (Wave 35b — 2026-08-05)** — new endpoints on `escrow.py`: `POST /magic-tokens` (admin issues token for one officer of one joint account), `GET /magic/{token}` (public, returns pending txs), `POST /magic/{token}/sign` (public, signs a tx without a full staff account). Frontend `/escrow/officer/:token` shows a per-tx sign form; dual-signature rule still enforced downstream. `escrow_magic_tokens` collection stores per-token metadata; revocable.
- **Live Roadmap Page (Wave 35c — 2026-08-05)** — public `/roadmap` reads `GET /api/v1/reports/public/roadmap` (no auth) — 36 tracked scope items grouped into 20 areas with status pills (Delivered/Partial/Planned). Vendors can now watch the roadmap live. Stat cards toggle-filter by status.
- **KYC Pre-Bid Gate (Wave 35d — 2026-08-05)** — `bids.py` `create_bid()` now returns HTTP 412 unless the vendor has a passing KYC decision (`kyc.status ∈ {verified, cleared, passed}` OR a `kyc_cases` row with `status=passed`). Notice-level `kyc_bypass=true` overrides. Prevents unverified vendors from wasting EMD.
- **Auto-Snapshot On Change (Wave 35e — 2026-08-05)** — every backend startup regenerates all 5 stakeholder-report files into `/app/docs/reports/`. So every deploy carries the current wave-row set. Wrapped in try/except so a snapshot failure never blocks startup.
- **Wave 35 (Product Catalog + Stripe billing — 2026-08-05)** — admin-managed master of every revenue line from CA-02 (client) + CA-03 (supplier). 55 default products seeded (34 client + 21 supplier), pricing models: fixed / range / % / monthly / annual / per-delegate / per-user-monthly / cost-recovery / package. All amounts admin-editable. Multi-currency (USD/GBP/EUR/KZT/INR/AED/SAR). New `products.py` router (CRUD + public list + reseed + `/categories`). New `billing.py` router — Stripe Checkout via `emergentintegrations` (Flow B, `sk_test_emergent`) with server-authoritative pricing; endpoint drops `payment_transactions` row before redirect. `POST /api/webhook/stripe` idempotent. New admin **Product Catalog** tab with filter/sort/edit modal (`ProductCatalogPanel.jsx`). Verified: curl checkout returned `cs_test_a1wco9zk…` Stripe URL for $3000 Bronze package. Also **PDF placeholder fix**: `notices.py` upload endpoint now rejects files < 200 bytes and enforces magic-byte match; `POST /api/v1/notices/admin/cleanup-bogus-documents` detaches existing bogus PDFs; `NoticeDetail.jsx` shows an amber "Placeholder file" badge when a primary_document is < 200 bytes so users no longer click into broken PDFs.
- **Wave 34 (Snapshot reports to Git — 2026-08-05)** — `reports.py` now exposes `snapshot_to_disk()` + `POST /api/v1/reports/snapshot` (admin-only). Writes all 5 artefacts (`PMC-v2-Asked-vs-Delivered.{xlsx,docx,pdf}`, `PMC-v2-Platform-Flowchart.{svg,pdf}`) + `GENERATED_AT.txt` into `/app/docs/reports/` so the next "Save to Github" carries them. `ReportsPanel.jsx` gains a **Save snapshot to repo** button with per-file result listing. `docs/reports/README.md` explains the flow. Verified: files written (10 KB → 62 KB range), git shows `?? docs/reports/`, endpoint returns 401 to anon (admin-gated).
- **Wave 32 (Joint Escrow ledger — 2026-08-03)** — implements user's EMD governance model:
  - EMD is held in a **JOINT escrow account** with two named officers: one from PMC, one from the escrow institution. Admin picks the account details.
  - New router `/api/v1/escrow/*`:
    - `POST/GET/PATCH /accounts` — admin creates & manages joint accounts (institution, IBAN, SWIFT, currency, two officer records).
    - `POST /transactions/init` — Accounting records an inbound EMD receipt against an active account (snapshots the officers so later account edits don't rewrite history).
    - `POST /transactions/{tid}/sign` — one officer signs off on an intended action. Officer side (`pmc` vs `escrow_institution`) is inferred from the account snapshot, so an admin can't accidentally sign as the wrong side.
    - `POST /transactions/{tid}/release` — dual-signature gated. Won't fire unless both officers have signed the **same** action (`release_to_contractor` / `release_to_vendor` / `forfeit`). Returns 409 otherwise.
    - Immutable `audit_trail[]` on each tx + global `audit_log` entries.
  - New admin tab `Escrow (EMD)` with the whole flow: joint-account form, ledger of transactions, per-officer sign buttons, gated Release button that only unlocks after both officers signed the same action.
  - **Verified via curl**: created account, recorded 25 000 USD inbound EMD, tried to release with zero signatures → **HTTP 409**; then PMC-officer signed → status flipped to `awaiting_signatures` with `signed_by_pmc` audit entry.
- **Wave 31 (four backlog features — 2026-08-03)**:
  - **Version History**: rolling 20-snapshot list on every save (`versions[]` on the template), `GET /versions` + `POST /versions/{i}/restore`. Restore itself is auto-snapshotted (undoable). New `VersionHistory` drawer in Tender Builder header (`⟲ History · v{n}`).
  - **Bidder Q&A**: new router `notice_qa` with public POST question / GET answered + admin listAll / reply. Email of the asker is masked in public output (`a***@company.com`). New `NoticeQa` component on the public Notice page. EmailStr swapped for regex validation to accept `.test` TLDs used in staging.
  - **AI Redline Comparison**: `POST /api/v1/bids/compare-ai` returns structured JSON (`summary`, `clauses[]`, `recommended_questions[]`, `advisory_notice`). Explicitly refuses to rank a winner — advisory only, human retains signature. Verified: 9 clauses + 5 questions on a synthetic Bid A vs Bid B run.
  - **Multi-language PDF**: `?lang=en|ru|kk` on `/export/pdf` and `/public/pdf`. Full I18N dict for section-kind labels, page footer, DRAFT watermark, issuance stamp + a per-language advisory notice. RU render confirmed via pypdf: contains "ЧЕРНОВИК" + "Стр." Notice detail now exposes three per-language PDF buttons.
  - `diff@9.0.0` frozen; NoticeQa lint warning fixed with `useCallback`.
- **Architecture guardrails captured** from user 2026-08-03:
  - EMD → direct-to-escrow with dual-officer joint-account control (Wave 32).
  - KYC must gate bidding (P1 — see roadmap).
  - Technical / commercial evaluations kept segregated with per-stage authority (P1 — evaluation module already segregates rubric scores; needs role-firewall audit).
  - AI stays advisory. All substantive decisions remain attributable to authorised individuals and fully auditable (enforced in `compare-ai` and `ai-draft` — no automated actions).
- **Wave 30 (Tender Builder v4 — 2026-08-03)** — the previous 4 backlog items shipped:
  1. **Section Diff Viewer** — `diff@9` word-level diffs with red-strike / green-highlight; the `AiDiffModal` appears whenever AI is re-run on a section that already has body content, with `+N / −N words` stats, Keep-current vs Replace-with-AI actions. Only fires when body is non-empty (empty sections auto-apply).
  2. **Public Full-Docs Zip** — new endpoint `GET /api/v1/tender-templates/{id}/public/zip?notice_ref=…` (`zipfile` from stdlib) bundles the composed PDF + every section attachment + `README.txt` index. Public gated by the linked notice being published. Verified: 33 KB zip with `Standard_..pdf` + 3 attachments + README.
  3. **Tone Presets in UI** — new `AiDraftMenu` popover replaces the plain ✨ button. Grid of Formal / Plain / Strict tones × Short / Medium / Long lengths (~120/240/420 words), a purple "Draft with AI" CTA, escape-on-outside-click. Verified via Playwright: all 6 knobs + go button render for every section.
  4. **Vendor Portal Preview** — added a "Preview as bidder ↗" link on every row of the admin Notices panel that opens the public `/notices/{ref}` page in a new tab (`target=_blank`). Also added a "Tender template" dropdown to the New-notice form so admins wire the template + notice together at creation time. A subtle "📐 template linked" badge appears on rows that already have one.
  - `diff@9.0.0` frozen into `frontend/package.json`.
- **Wave 29 (Tender Builder v3 — 2026-08-03)** — the 4 backlog items shipped:
  1. **Notice PDF Wire-Up** — `NoticeIn.tender_template_id` added; new public endpoint `GET /api/v1/tender-templates/{tid}/public/pdf?notice_ref=…` gated by the linked notice being published; the Notice Detail page now shows a prominent navy "Download the full tender (PDF, watermarked)" CTA. Verified 200 · `%PDF-1.7` · 3 pages.
  2. **Bulk Section Upload** — `POST /api/v1/tender-templates/{tid}/attachments/bulk` (multipart, N files). Filename→section matcher now prefers exact code → exact title-slug → longest-code prefix → longest substring, so `annex-VIII_bank.pdf` correctly matches `annex-VIII` (not `annex-V`). Frontend dropzone with per-file green/red report.
  3. **AI Section Drafts** — `POST /api/v1/tender-templates/{tid}/sections/{code}/ai-draft` using **emergentintegrations LlmChat** + `EMERGENT_LLM_KEY`. System prompt drafts HTML-only (via allowed-tag list), tone/length knobs, header context passed in. Sanitised server-side before persist. Per-section ✨ AI button in the UI. Verified: 758-char formal HTML draft for Annexure I.
  4. **Watermark & Version Stamp** — WeasyPrint `@page` running headers/footers: bottom-left `{status · v{version} · issued yyyy-mm-dd}`, bottom-right `Page x / y`, top-right shows the tender reference. Full-page diagonal DRAFT watermark when status ≠ PUBLISHED. Also injects a mustard `stamp` tile in the document header. `pypdf` confirms the "DRAFT" text and page-numbers are on every page.
  - Added `EMERGENT_LLM_KEY` into `backend/.env`.
- **Wave 28 (Real PDF export — 2026-08-03)**:
  - Adobe Acrobat rightly rejected the previous `.html` "Download" file. Replaced the client-side blob with a proper server-side render: new endpoint `GET /api/v1/tender-templates/{id}/export/pdf` uses **WeasyPrint** to produce a real A4 PDF, `Content-Disposition: attachment; filename="…pdf"`.
  - Frontend "Download" button relabelled `Download PDF` and now targets that endpoint — the browser downloads a genuine `%PDF-1.7` file.
  - Section bodies are re-sanitised server-side (`bleach` if installed, otherwise trust the DOMPurify client pass) before entering the PDF layout — no XSS carry-over.
  - Verified via curl + Playwright: 27 KB PDF, pypdf reads it as a valid multi-page document. Also `weasyprint` frozen into `backend/requirements.txt`.
- **Wave 27 (Admin vendor UX — 2026-08-03)**:
  - Killed the "Malformed registration id — save the draft first" wall on `/admin/vendors/new`. `DocSlot` now accepts an `ensureDraft()` callback and calls it lazily the first time the admin actually picks a file — the draft is created silently and the upload proceeds. No more manual "Save draft & enable uploads" click required.
  - Fixed route ordering in `App.js` — the `/admin/*` wildcard used to shadow `/admin/vendors/new`. Specific route now precedes the wildcard.
  - Nodraft banner rewritten as a soft info tile ("Enter the vendor email first — the draft is auto-saved the moment you pick a document"). Manual save button preserved as an optional shortcut.
- **Wave 26 (Tender PDF UX fix — 2026-08-03)**:
  - `Export PDF` split into **two robust buttons**: `Print / PDF` (hidden iframe + `iframe.contentWindow.print()` — popup-blocker-proof) and `Download` (self-contained `.html` file via `<a download>`). Verified: Playwright caught the download event (7,560-byte file, safe filename slug) and confirmed the iframe injection (0 → 1) on Print / PDF click.
  - Backend `/api/v1/uploads/files/{key}` now sets `Content-Disposition: inline; filename="..."` (strips the uuid_ prefix) + `X-Content-Type-Options: nosniff` so browsers preview PDFs and users get a sensible name when they Save-As.
  - Section attachment `<a>` in Tender Builder gained the `download={file_name}` attribute so right-click / cmd-click stores it cleanly instead of trying to render.
- **Wave 25 (code-review fixes — 2026-08-03)**:
  - **XSS defence in Tender Builder**: `RichEditor.jsx` now sanitises every HTML string on the way in AND out with **DOMPurify** (allowlist: p/br/b/strong/i/em/u/h2/h3/ul/ol/li/blockquote/code/pre/span/div/a); paste handler forces plain-text so no `<script>`/`onerror` survives. `tenderPdf.js` sanitises each section body before composing, drops `document.write` in favour of a **Blob URL + `window.open`**, and revokes the URL after 60 s. Verified via runtime injection test — the injected `<script>window.__pwned=true</script>` was blocked (pwned=false).
  - Added dev-mode warns to empty catches in `mobileBridge.js::saveSecure`/`clearSecure` and `tenderPdf.js::print`.
  - `PaymentResult.jsx`: two nested ternaries flattened into if/else for icon glyph + colour.
  - Confirmed the flagged Python `is None` / `is not None` checks in `vendor_full_invite.py`, `packages.py`, `boqs_helpers.py` are PEP-8 correct — leaving them untouched (`is None` is mandated for None; the scanner false-positives it as "constant comparison").
  - i18n-strings.js "secret" flags at lines 199/252/753/806 confirmed again as translation labels for the password field (already annotated in prior waves) — no change.
- **Wave 24 (this session — 2026-08-03)** — Tender Builder v2:
  - Injected **CPPP-style structured header form** (`TenderHeaderForm.jsx`) at the top of `TenderBuilderPanel` — Basic Details, Cover Details (multi-row), Fee & EMD, Work/Item, Critical Dates (8 datetimes), NIT + Work-Item Documents lists, Tender Inviting Authority (~60 typed fields streamed into `doc.header`).
  - Built dependency-free **RichEditor** (`tender/RichEditor.jsx`) — Bold, Italic, Underline, H2, H3, Paragraph, • List, 1. List, Blockquote, Undo, Redo, Clear formatting. Persists HTML into the same `section.body` field (fully back-compat with plain-text seed).
  - Added **Per-section Template Attachments** — new backend endpoints `POST/DELETE /api/v1/tender-templates/{id}/sections/{code}/attachment` write to `db.uploads` (same pattern as notice docs); UI shows current file + Upload/Replace/Remove per section.
  - Added **Export PDF** button in save bar — opens a print-ready standalone HTML window (`tenderPdf.js`) with the composed header table + all sections + inline RichEditor HTML → browser Save-as-PDF.
  - Verified with screenshot (header form + Bold text applied + attachment row) and cURL (upload + delete round-trip on `annex-VIII`).
- **Wave 23** — code review round 3:
  - Empty-catch dev-mode logs added to `NotificationBell.jsx`, `VendorDashboard.jsx::logout`, `StaffDashboard.jsx::logout`, `MobileLogin.jsx::tryDetect` (3).
  - Perf win in `TenderBuilderPanel.jsx`: sections list now `useMemo`'d — avoids `sort()` on every re-render + preserves referential identity for React reconciler.
  - Skipped (same false-positive family as prior waves): the recurring "hardcoded secrets" flags at i18n-strings.js lines 199/252/753/806 (translation labels for the *password field*, already annotated), and I18nContext `useMemo` "missing STRINGS in deps" (ESLint says otherwise — STRINGS is a module-level constant).
- **Wave 22** — Sign-in Hub redesign (Employee / Vendor two-card split)
- **Wave 21** — Upload 500 fix + admin-side uploads
- **Wave 20** — Tender / RFP / RFQ Template Builder

### P1 (Next)
- **Deploy Refresh** — user needs to click "Save to Github" + "Deploy" so Waves 15–18 land in production, then hit `POST /api/v1/admin/heal/rename-admin` once to purge the legacy `admin@pmcmanagers.com` row from prod
- **Firebase + APNs** — waiting for `google-services.json` + APNs auth key
- **Live KYC-Checks** — waiting for `KYC_BASE_URL` + `KYC_API_KEY`
- **Admin UI for subdomain/host_alias** — currently editable via API only; add fields to the `MastersPanel > Tenants` form so admins can set CNAME aliases from the UI (P2)

### P2
- Refactor big frontend components (BiddingOpsPanel, MastersPanel, BOQContractsPanel) — deferred
- Domain-based multi-tenant routing (currently query-string)
- Phase 2 AWS migration

## Deployment Notes
- MongoDB unique indexes MUST use `sparse=True`
- CSRF double-submit on state-changing routes
- Emergent LLM key powers AI Audit Copilot + bid anomaly
- Emergent Email key powers all send_email calls (best-effort if missing)
- `KYC_PROVIDER` env var: `stub` (default) or `kyc-checks` (real)
- **Production self-heal**: after redeploy, hit `POST /api/v1/admin/heal/rename-admin` once to clean the legacy `admin@pmcmanagers.com` row

## Integrations
- Stripe (sandbox key in pod env)
- Emergent LLM key
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks (real client wired; awaiting credentials)
- Capacitor 8.x (camera, preferences, push-notifications) + biometric-auth
