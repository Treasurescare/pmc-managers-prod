# PMC Enterprise CRM & e-Tender — Master Delivery Roadmap

Source of truth: `PMC_Managers_Enterprise_CRM_eTender_Revised_Integrated_Report.pdf`
Progress tracker for the full-scope build (Option C — build everything).

Legend: 🟢 Done · 🟡 In Progress · ⚪️ Not Started

---

## WAVE 1 — Bidding & Financial Core  🟢 COMPLETE (Feb 2026, 34/34 tests)
Vendor login · Bid submission w/ PDFs · EMD via Stripe · Multi-role staff auth (single `/staff/login`, role dropdown, multi-role per user) · Escrow/Certifier/Legal/Accounting/Committee dashboards · Sequential pipeline · Bid Committee formation & closure · CRM tasks + internal chat · Site inspection with photo/video · Masters CRUD backend.

## WAVE 2 — Evaluation Engine  🟢 COMPLETE (Feb 2026, part of 29/29 Wave2-6 tests)
Multi-envelope lock (technical + commercial) · Scoring rubric with weighted criteria · **Mandatory Conflict-of-Interest declaration BEFORE scoring** (enforced with 400) · Technical + commercial scoring per evaluator · Weighted combined score · Award Recommendation Report with pass/fail on minimum-technical cutoff.

## WAVE 3 — Contract & BOQ  🟢 COMPLETE (Feb 2026)
BOQ template builder + Excel (.xlsx) import + item-wise pricing · Vendor BOQ submissions with auto-total · Cross-vendor rate comparison view · Contract Management (auto `PMC-CON-YYYY-####` reference, awarded-bid gating, milestones, variation orders) · Multi-currency (currency field on BOQ/contract).

## WAVE 4 — Vendor Intelligence & Masters UI  🟢 COMPLETE (Feb 2026)
Vendor Intelligence (rating, band, blacklist, watchlist, ESG declarations, joined summary view) · Admin console **Masters** tab exposing Staff Master (multi-role CRUD), Companies, Approval Matrix editor, Hierarchy visualiser · Helpdesk tickets in Wave 6.

## WAVE 5 — Intelligence & Integrations  🟢 COMPLETE (Feb 2026, backend)
BI Dashboard (`/api/v1/analytics/dashboard` — totals, funnel, top bids, EMD collected) · AI Bid Anomaly Check (deviation vs peer bids + Emergent LLM narrative fallback) · In-app notifications wired to state machine · Frontend NotificationBell polls every 20s. PayPal + Kaspi gateways — DEFERRED (Stripe covers the demo).

## WAVE 6 — Governance & Enterprise  🟢 COMPLETE (Feb 2026, backend)
Reverse/forward/live/sealed Auction module (create + place-bid with min-decrement rule) · Helpdesk tickets (open/reply/close). MFA, GDPR consent, sanctions screening — DEFERRED (P2 backlog).

---

## Combined test evidence
- Wave 1: 34/34 backend tests (`/app/backend/tests/wave1_test.py`, iteration_14.json)
- Wave 2-6: 29/29 backend tests (`/app/backend/tests/wave2_6_test.py`, iteration_15.json)
- Frontend: 11-tab Admin Console + Vendor Portal + Staff Portal — all render, tabs clickable, NotificationBell active

## Wave 1-6 Decisions locked
1. Bid content: Price + EMD + PDF uploads
2. EMD amount: Fixed + % + combination (admin per tender)
3. Staff auth: Single `/staff/login`, role dropdown, staff may hold multiple roles
4. Vendor login: Auto-password emailed on approval + force change on first login
5. Bid Committee: Per-tender tag drawn from admin pool
6. Notifications: In-app row + Resend email (fire-and-forget)
7. Master admin: `adminsupport@pmcmanagers.com` / `Admin@123`

## Deferred (P2 backlog)
- MFA (TOTP)
- GDPR consent tracking + right-to-be-forgotten
- Sanctions screening / duplicate-bid ML detection
- Subscription & Monetisation
- Sandbox + Training environment
- Government / Corporate CRM tenant portals

## Feb 2026 — Post-Wave-6 enhancements shipped
- **Approval Matrix editor**: full drag-lite reorder (↑ / ↓), add step, delete step, editable role dropdown + action label + SLA hours per row in the Admin console → Masters → Approval Matrix tab
- **EMD gateway selector**: vendor bid submit page now offers **Stripe · PayPal · Kaspi Pay**. Stripe stays live; PayPal + Kaspi ship as in-app sandbox demos that advance the bid to `emd_paid` end-to-end so escrow/certifier/legal/accounting demos can be walked through on any gateway. Real PayPal/Kaspi live-mode remains on the P2 backlog and will replace the sandbox endpoints without vendor-facing contract changes.
- **Approval Matrix wired into the live pipeline**: notices can now pick a matrix via a dropdown on the Notice form. The bid decision endpoint resolves the *next* status dynamically from `matrix.steps` (falls back to the default hard-coded pipeline when no matrix is set). Admins are now no-code procurement engineers.
- **MFA (TOTP)** for Staff Portal: `/api/v1/staff/mfa/{enroll,verify,disable,status}` + PyOTP + QR PNG generation. Admin header has a "Security · 2FA" button opening the setup modal (scan QR → verify OTP → shows recovery codes). Staff login now returns `{mfa_required: true}` if the user has MFA enabled; the login form shows a second OTP step.
- **GDPR consent flow**: registration draft captures `data_processing_consent` + `marketing_consent` (with timestamp). New `POST /api/v1/registrations/{id}/gdpr-forget` endpoint anonymises registration + linked vendor documents while preserving the audit hash-chain (Art. 17 compliant).
- **Tenant Master**: `POST/GET/PATCH /api/v1/tenants` for **Corporate Client**, **Government Department**, and internal PMC tenants. Admin → Masters → Tenants sub-tab adds them with code / name / kind / country. The infrastructure for full multi-tenant portal isolation is now in place; visible per-tenant portal skin ships in a follow-up drop.
