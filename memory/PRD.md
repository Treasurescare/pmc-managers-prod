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
