# PMC Managers Limited — Tender Management Platform (PRD)

## Original problem statement
Build a global tender management application titled **PMC Managers Limited**. Vendors register through a Pre-Tender Registration Form (Sections A–E). Solution serves multiple countries with country-specific IDs (Kazakhstan as primary jurisdiction).

## User personas
- **Vendor** — Bidder. Completes KYC. Bids on tenders after approval.
- **Buyer** — Publishes tenders, evaluates bids, awards contracts.
- **Admin** — PMC Compliance / Procurement office. Approves vendors, oversees the whole board.

## Core requirements (static)
- Multi-role auth (JWT, cookie-based)
- Vendor Pre-Tender Registration Form aligned to Sections A–E of the supplied docx
- Country-aware Tax/Business ID capture (30 countries, Kazakhstan default)
- 6 declarations + electronic signature block
- KYC document uploads (tagged to the required document list)
- Tender lifecycle: open → closed → awarded
- Buyer creates tenders with 200+ pre-classified categories from PMC Works List
- Vendor bidding with price + currency + delivery + attachments
- Bid comparison with "lowest bid" highlight
- Admin vendor approval workflow with inspector panel
- In-app notifications for state changes
- Public landing page with live stats

## v1 implemented (2026-02)
- Backend (FastAPI + Mongo)
  - Auth: register/login/logout/me (bcrypt + JWT httpOnly cookies)
  - Vendor profile upsert with Section A–E fields, declarations, signature, documents
  - Admin vendor list + approve/reject
  - Tenders CRUD, close
  - Bids: create, list, award (with automatic rejection of others)
  - Notifications on state changes
  - File upload (base64 in Mongo, 5MB cap)
  - Public stats + admin stats
  - Seed admin/buyer/vendor
- Frontend (React + Tailwind + Shadcn)
  - Landing (dark hero, Swiss/Old-Money Tech aesthetic, live stats)
  - Login + Register (role toggle)
  - Vendor: Dashboard, 6-step Pre-Tender Registration Form, My Bids
  - Buyer: Dashboard, Create Tender, My tenders
  - Admin: Overview, Vendor Approvals (with inspector), Users
  - Shared: Tender list (search/filter), Tender detail with bid form + bid comparison, Notifications

## Deferred / P1 backlog
- Google OAuth (Emergent-managed) — deferred to keep v1 focused
- Resend transactional emails (registration approved, bid awarded) — currently in-app only
- Country-specific eligibility gates (Kazakhstan licence-type requirement enforcement)
- Registration fee payment (Stripe test key)
- Company seal / stamp image upload
- CSV export of bids / vendors
- Tender revision & Q&A / clarifications thread
- Multi-language (Russian, Kazakh) for KZ vendors
- Vendor self-service AMC contract dashboard for Cross-Cutting Services vendors
- Advanced Bid scoring model (technical + commercial weights)

## Next tasks
1. Implement Resend email notifications (using Emergent-managed Resend)
2. Add Google OAuth via Emergent
3. Stripe payment for non-refundable registration fee
4. CSV/PDF export of bid comparison for finance & audit trail

Test creds live in `/app/memory/test_credentials.md`.
