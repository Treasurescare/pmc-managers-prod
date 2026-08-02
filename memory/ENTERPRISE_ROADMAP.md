# PMC Enterprise CRM & e-Tender — Master Delivery Roadmap

Source of truth: `PMC_Managers_Enterprise_CRM_eTender_Revised_Integrated_Report.pdf`
Progress tracker for the full-scope build (Option C — build everything).
Updated after each Wave.

Legend: 🟢 Done · 🟡 In Progress · ⚪️ Not Started · ⏸ Blocked

---

## WAVE 1 — Bidding & Financial Core  🟢 COMPLETE  (2026-02, tests 34/34)

| Item | Status | Notes |
|---|---|---|
| Vendor login (post-approval accounts) | 🟢 | Auto-password + change on first login |
| Tender browse (vendor side) | 🟢 | 3 tender cards + budget preview |
| Bid submission (price + PDF uploads) | 🟢 | Technical + Commercial + Supporting docs |
| EMD payment via Stripe Checkout | 🟢 | Flow B, sk_test_emergent, /api/webhook/stripe |
| Multi-role staff auth (multi-role per user) | 🟢 | Single `/staff/login` with role dropdown |
| Staff role: Escrow Agent dashboard | 🟢 | Accepts EMD paid bids |
| Staff role: Certifier + Site Inspection module | 🟢 | Photo/video upload, pass/fail result |
| Staff role: Legal Counsel dashboard | 🟢 | KYC clearance |
| Staff role: Accounting dashboard | 🟢 | Financial sign-off |
| Bid Committee (per-tender committee tag) | 🟢 | Formed from admin pool |
| Bid Committee closure logic | 🟢 | Awarded vs closed vs deadline-locked |
| CRM Task + Followup module | 🟢 | Backend + attachment refs |
| CRM Internal Chat module | 🟢 | Soft delete, attachment refs |
| Masters: Company / Role / Approval Matrix | 🟢 | Backend CRUD; admin UI pending Wave 4 |

## WAVE 2 — Evaluation Engine  ⚪️ NEXT
- Multi-envelope bidding (Technical + Commercial time-lock)
- Technical + Commercial + Combined scoring
- Conflict-of-interest declarations
- Evaluation moderation + award recommendation report

## WAVE 3 — Contract & BOQ  ⚪️
- BOQ template builder + Excel import/export + item-wise pricing + auto-compare
- Contract Management (work orders, variation orders, milestones, renewals, obligations)
- Multi-currency + tax handling

## WAVE 4 — Vendor Intelligence & CRM Portals  ⚪️
- Corporate Client + Government Department portals (multi-org, multi-branch)
- Vendor Intelligence: unified rating, blacklist/watchlist, ESG, risk profile
- Configurable Workflow Engine (SLA clocks, escalations, conditional approvals)
- Communication Portal + Helpdesk/Ticketing
- Masters UI panels (Company/Staff Master, Hierarchy, Approval Matrix)

## WAVE 5 — Intelligence & Integrations  ⚪️
- BI Dashboards + Custom Report Builder + Cross-project Benchmarking
- AI: vendor scoring, bid anomaly detection, tender recommendation, predictive costing
- Integration Gateway (webhooks, ERP/finance stubs, eSignature, calendar sync)
- Additional payment gateways: PayPal, Kaspi

## WAVE 6 — Governance & Enterprise Hardening  ⚪️
- MFA + encryption at rest + session mgmt + data masking
- Risk & Compliance (duplicate-bid, sanctions, fraud)
- GDPR + Data Retention + Consent tracking
- Auction Module (reverse / forward / live / sealed)
- Subscription & Monetisation (vendor plans, pay-per-tender, featured listing)
- Sandbox + Training environment

---

## Wave 1 — Decisions locked
1. Bid content: Price + EMD + PDF uploads (technical + commercial + supporting)
2. EMD amount: Fixed + Percentage + Combination (admin sets per tender)
3. Staff auth: Single `/staff/login`, role dropdown, staff may hold multiple roles
4. Vendor login: Auto-password emailed on approval, forced change on first login
5. Bid Committee: Per-tender committee tag, drawn from Admin pool

## Wave 1 — Test evidence
- Backend: 34/34 pytest in `/app/backend/tests/wave1_test.py`
- Frontend: `/staff/login`, `/vendor/login`, `/admin` Bidding Ops tab, Notice EMD fields
- Sample data in DB: 1 vendor `TEST_Wave1_Vendor`, 1 bid `PMC-BID-2026-00001` (AWARDED), 2 committees
