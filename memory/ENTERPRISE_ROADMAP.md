# PMC Enterprise CRM & e-Tender — Master Delivery Roadmap

Source of truth: `PMC_Managers_Enterprise_CRM_eTender_Revised_Integrated_Report.pdf`
Progress tracker for the full-scope build (Option C — build everything).
Updated after each Wave completes and passes tests.

Legend: 🟢 Done · 🟡 In Progress · ⚪️ Not Started · ⏸ Blocked

---

## WAVE 1 — Bidding & Financial Core  🟡 IN PROGRESS

| Item | Status | Notes |
|---|---|---|
| Vendor login (post-approval accounts) | 🟡 | Auto-password + change on first login |
| Tender browse (vendor side) | 🟡 | Filters, categories, EMD preview |
| Bid submission (price + PDF uploads) | 🟡 | Technical proposal + Commercial proposal + supporting docs |
| EMD payment via Stripe Checkout | 🟡 | Amount = fixed + % of tender value (combinable) |
| Multi-role staff auth (multi-role per user) | 🟡 | Single `/staff/login` with role dropdown |
| Staff role: Escrow Agent dashboard | 🟡 | Accepts EMD |
| Staff role: Certifier + Site Inspection module | 🟡 | Upload site photos/videos |
| Staff role: Legal Counsel dashboard | 🟡 | KYC / legal clearance |
| Staff role: Accounting dashboard | 🟡 | Financial sign-off |
| Bid Committee (per-tender committee tag) | 🟡 | Formed from Admin pool |
| Bid Committee closure logic | 🟡 | Deadline auto-close + committee override |
| CRM Task + Followup module | 🟡 | Assign tasks, followups |
| CRM Internal Chat module | 🟡 | Files/photos/videos, view/delete |
| Masters: Company / Staff / Role / Hierarchy / Approval Matrix | 🟡 | Admin-configurable |

## WAVE 2 — Evaluation Engine  ⚪️
- Multi-envelope bidding (Technical / Commercial time-lock)
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

## WAVE 5 — Intelligence & Integrations  ⚪️
- BI Dashboards + Custom Report Builder + Cross-project Benchmarking
- AI: vendor scoring, bid anomaly detection, tender recommendation, predictive costing (Emergent LLM key)
- Integration Gateway (webhooks, ERP/finance stubs, eSignature, calendar sync)
- Additional payment gateways: PayPal, Kaspi

## WAVE 6 — Governance & Enterprise Hardening  ⚪️
- MFA + encryption at rest + session mgmt + data masking
- Risk & Compliance (duplicate-bid detection, sanctions screening, fraud patterns)
- GDPR + Data Retention + Consent tracking
- Auction Module (reverse / forward / live / sealed)
- Subscription & Monetisation (vendor plans, pay-per-tender, featured listing)
- Sandbox + Training environment

---

## Wave 1 — Decisions locked
1. **Bid content**: Price + EMD + PDF uploads (technical + commercial + supporting)
2. **EMD amount**: Fixed value + Percentage + Combination (admin sets per tender)
3. **Staff auth**: Single `/staff/login`, role dropdown on login, **staff may hold multiple roles**
4. **Vendor login**: Auto-password emailed on approval, forced change on first login
5. **Bid Committee**: Separate committee tag per tender, drawn from Admin pool

## Wave 1 — Extended asks (from user turn)
- Company Master · Staff Master · Role Master · Hierarchy Master · Approval Matrix Master
- CRM: assign tasks + followups + internal chat with file/photo/video upload + view/delete
- Certifier module: admin assigns a responsible person per tender for verification, site inspection, upload site photos & videos
