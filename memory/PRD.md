# PMC Managers Limited — PRD

## Original problem statement
Build and operate PMC Managers Limited (pmcmanagers.com), a multi-role procurement and tender-management platform for Kazakhstan and CIS markets. Roles include Admin, Management, Partners, Agents and Registered Vendors. Core surfaces: public tender notice board (About Us, Vision & Mission, Live/Completed/All Tenders lists), vendor registration, admin tender workbench, evaluations, awards, escrow, auctions and analytics. AI-assisted DPR ingestion must handle very large tender/DPR documents "of any size and any number of characters" and produce genuine section-level extraction, not stubs.

## Architecture

- Frontend: React (CRA), Tailwind, shadcn/ui — hosted on S3 + CloudFront.
- Backend: FastAPI on AWS Elastic Beanstalk (Docker) with 25 MB nginx body limit.
- Data: MongoDB (via `MONGO_URL`).
- AI: Emergent LLM Universal Key (map-reduce DPR pipeline in `backend/routers/tender_pro.py`).
- Auth: Cookie sessions, three realms (admin, staff, vendor). Same-origin `/api` calls required in production bundles.
- Assets: Public `/downloads/` folder for release artifacts and manuals — NEVER deleted with `s3 sync --delete` at bucket root.

## Implemented (as of 2026-09-24)

- **v46m Manual v2** — regenerated 66-page (25-chapter, 32-screen) master training manual against the deployed sovereign design.
  - Screens: 8 public + 6 five-portal logins + 14 admin tabs + 5 vendor tabs = **32** full-page captures at 1600×900 @ 1.25 DSR (retina-clean).
  - Chapters: architecture, roles matrix, security/audit, public journey, vendor journey, admin tour, DPR deep-dive, evaluation/escrow deep-dive, reverse auctions, UX safeties, deploy runbook, troubleshooting, API index, release history, glossary, 30/60/90 onboarding, monthly cadence, KPIs, escalation matrix, keyboard shortcuts, FAQ, sample tender lifecycle, data-model appendix, release archive, sign-off.
  - Artefacts: PDF (9 MB), DOCX (8 MB), MD (49 KB) plus a single-file bundle zip (16 MB).
  - Regenerate at any time with `python3 /app/tools/manual/capture.py && python3 /app/tools/manual/build.py`.
- **v46m Bug Blitz Round Two** (backend + frontend zips staged).
  - `GET /api/v1/evaluations/lock-state/{notice_ref}` added; frontend `EvaluationPanel` now disables Lock buttons + shows sealed timestamp banner once an envelope is locked.
  - `POST /api/v1/evaluations/lock-envelope` refuses re-lock (409) so a rogue call cannot overwrite the timestamp / attribution.
  - `AuctionRoom` recent-bids row rebuilt as `flex-col sm:flex-row` with `break-all` on money column — resolves mobile overflow (bug tracker items 78/81/82).
  - Rubric max + Registration Section-A step gate re-verified in code (were shipped earlier; still enforcing).
  - Stakeholder-snapshot JSON parse: no live frontend caller in current source — deferred with "no repro" note.
- **v46l Unlimited DPR + async worker** (staged 2026-09-24).
- **v46k Sovereign Redesign** (deployed 2026-09-24)
  - Rebuilt `/login` as a 5-portal picker (Admin, Management, Partners, Agents, Vendors) with per-portal branding, badges, icons and dedicated credential forms.
  - Sovereign navy (#0B132B) + gold (#D4AF37) accent palette across public surfaces.
  - Refreshed home hero with editorial serif headline, gold kicker, gold primary CTA.
  - Home now uses `PmcFooter` (Snapchat / Instagram / WhatsApp social icons + gold seal strip).
  - New Tailwind tokens: `brand-gold`, `brand-gold-hover`, `brand-gold-soft`, `brand-navy-sovereign`.
- **v46j Map-Reduce AI DPR ingestion** (backend zip staged; production deployment pending).
- **v46i editorial public surfaces** (About Us, Vision & Mission, live/completed/all tender lists, admin shell with 5-section collapsible sidebar + hamburger drawer). Deployed to production.
- **v46f no-master AI DPR flow** (editable tender name, save-as-master persists, master reusable across countries).
- **v46b/c/d/g bug blitz** (bulk of the 87-item bug tracker fixed and shipped).

## Open backlog (P0/P1/P2)

**P0 (blocking)**
- Deploy v46j backend + v46k frontend to production and run KMT DPR validation end-to-end.
- Address "unlimited size" DPR ingestion — remove the 800 KB cap and add background/async worker processing for 100 MB+ / 500+ page files.

**P1 (bugs still open in tracker)**
- Registration wizard step-validation gate between Section A and B/C.
- Stakeholder Reports save-snapshot JSON parse error (needs backend RCA).
- Evaluation rubric max-value client-side gate.
- Locked-evaluation should refuse re-open + show saved report.
- TenderBuilder Tender/RFP/RFQ tab switch should refetch.
- Escrow — modify email IDs on transaction signer flow.
- Mobile CSS overflow: landing pipeline funnel labels, reverse-auction summary button, vendor-intel columns.
- i18n Russian/Kazakh strings backfill.
- Profile avatar cache invalidation after re-login.
- Global email + mobile regex validation across forms.

**P2 (feature backlog)**
- Manual v2 (130–160 pages) covering admin sub-tabs, modals, workflows, vendor journey — capture after v46k design settles.
- Firebase / APNs push notifications.
- LSEG / World-Check integration.
- PayPal / Kaspi payments alongside Stripe.
- Zoom integration for evaluation committees.

## Guardrails

- Never use `aws s3 sync ... --delete` at bucket root — it previously deleted `/downloads/`.
- Production frontend bundle MUST be built with no `REACT_APP_BACKEND_URL` (same-origin `/api`).
- Service worker registration remains disabled/self-cleaning.
- Do not package `backend/.env` in EB deployment archives — use EB environment properties.

## Recent artifacts

- `/app/frontend/public/downloads/pmc-backend-v46j.zip` — map-reduce DPR backend for EB.
- `/app/frontend/public/downloads/pmc-frontend-v46k-prod-build.zip` — sovereign redesign frontend.
- `/app/frontend/public/downloads/DEPLOY_v46k_README.md` — deploy instructions.
- `/app/deliverables/v46c/Bugs_Tracker_v46h.xlsx` — bug tracker current status.
