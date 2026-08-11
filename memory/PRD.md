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
  - Vendor Signing Dashboard (`VendorSignatures.jsx`)
  - UNSPSC picker component (currently attached to Product Catalog only)
  - Refactored oversized files:
    - `TenderBuilderPanel.jsx` 481 → 362 lines
    - `AdminVendorCreate.jsx` 213 → 177 lines
    - `reports.py::_build_flowchart_svg` 376 lines → 11-line delegator + `_flowchart.py` split by 7 lane helpers (byte-identical output verified: 23578 bytes)

### Backlog (prioritised)
**P0 — Push to production**
- User to click **Save to GitHub** and **Deploy** in Emergent chat input
- After deploy: update DocuSign Connect webhook URL from preview to prod domain in DocuSign Admin

**P1 — Complete UNSPSC integration**
- Embed `UnspscPicker` into BOQ Builder line items
- Embed `UnspscPicker` into Vendor Registration Section C (scopes/commodities)

**P2 — Real integrations (blocked on external creds)**
- PayPal & Kaspi Pay real (needs merchant creds from user)
- Firebase & APNs push (needs project ID + service account JSON)
- Live KYC provider (needs KYC_BASE_URL + KYC_API_KEY)
- Resend real email delivery (needs Emergent-managed Resend key)

**P2 — UX / observability**
- Add "Delivery: email/embedded" column to envelope log table
- DocuSign envelope PDF download after completion
- Test-plan doc auto-regeneration on wave completion

---

## Key API Endpoints (recent adds)
- `POST /api/v1/docusign/webhook` — Connect callback, HMAC-verified
- `POST /api/v1/docusign/awards/{bid_id}/{kind}/envelope` — send envelope (accepts `delivery: embedded|email`)
- `GET  /api/v1/docusign/envelopes` — list
- `GET  /api/v1/docusign/envelopes/{env_id}` — status + live sync
- `GET  /api/v1/reports/flowchart.svg` — 23578-byte platform flowchart

## Key DB Collections
- `docusign_envelopes` — {envelope_id, kind, sub_kind, bid_id, delivery, status, webhook_at, ...}
- `award_documents` — {kind, pdf_b64, vendor_id, bid_id, status}
- `taxonomy_nodes` — UNSPSC {code, segment, family, class, title}
- `payment_transactions`, `bids`, `notices`, `vendors`, `tender_templates`, `engagements`

## Test Credentials
See `/app/memory/test_credentials.md`.

## Preview URL
`https://tender-hub-57.preview.emergentagent.com`
