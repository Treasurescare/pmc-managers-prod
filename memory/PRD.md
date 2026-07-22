# PMC Managers Limited — Tender Management Platform (PRD)

## Original problem statement
Build a global tender management application titled **PMC Managers Limited**. Vendors register through a Pre-Tender Registration Form (Sections A–E). Solution serves multiple countries with country-specific IDs (Kazakhstan as primary jurisdiction).

## User personas
- **Vendor** — Bidder. Completes KYC. Bids on tenders after approval.
- **Buyer** — Publishes tenders, evaluates bids, awards contracts.
- **Admin / Contracts Committee** — PMC Compliance / Procurement office. Approves vendors, signs off tenders, oversees the whole board.

## Core requirements (static)
- Multi-role auth (JWT httpOnly + Emergent Google OAuth)
- Vendor Pre-Tender Registration Form aligned to Sections A–E of the supplied docx
- Country-aware Tax/Business ID capture (30 countries, Kazakhstan default)
- 6 declarations + electronic signature block
- KYC document uploads (tagged to the required document list)
- Tender lifecycle: draft → pending_approval → open → closed/awarded/rejected
- Buyer creates tenders with 200+ pre-classified categories from PMC Works List
- Vendor bidding with price + currency + delivery + attachments
- Bid comparison with "lowest bid" highlight
- Admin vendor approval workflow with inspector panel
- In-app notifications for state changes
- Public landing page with live stats

## v1.1 (2026-02)
- Resend transactional emails, Emergent Google OAuth, Stripe registration fee, KZ license gate, CSV bid export, Multi-language EN/RU/KK.

## v1.5 (2026-02) — Live Feed
- Right-rail Tender Feed switched from 15s polling → **Server-Sent Events (SSE)** at `/api/feed/stream`
- Filter chips: All / RFP / RFQ / Tender / My country / Unread
- Per-user read/unread state (`read_tender_ids` on user doc); mark-read + mark-all-read
- Higher-contrast time-remaining badge (destructive under 24h)
- Async email fan-out on POST /api/tenders to keep responses fast

## v1.6 (2026-02) — Two-envelope Sealed Bidding
- RFP `two_envelope: bool`. Technical + Commercial envelopes remain sealed to buyer until explicitly opened
- Backend masking: hides technical_proposal until `technical_opened_at`, hides commercial (price/proposal/attachments) until `commercial_opened_at` AND bid is `technical_qualified=True`
- New endpoints: POST /tenders/{id}/open-technical, /open-commercial, /bids/{id}/qualify
- Award blocked on two-envelope until commercial opened AND bid qualified
- UI: TwoEnvelopePanel with 3-stage indicator, Qualify/Reject buttons, sealed price cells

## v1.7 (2026-02) — Governance & Collaboration (P1 batch)
### Multi-level Approval Workflow
- Tender `approval_state: not_required|pending|approved|rejected` + `approval_chain: [{level, threshold, decision, approver_user_id, decided_at, notes}]`
- Approval chain auto-derived from department budget thresholds
- `require_approval` flag forces admin sign-off even without department
- POST /api/tenders/{id}/approve walks chain; pending tenders hidden from vendors until fully approved
- SSE broadcast fired only when a tender finally becomes open

### Buyer Orgs & Departments
- `orgs` collection: {name, code, country}
- `departments` collection: {org_id, name, code, approval_thresholds: [{threshold, level}]}
- Seed on startup: PMC Managers Global org + Medical Facilities (10k/100k) + General Procurement (50k/250k)
- POST /api/orgs, /api/departments, /api/users/me/department

### EMD (Earnest Money Deposit) + Stripe Refund
- Tender fields `emd_required`, `emd_amount`, `emd_currency`
- Bid fields `emd_reference`, `emd_payment_intent_id`, `emd_status`
- Auto-transition on award: winner → `held_as_security`, losers → `refundable`
- POST /api/bids/{id}/emd-refund (buyer/admin) triggers actual Stripe refund when `emd_payment_intent_id` is set; falls back to `refund_pending` on Stripe failure

### Pre-bid Q&A + Corrigendum / Addenda
- `tender_questions` collection with anonymization
- Vendors only see published (buyer-answered) questions from other vendors + their own
- Buyer/admin answer publishes to all vendors
- Addenda pushed onto tender.addenda[]; auto-notifies existing bidders

## Backlog (P2)
- Standard Bidding Documents (SBD) template library
- Vendor performance scoring / KPI dashboard
- SMS + WhatsApp notifications (Twilio)
- DSC/eSign integration + watermarking
- Immutable hash-chained audit trail
- Foreign currency conversion display (Central Bank rate)
- Approver as its own role (currently piggybacks on admin)
- Refactor server.py into /app/backend/routers/{tenders,bids,orgs,qa,payments}

## Test credentials
See `/app/memory/test_credentials.md`.

## Test coverage
- `/app/test_reports/iteration_1.json` … `iteration_8.json` — iter 6 SSE, iter 7 two-envelope, iter 8 P1 governance batch (100% pass)
