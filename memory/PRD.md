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

## Session 2026-02-12 (Late afternoon) — FINAL BUILD v6 SHIPPED 🎉

### ✅ Completed Today
- **Wave 45 Awards↔DocuSign bridge**: "Send for Signature" button on each of 3 award cards (PO/SLA/Contract). Modal with signer name + email + delivery mode. Auto-opens signing tab in embedded mode.
- **DocuSign UX**: Signing URL page now shows "Open signing window" + "Copy link" buttons instead of raw ugly URL.
- **State persistence**: `pickedBidId` saved to localStorage — survives tab switches in Awards & POs.
- **Auth redirect fix**: AdminDashboard fallback now sends to `/login` (unified) instead of `/admin/login`. Both top-nav sign-in and direct `/login` land at the same admin state.
- **DocuSign Connect Webhook**: Fully working — every signed envelope updates `webhook_at` within seconds.
- **DocuSign JWT auth**: Fixed via base64 Private Key in EB.
- **CloudFront POST-routing**: User cleaned rogue behaviors → `/api/v1/awards/*`, `/notices`, `/tenders` all working.
- **Frontend v6**: `main.3c36ee81.js`, packaged as `/app/pmc-frontend-v6.zip`, uploaded to S3, CloudFront invalidated, verified live.

### 📌 User Confirmed Working
- Login via top-nav sign-in ✅
- Login via direct `/login` ✅
- Send for Signature buttons visible ✅
- Email field with prefill hint ✅
- State persistence across tab switches ✅

## AWS Production — 🎉 LIVE with custom domain (2026-02-12)
- **Live app**: `https://www.pmcmanagers.com` (also `https://pmcmanagers.com` → 301 → www)
- **Cert**: ACM us-east-1 `f9755627-05ac-4dc6-b4ab-5751ddd4f5e8` covers www + apex
- **Verified**: HTTP 200 health, admin login 200, CORS allow-origin correct
- **Architecture**: GoDaddy DNS → CloudFront (Free + WAF, distribution `E2WZT1TMQ0EK9W`) → S3 (static) + EB Docker t3.medium (`/api/*`) → MongoDB Atlas (`pmc-managers-uk`, eu-west-2)
- **Fallback URL**: `https://d2h9tkca2zjofy.cloudfront.net` still active (belt & suspenders)
- Full launch state + fixes applied: `/app/memory/AWS_LAUNCH_STATE.md`

---

## Session 2026-02-12 — DocuSign Prod Recovery (PARTIAL)

### ✅ Completed
- **DocuSign RSA Private Key restored** — user copied correct Private Key from DocuSign UI, base64-encoded via PowerShell (2232 chars), pasted full string into `DOCUSIGN_PRIVATE_KEY_B64` in EB → JWT auth working
- **Force-refreshed 2 stuck envelopes** (`a9d92a78...`, `2f9d225a...`) via `GET /api/v1/docusign/envelopes/{id}` live-fetch endpoint → both now `completed` in DB
- **HMAC secret removed** from EB (`DOCUSIGN_CONNECT_HMAC_SECRET` unset) to allow unsigned webhooks temporarily
- **Old Connect configs deleted** (22271585, 22272951 — both pointed to stale URLs)
- **New Connect config created** — `PMC Managers Prod`, URL: `https://www.pmcmanagers.com/api/v1/docusign/webhook`, HMAC OFF
- **TLS verified from container**: TLS 1.2 + 1.3, cert valid until Feb 2027, chain depth 3 ✅
- **Cosmetic bug identified**: `/api/v1/docusign/status` reports `configured: false` because deployed code checks disk path only — workspace fix already exists (line 257 checks B64 env var), needs backend redeploy

### ⏸️ Paused Mid-Test (user tired 2026-02-12)
- **Fresh test envelope**: `074129a3-16bb-8cb9-8069-f87ed8850caf` (PMC-AWD-2026-00011), signer `managerspmc@gmail.com`, status `sent`, waiting to be signed
- **Once signed** → verify `webhook_at` gets populated → proves Connect webhook is end-to-end working
- **If `webhook_at` stays None**: CloudFront TLS policy may be too strict → change from `TLSv1.2_2021` to `TLSv1.2_2019` in CloudFront distribution settings

### 🔮 Next Steps (in order)
1. **P0**: User signs envelope `074129a3-16bb-8cb9-8069-f87ed8850caf` from Gmail → verify webhook fires (60 sec wait)
2. **P0**: If webhook succeeds, re-enable HMAC — generate new secret in DocuSign Connect Keys, save to `DOCUSIGN_CONNECT_HMAC_SECRET` in EB
3. **P1**: Deploy latest backend to fix cosmetic `/status` endpoint (`configured: false` bug)
4. **P1**: Update DocuSign OAuth Redirect URI → `https://www.pmcmanagers.com/admin`
5. **P1**: Nuclear Git History Reset — fresh `pmc-managers-prod` GitHub repo before investor review
6. **P2**: Rotate weak admin password `Admin@123`
7. **P2**: Add per-row "🔄 Refresh Status" button to Envelope Log (manual escape hatch if webhook fails)
