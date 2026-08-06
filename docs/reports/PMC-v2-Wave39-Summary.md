# PMC Managers v2 — Wave 39 Executive Summary
### 2026-08-06 · Response to top-management (Sailesh Mal) feedback

---

## What was asked (top-management feedback · 06/08/2026)

Feedback from Sailesh's review identified 5 enterprise-grade capability gaps:

| Ref | Ask | Priority |
|---|---|---|
| a | Digital Signature Certificate (DSC / PKI) integration — legal non-repudiation on bids & contracts | High |
| b | Standardised Product/Service Taxonomy (UNSPSC or equivalent) | High |
| c-1 | Direct Purchase route for low-value catalog buys | Medium |
| c-2 | L1 (lowest-price) Comparison engine for mid-value tenders | Medium |
| c-3 | Custom Bids / BOQ for complex non-standardised tenders | Existing |
| c-4 | Pre-Bid Meeting & Corrigendum / Clarification Portal | High |
| d-1 | Two-Cover Submission (Technical/Financial split with sealed pricing) | High |
| d-2 | Reverse Auction (RA) live room — masked ids, auto-bid, price floor | High |
| e   | Post-Award auto-generation of PO, SLA, and Contract PDFs | High |

---

## What was DELIVERED in Wave 39 (this session · 3 features)

### ✅ Feature 1 — Corrigendum / Amendment Publisher  *(covers c-4)*
- New backend router `backend/routers/corrigenda.py`
- Endpoints:
  - `POST   /api/v1/notices/{ref}/corrigenda` (admin) — publish new corrigendum, auto-numbered
  - `GET    /api/v1/notices/{ref}/corrigenda` (public) — list active corrigenda
  - `GET    /api/v1/notices/{ref}/corrigenda/admin` (admin) — list all
  - `DELETE /api/v1/notices/{ref}/corrigenda/{cid}` (admin) — soft-withdraw
  - `POST   /api/v1/notices/{ref}/corrigenda/{cid}/attachment` (admin) — attach revised BOQ/drawings
- If the corrigendum contains `new_submission_deadline`, the parent notice deadline is auto-updated and stamped with `deadline_last_amended_by_corr`.
- Public Notice Detail page shows an amber banner with every active corrigendum in numbered order — bidders see it before submitting.
- Admin has a new **Corrigenda** tab in the console: pick any published notice, publish/withdraw corrigenda inline.
- Verified end-to-end via curl: published Corrigendum No. 1 on `PMC-NOT-2026-0020`; public notice response returned `corrigenda_count = 1`.

### ✅ Feature 2 — Two-Cover Envelope Enforcement  *(covers d-1)*
- Sealed-pricing rule now enforced server-side, not just in the data model.
- New endpoints on `backend/routers/bids.py`:
  - `POST /api/v1/bids/{id}/technical-clear` — committee/admin marks technical envelope as cleared
  - `POST /api/v1/bids/{id}/financial-open` — admin unseals the commercial envelope; **gated (HTTP 412)** until `technical_cleared_at` is set
- New `_redact_commercial()` filter runs on every bid list/get:
  - Bids strip `price_amount`, `price_currency`, `commercial_notes`, and any `documents[]` with `kind == "commercial"` when either (a) the viewer role is `tech_evaluator`/`technical_evaluator` without any finance-cleared role, or (b) the financial envelope has not yet been opened AND the viewer does not hold `admin`/`accounting`/`auditor`/`committee_member`.
  - A `commercial_redacted: true` marker is added to the response so UIs can show a "Sealed" badge.
- Verified end-to-end via curl: `technical-clear` returned 200 with `technical_cleared_at`; `financial-open` then also returned 200.

### ✅ Feature 3 — Post-Award Auto-Generated PO / SLA / Contract  *(covers e)*
- New backend router `backend/routers/awards.py`.
- Hook in `bids.decide_bid`: the moment a bid transitions to `awarded`, `generate_award_documents()` fires and drafts three WeasyPrint A4 PDFs:
  1. **Purchase Order** — auto-numbered `PMC-PO-YYYY-#####`, buyer + supplier + line-item table + signature grid
  2. **Service Level Agreement** — on-time delivery / defect rate / incident SLA / uptime targets + service credits clause
  3. **Contract / Letter of Acceptance** — award reference, contract value, references to tender + corrigenda + SLA + performance security, mandatory countersign clause; watermark `AWARDED`
- Documents are stored in `db.award_documents` (base64 PDF blobs) — idempotent upsert per `(bid_id, kind)`.
- Endpoints:
  - `GET /api/v1/awards/bid/{id}` (admin) — list documents
  - `GET /api/v1/awards/bid/{id}/mine` (vendor) — awarded vendor lists own docs
  - `GET /api/v1/awards/bid/{id}/pdf/{kind}` (admin) — download
  - `GET /api/v1/awards/bid/{id}/pdf/{kind}/mine` (vendor) — awarded vendor download
  - `POST /api/v1/awards/bid/{id}/regenerate` (admin) — re-fire the generator (idempotent)
- New admin **Awards & POs** tab: pick any awarded bid → see the three cards with `Award Ref`, `PO No.`, issued date, file size, "Download PDF" per card, and a global "Regenerate documents" button.
- Verified end-to-end via curl: forced a bid to `awarded`, regenerate returned `award_ref=PMC-AWD-2026-00001 · po=PMC-PO-2026-00001` with 3 valid PDFs (14 460 / 14 795 / 16 375 bytes). PDF header `%PDF-1.7` and 2 pages containing the correct PO number and buyer/supplier confirmed via `pypdf`.

### ✅ Bonus — Evaluation role firewall (previously P1 planned)
- `tech_evaluator` role now technically enforced through `_redact_commercial()`.
- This closes the earlier P1 backlog item ("Evaluator role firewall") without any additional feature work.

---

## Regenerated stakeholder artefacts

All 5 files under `/app/docs/reports/` have been regenerated to reflect Wave 39:

| File | Purpose |
|---|---|
| `PMC-v2-Asked-vs-Delivered.xlsx` | Comparative statement — 4 new Delivered rows + 6 new Planned rows |
| `PMC-v2-Asked-vs-Delivered.docx` | Narrative Word version of the same |
| `PMC-v2-Asked-vs-Delivered.pdf`  | WeasyPrint PDF of the same |
| `PMC-v2-Platform-Flowchart.svg`  | Now 7 lanes — new lane 7 shows Corrigenda + Two-Cover + Auto PO/SLA/Contract |
| `PMC-v2-Platform-Flowchart.pdf`  | Same, A3-landscape aware page size (380 × 348 mm) — no clipping |

---

## What is PENDING from the top-management feedback

The following six items from Sailesh's review are now formally on the roadmap as `Planned` rows and appear in the public `/roadmap` page:

| # | Item | Priority | Effort | Blocker |
|---|---|---|---|---|
| 1 | **DSC / PKI integration** | P1 | L | Needs a paid signature-vendor account |
| 2 | **Reverse Auction live room** (masked, auto-bid, price floor) | P1 | L | None — data model already in place |
| 3 | **UNSPSC taxonomy import + picker** | P1 | M | None — needs UNSPSC v25 seed |
| 4 | **L1 auto-comparison engine** | P2 | S | None |
| 5 | **Direct-Purchase value-threshold gate** | P2 | XS | None |
| 6 | **Pre-Bid Meeting scheduler** (video + RSVP) | P2 | S | Google Calendar / MS Teams integration choice |

---

## DSC / PKI — Recommendation (research spike)

You asked to "see how we can integrate a tool that reads a digital key". Options in decreasing fit for a UK-headquartered global platform:

| Vendor | Territory strength | Reads a hardware key? | Standard | Notes |
|---|---|---|---|---|
| **DocuSign eSignature Advanced** | UK/EU/US enterprise default | Yes — PKCS#11 + smartcards + USB tokens | eIDAS AES/QES, ESIGN, UETA | Most familiar to enterprise buyers, best legal precedent |
| **Signicat** (Norway-based) | UK + EU eIDAS-first | Yes — BankID, itsme, national eIDs, smartcards | eIDAS QES certified | Best if EU public-sector tenders are in scope |
| **Adobe Acrobat Sign — Cloud Signatures** | Global | Yes — cloud-based HSM + local USB tokens | eIDAS AES, PAdES | Native PDF signing, no server work required |
| **eMudhra emSigner** | India + global expansion | Yes — smartcard/USB token reader for India DSC | India IT Act 2000, eIDAS | Best if India tenders are in scope |
| **Emergent-managed OTP + audit + PKCS7** (in-house) | Any | Kind of — needs a client-side plug-in | Not eIDAS QES-graded | Cheapest but weakest legal weight |

### My recommendation
Ship **DocuSign eSignature Advanced** as the default (single vendor, global reach, best legal defensibility). Wire a fallback path to **eMudhra emSigner** for India-specific DSC users because that's where hardware tokens are still the norm.

Implementation path (once we have the paid account):
1. Add `signature_provider` and `signature_blob` fields on `bids`, `contracts`, and `award_documents`.
2. Frontend: DocuSign Web Widget on the bid submission + Award Package pages — reads USB DSC token via PKCS#11 browser extension.
3. Backend: DocuSign webhook confirms signature; store `envelope_id`, verify certificate chain, mark object as `signed`.
4. Every downstream download embeds the digital signature into the PDF (PAdES) so anyone can verify offline.

**Blocker for us to proceed:** one paid vendor account + API credentials.

---

## What was pending from YESTERDAY (2026-08-05)

| Task | Status |
|---|---|
| AWS deployment support — MongoDB Atlas + EC2 + Nginx walkthrough | **In progress** — user parked mid-way to attend to top-management feedback. Atlas cluster provisioned in Mumbai; user has since requested rebuild in **London (eu-west-2)** for UK data residency. Next: EC2 launch in London. |
| Live KYC (kyc.py) | Blocked — waiting for `KYC_BASE_URL` + `KYC_API_KEY` |
| Firebase + APNs push notifications | Blocked — waiting for `google-services.json` + APNs `.p8` |
| Real transactional emails (Resend) | Blocked — waiting for `EMERGENT_EMAIL_KEY` |
| Refactor `AdminVendorCreate.jsx` + `TenderBuilderPanel.jsx` | Backlog · P2 |

---

## Next step per user's instruction

> "after finishing this build we sit on the aws move"

Ready to resume the AWS deployment. Pending user action:
1. Terminate the Mumbai Atlas cluster
2. Provision new M0 cluster in **London (eu-west-2)**
3. Reset DB password & send new connection string
4. Launch EC2 t3.medium (Ubuntu 22.04) in London + Elastic IP + open ports 22/80/443/3000/8001

Then I walk you through SSH-in, install stack, clone, `.env`, supervisor, nginx.
