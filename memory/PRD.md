# PMC Managers v2 — Product Requirements & Status

## Original Problem Statement
Global enterprise e-Tender platform mirroring a 39-page Enterprise CRM & e-Tender Revised Integrated Report. Full multi-role approval pipeline (Escrow, Certifier, Legal, Accounting), dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, and an AI Audit Copilot.

## Roles
Admin · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee).

## Core Modules
Notice Board · Registration · Package Tracker · Bidding Management · BOQ Builder · Evaluation & Contracts · Vendor Intelligence · Tender/RFP/RFQ Template Builder · Joint-Signature Escrow · Reverse Auctions · Meetings (Jitsi + Zoom) · DocuSign eSignature.

## Monetization
Product Catalog · Stripe checkout · Quote pipeline · Subscriptions · Engagements.

## 3rd Party Integrations (Live)
- **Stripe** — payments (sandbox `sk_test_emergent`)
- **Emergent LLM** — AI Audit Copilot, tender section draft, redline
- **Zoom** — Server-to-Server OAuth (rotated 2026-08-08)
- **Jitsi** — no-keys meetings
- **DocuSign** — JWT sandbox, embedded + email delivery, Connect webhook with HMAC (Wave 43/44)
- **UNSPSC taxonomy** — commodity picker (Wave 44)

## 3rd Party Integrations (Backlog / Mocked)
- Firebase & APNs push (needs project ID + service account)
- Live KYC provider (needs KYC_BASE_URL + KYC_API_KEY)
- Resend email delivery (currently mocked)
- PayPal & Kaspi Pay (currently mocked sandbox — needs real merchant creds)

---

## Implementation Timeline (compressed)

### Delivered (production-ready in preview)
- **Wave 35** — Product Catalog (55 rows) + Stripe billing
- **Wave 38** — Engagements: quote → invoice pipeline
- **Wave 39** — Corrigenda publisher · Two-cover envelope · Auto PO/SLA/Contract on award
- **Wave 41b** — Zoom S2S OAuth meetings
- **Wave 42a** — Trilingual sweep (EN/RU/KK) across 15 admin panels
- **Wave 42b** — Mobile responsive audit
- **Wave 43** — DocuSign eSignature (JWT sandbox), embedded signing, Connect webhook w/ HMAC verification (secret `KFSC…VEs=` in `.env`), envelope status live-updates
- **Wave 44** (2026-02-11)
  - DocuSign delivery-mode toggle: `embedded` vs `email`
  - Delivery column + Signed PDF download button in envelope log
  - Backend endpoints: `GET /api/v1/docusign/envelopes/{id}/combined-pdf` (admin) and `/mine/envelopes/{id}/combined-pdf` (vendor)
  - Vendor Signing Dashboard (`VendorSignatures.jsx`)
  - UNSPSC picker attached to BOQ template creation + Vendor Registration Section C
  - Toaster moved from top-right → bottom-right (no longer covers avatar)
  - New "How to use the platform" user-journey flowchart (`_userguide.py` · 22kb SVG · 81kb PDF · 37 numbered steps across 5 phases). Endpoints: `GET /api/v1/reports/user-guide.svg|.pdf`
  - Refactored oversized files:
    - `TenderBuilderPanel.jsx` 481 → 362 lines
    - `AdminVendorCreate.jsx` 213 → 177 lines
    - `reports.py::_build_flowchart_svg` 376 lines → 11-line delegator + `_flowchart.py` split by 7 lane helpers (byte-identical output verified: 23578 bytes)

### Backlog (prioritised)
**P0 — Push to production**
- User to click **Save to GitHub** and **Deploy** in Emergent chat input
- After deploy: update DocuSign Connect webhook URL from preview to prod domain in DocuSign Admin

**P1 — Complete UNSPSC integration**
- ✅ Attached UnspscPicker to BOQ template creation (Wave 44)
- ✅ Attached UnspscPicker to Vendor Registration Section C (Wave 44)
- Backlog: propagate per-line-item UNSPSC on BOQ items (currently template-level only)

**P2 — Real integrations (blocked on external creds)**
- PayPal & Kaspi Pay real (needs merchant creds from user)
- Firebase & APNs push (needs project ID + service account JSON)
- Live KYC provider (needs KYC_BASE_URL + KYC_API_KEY)
- Resend real email delivery (needs Emergent-managed Resend key)

**P2 — UX / observability**
- ✅ Delivery column in envelope log (Wave 44)
- ✅ Signed PDF download button (Wave 44)
- ✅ Toaster moved to bottom-right (Wave 44)
- Test-plan doc auto-regeneration on wave completion

---

## Key API Endpoints (recent adds)
- `POST /api/v1/docusign/webhook` — Connect callback, HMAC-verified
- `POST /api/v1/docusign/awards/{bid_id}/{kind}/envelope` — send envelope (accepts `delivery: embedded|email`)
- `GET  /api/v1/docusign/envelopes` — list
- `GET  /api/v1/docusign/envelopes/{env_id}` — status + live sync
- `GET  /api/v1/docusign/envelopes/{env_id}/combined-pdf` — signed PDF (Wave 44)
- `GET  /api/v1/docusign/mine/envelopes/{env_id}/combined-pdf` — vendor-facing signed PDF (Wave 44)
- `GET  /api/v1/reports/flowchart.svg|.pdf` — 23578-byte platform architecture flowchart
- `GET  /api/v1/reports/user-guide.svg|.pdf` — user-journey how-to-use flowchart (Wave 44)
- `GET  /api/v1/reports/comparative-statement.xlsx|.pdf|.docx` — Asked vs Delivered

## Key DB Collections
- `docusign_envelopes` — {envelope_id, kind, sub_kind, bid_id, delivery, status, webhook_at, ...}
- `award_documents` — {kind, pdf_b64, vendor_id, bid_id, status}
- `taxonomy_nodes` — UNSPSC {code, segment, family, class, title}
- `payment_transactions`, `bids`, `notices`, `vendors`, `tender_templates`, `engagements`

## Test Credentials
See `/app/memory/test_credentials.md`.

## Preview URL
`https://tender-hub-57.preview.emergentagent.com`

## Production URL (Emergent-managed, already live)
`https://tender-hub-57.emergent.host`

## AWS Production — 🎉 LIVE with custom domain (2026-02-12)
- **Live app**: `https://www.pmcmanagers.com` (also `https://pmcmanagers.com` → 301 → www)
- **Cert**: ACM us-east-1 `f9755627-05ac-4dc6-b4ab-5751ddd4f5e8` covers www + apex
- **Verified**: HTTP 200 health, admin login 200, CORS allow-origin correct
- **Architecture**: GoDaddy DNS → CloudFront (Free + WAF, distribution `E2WZT1TMQ0EK9W`) → S3 (static) + EB Docker t3.medium (`/api/*`) → MongoDB Atlas (`pmc-managers-uk`, eu-west-2)
- **Fallback URL**: `https://d2h9tkca2zjofy.cloudfront.net` still active (belt & suspenders)
- Full launch state + fixes applied: `/app/memory/AWS_LAUNCH_STATE.md`
