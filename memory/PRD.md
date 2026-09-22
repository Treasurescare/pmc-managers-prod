# PMC Managers v2 — Product Requirements & Roadmap

Last updated: 22 Feb 2026 — v44 preview (Vendor Admin UI + Directors registration)

## Original Problem Statement
Develop a global tender management application (PMC Managers Limited v2) supporting a full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, and an AI Audit Copilot.

Core requirements:
- Roles: Admin, Vendor, Staff
- Core Modules: Notice Board, Registration, Package Tracker, Bidding Management, BOQ Builder, Evaluation & Contracts, Vendor Intelligence, Tender/RFP/RFQ Template Builder, Joint-Signature Escrow
- Monetization/Revenue: Product Catalog, Stripe checkout, Quote pipeline, Subscriptions
- Integrations: Stripe, Emergent LLM (AI Audit Copilot), KYC, Firebase, Resend, Zoom, DocuSign
- Fully white-labeled AWS Deployment (S3 + CloudFront + Elastic Beanstalk Docker)
- Codebase and Git history 100% purged of "Emergent" branding

## v44 — Preview (22 Feb 2026)

### Vendor Admin UI (P0 — DONE)
- **Inline "Activate now" green button** on every inactive vendor row (`VendorsPanel.jsx`).
- **Auto-scroll + emerald ring highlight (3.5 s)** on any vendor row that was just invited, activated, or force-activated. Newly created vendors no longer feel like they "disappeared".
- **Force-activate confirmation flow**: OK = resend magic-link email; Cancel = admin sets a temporary password inline and vendor is asked to change it on first login.

### Backend — new endpoint (P0 — DONE)
- `POST /api/v1/vendors/{vendor_ref}/activate` (admin + CSRF)
  - `mode=resend_link` regenerates magic token and re-emails the verify link.
  - `mode=set_password` force-activates immediately with an admin-supplied password (min 8 chars) and forces `must_change_password=True`.
  - Guards: 404 if vendor not in tenant, 400 if already active, 400 if `set_password` without password.

### Registration flow — Directors section (P1 — DONE)
- New **"Directors · Beneficial Owners"** tab inserted between Section D and Section E.
- Dynamic add/remove rows (unlimited entries), fields: Full legal name, Role (Director / Shareholder / UBO / Officer / Other), Nationality, ID/Passport #, Ownership %, Residential address.
- **Submit gate**: at least one row with a non-empty `full_name` required. Reason surfaced inline (red text under Submit button) and via toast.
- Persisted at `reg.directors` (array). Backed by existing `RegistrationUpdateIn` model with `extra="allow"` — no backend schema change needed.
- Localised in EN / RU / KK.

## v43 — Production Status (19 Feb 2026)

### Frontend — LIVE
- Bundle: `main.ac7e71b2.js` on https://www.pmcmanagers.com
- ⓘ Tooltips across all 26 admin panels via `<InfoDot>`
- 🔴 `showApiError()` loud toasts in 51 files (verbatim backend errors, HTTP status, 12-second red toast)
- 📖 In-app Help tab (from v42) now wired to live backend endpoint

### Backend — LIVE
- Version label: `v22g-clean-20260919-take3` on `pmc-backend-prod`
- Delta from v22f: two-line `include_router(help_content.router)` + static `help_content.json` + minimal `routers/help_content.py`
- Endpoint `/api/v1/meta/help` returns full 28-module JSON payload

### Deployment lessons learned this cycle
- CloudFront SPA-fallback silently serves `index.html` for any 404 on `www.pmcmanagers.com/downloads/*`. Always verify downloads via `file` + `shasum` BEFORE uploading to AWS — a "zip" that's really HTML will pass EB's file selector and fail at Docker-image parse.
- macOS Safari auto-extract + Finder-compress wraps zips in a parent folder, breaking EB's Dockerfile detection. Use Terminal `curl -O` + drag-from-Finder pattern for AWS uploads.
- Preview URL (`tender-hub-57.preview.emergentagent.com`) is the authoritative download source until the corresponding S3 upload lands.

## Follow-ups (still pending)
- **P1: Upload `downloads/` folder** from the frontend v43 build to S3 so `https://www.pmcmanagers.com/downloads/PMC_User_Manual_v43.pdf` returns real PDF instead of HTML. Requires an S3-console drag of the `downloads/` subfolder + CloudFront invalidation of `/downloads/*`.
- **P2: Stale prod data — Joint Escrow Account #1**: manual DB edit needed to assign distinct Escrow-officer email so bidder BID-2026-TEST2 unblocks.

## Backlog (P2 — deferred)
- Turkish / Russian / Kazakh translation versions of the Master Training Manual
- Firebase & APNs Push Notifications
- Live KYC provider integration
- PayPal & Kaspi Pay live integrations (currently mocked)
- Route 53 SOA min-TTL update from 86400s to 60s (optional DNS safeguard)

## Architecture
- `/app/backend` — FastAPI + MongoDB
- `/app/frontend` — React SPA (CRA + Shadcn UI + Radix + Sonner + Framer Motion)
- `/app/scripts` — deployment + docs generation pipelines
- `/app/deliverables` — versioned QA trackers, user manual DOCX/PDF, deployment tarballs

## Test credentials
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Key v43 files
- `/app/frontend/src/components/InfoDot.jsx`
- `/app/frontend/src/lib/api.js` (`showApiError()`)
- `/app/scripts/apply_show_api_error.py`
- `/app/scripts/capture_manual_v43.py`
- `/app/scripts/build_manual_v43.py`
- `/app/deliverables/pmc-backend-v22g-clean.zip` (sha256 `74e6c92258ed37cfcdd795c64d70e525dc83107e09bfc9dc87376f837001db97`)
- `/app/deliverables/deploy-frontend-v43.sh` + `deploy-backend-v22g.sh`
- `/app/deliverables/PMC_Bug_Tracker_v16_20260919.xlsx`
- `/app/deliverables/manual/PMC_User_Manual_v43.docx` + `.pdf`
