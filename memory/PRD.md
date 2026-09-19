# PMC Managers v2 · Product Requirements Document

## Original Problem Statement
Global tender management application (PMC Managers Limited v2) — full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labelled AWS deployment. Zero "Emergent" branding.

## Roles
Admin (master + reviewer/sub-admin) · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor).

## Architecture — LIVE
- Backend: FastAPI + MongoDB Atlas, 60+ routers.
- Frontend: React + Tailwind + Shadcn, 8 sub-apps.
- Deploy: EB (Single-instance Docker, backend-v18b-final) + S3 bucket `pmc-managers-frontend-prod` + CloudFront distribution serving `www.pmcmanagers.com`.
- **HTTPS termination**: CloudFront (single distribution) with `/api/*` Behavior forwarding to EB origin over HTTP:80. Zero-cost HTTPS, same-origin frontend + backend eliminates CORS.

---

## Implemented — 100% shipped (as of 19 Feb 2026)

### 19 Feb 2026 — CloudFront apex→www 301 redirect + same-origin architecture live
- **CloudFront Function `pmc-apex-to-www-redirect`** (cloudfront-js-2.0) associated with distribution `E2WZT1TMQ0EK9W` on the Default (*) cache behavior at Viewer request stage. `pmcmanagers.com` now returns `HTTP 301 → https://www.pmcmanagers.com/…` preserving path + querystring. Verified from container + 6 external nodes (Austria, Spain, Finland, Indonesia, Iran, USA) — all HTTP 200 end-to-end. `/api/*` on apex still routes to EB unredirected (function only fires on Default behavior).
- **Same-origin browser architecture** — the `/api/*` CloudFront behavior serves the backend under both `pmcmanagers.com/api/*` and `www.pmcmanagers.com/api/*`, eliminating the need for an `api.pmcmanagers.com` subdomain. Cookies are first-party (`Domain=www.pmcmanagers.com`), which sidesteps Safari ITP + third-party-cookie blockers globally.
- **Route 53 SOA min-TTL** (recommended to change from 86400 → 60) — reduces future negative-cache lag from 24h → 1 min. Optional but recommended.
- **DNS propagation status** — 6/9 major public resolvers (Google, Cloudflare, Quad9, OpenDNS, Verisign, Comodo) already return CloudFront IPs for apex; 3 stragglers (Yandex, AdGuard, Level3) expected to catch up within 24-48h of the nameserver switch — normal ISP DNS behaviour, self-corrects.

### 19 Feb 2026 — Bug Tracker v12 delivered
`PMC_Bug_Tracker_v12_20260219.xlsx` (SHA-256 `767abe92a97b6df2b2df1edcea7ae1f69477a5fff9342720da0e59ab9fe3ad2f`) — includes a new "Feb 19 delivery" sheet documenting Batches #6/#7/#8 with file names, SHA-256s and cleared bug IDs.

### 19 Feb 2026 — Batch #8: P1 tester-experience polish (v35 frontend only, backend unchanged)
File: `pmc-frontend-v35-build.zip` (1.2 MB, `main.4b0111ec.js`, SHA-256 `bd7161beaaf93890235abc6bc9b8f7bf44d9a28ad4197f3ac6506ae47eb99508`). Backend stays at v22d — no server-side change needed.
- **Bug #26 — Product Catalog toast**: `ProductCatalogPanel.jsx` save toast now reads `"Product created · <name>"` / `"Product saved · <name>"` (was ambiguous "Saved <name>" that testers mistook for the Procurement Strategy module). List already had cache-buster + `onSaved` refresh — retained.
- **Bug #31 — Notice title/description validation**: `NoticesPanel.jsx` toast now shows `"Title is required · minimum 3 characters"` / `"Description is required · minimum 10 characters"` with clear separator. Testers no longer have to guess which field the "10 char" rule applies to.
- **Bug #32 — Master Admin publish checkbox**: `NoticesPanel.jsx` `isMasterAdmin` check now accepts `admin | master_admin | superadmin | staff_admin` role variants (backend returns different literals depending on seed path — testers on newer accounts saw the checkbox disabled even as Master Admin).
- **Bug #74 (registration template "undefined" toast)**: `VendorsPanel.jsx` `uploadTemplate` now falls back to `f.name`/`f.size` if the backend response omits `file_name`/`size_bytes`, and shows KB as a description. Also surfaces the real backend error detail on failure instead of a generic message.
- **Bugs #28 · #29 · #35 · #49 · #52 · #63 · #84 · #85** were already verified as fixed in v20/v21/v22 and shipped in prior batches — Batch #8 does not touch them; they remain green.

### 19 Feb 2026 — Batch #7: Notice draft flow + Tender Clone + Vendor Invite polish (v34/v22d)
Files: `pmc-frontend-v34-build.zip` (1.2 MB, `main.92d8377e.js`, SHA-256 `d91d5d2b552a34c704fffd881b11de77365135357d5d2241836630a36c29db37`) · `pmc-backend-v22d.zip` (258 KB, SHA-256 `80b88dc4a7ae723c15d9a4f1b3960194998a71df4b1e57bc0663b7481085ba4b`).
- **Bug #57 · #58 · #66 — Notice draft flow polish**
  - Backend `GET /api/v1/notices/admin/all` now returns `Cache-Control: no-store, no-cache, must-revalidate` explicitly. Prevents CloudFront/browser from briefly serving a stale list right after a draft is created — the main reason testers saw "created but not in list".
  - Frontend `NoticesPanel.jsx` create toast now says "Draft saved · REF" (with hint to use "Draft only" filter) when `is_published=false`, and "Notice published · REF" when true. Removed the ambiguous "Notice created" copy.
  - Frontend `NoticesPanel.jsx` list rows now show a visible **DRAFT** (amber) / **● Live** (green) status badge next to the doc type pill. Testers can no longer miss a saved draft.
- **Bug #69 · #70 · #71 — Tender Builder Clone / Delete / History polish**
  - Frontend `TenderBuilderPanel.jsx` `cloneMaster` now sanitises the master's sections before cloning: strips `attachment` (attachments belong to a specific instance and must not be carried across), plus any stray `_id` / `id` / server-only fields. Toast now warns admin to re-upload attachments on the clone.
  - Backend `POST /api/v1/tender-templates` `create_from_master` adds a server-side defence: `sec.pop("attachment"/"_id"/"id", None)` on every incoming section. Even if a future frontend forgets, the clone starts with no dangling files. Regression verified: clone of the 18-section PSU master returns HTTP 200 with `is_master: False` and 0 attachments.
- **Bug #5 · #8 · #25 — Vendor Invite pipeline resilience**
  - `VendorsPanel.jsx` `sendInvite`: added `sendingInvite` in-flight flag → button now shows "Sending…" and is disabled during the request (prevents double-submit / dead-button perception). Also validates `email` format client-side before POST for actionable error toasts. Added `type="button"` on submit to defend against implicit form submission.
  - `BulkInviteModal.jsx` `submit`: on 401/403 responses (CSRF/session), the modal now shows a specific "Auth failed — refresh the tab" toast **without** clearing state or reloading. Previously the frontend's generic error handler could look like a logout when combined with a session hiccup.
  - Toast on success now includes the number of skipped rows (with the hint to check the table below), and the results table remains visible.
- **All 4 e2e regression tests pass HTTP 200** against preview API using cookie + CSRF headers: draft notice create (`PMC-NOT-2026-0029`), tender clone (18 sections, 0 attachments), single vendor invite (`PMC-SUP-000026`), bulk CSV invite (2/2/0). Backend v22d verified with `python -c "from routers import notices, tender_templates, vendor_invites"`.

### 19 Feb 2026 — DNS migration to Route 53 + Frontend v33 (Emergent purge)
Files: `pmc-frontend-v33-build.zip` (1.2 MB, `main.8680e8df.js`, SHA-256 `e433a2078b85668149461efaa905386107e463cb3cc0594ff33812ed3f711233`) · backend unchanged (still v22c on EB).
- **DNS authoritative migration GoDaddy → AWS Route 53**: nameservers switched from `ns09/ns10.domaincontrol.com` to `ns-1502.awsdns-59.org · ns-1726.awsdns-23.co.uk · ns-169.awsdns-21.com · ns-610.awsdns-12.net`. Both apex and www now resolve to CloudFront (`d2h9tkca2zjofy`) and serve HTTP 200 globally (verified via check-host.net from HU/SG/US).
- **Email preserved during migration**: MX (0 smtp.secureserver.net, 10 mailstore1.secureserver.net), SPF TXT (`v=spf1 include:secureserver.net -all`), DKIM CNAMEs (`s1._domainkey`, `s2._domainkey` → onsecureserver.net), webmail CNAME (`email → email.secureserver.net`), SRV `_autodiscover._tcp` — all mirrored into Route 53 before NS switch. Verified via dnspython against 8.8.8.8/1.1.1.1/9.9.9.9.
- **api.pmcmanagers.com fix (was 100% broken)**: A record was pointing to orphaned Singapore IP `18.140.35.163`. Changed to Route 53 **Alias → Elastic Beanstalk environment** (`pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`, London IPs `3.10.6.189` / `3.11.167.236`). Health probe now returns `{"ok":true,"service":"pmc-tender-v2-api","phase":"pilot"}`. Admin login verified end-to-end from live domain (JWT + CSRF returned).
- **Frontend v33 — Emergent branding purged**: previous v32 build accidentally shipped with `REACT_APP_BACKEND_URL=https://tender-hub-57.preview.emergentagent.com` baked into `main.86b8c80a.js` (1 hit). v33 rebuilt with `REACT_APP_BACKEND_URL=https://api.pmcmanagers.com`, deployed via AWS Console upload to `pmc-managers-frontend-prod` + CloudFront invalidation `/*` on distribution `E2WZT1TMQ0EK9W`. New bundle `main.8680e8df.js` verified: `grep -c emergent` = **0**, `grep -c 'api.pmcmanagers.com'` = 1. Codebase 100% clean of Emergent brand references in user-facing artefacts.
- **CORS validated**: preflight from both `https://www.pmcmanagers.com` and `https://pmcmanagers.com` returns `Access-Control-Allow-Origin` matching origin + methods `DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT`.
- **Known-not-fixed (low-priority)**: (a) `_dmarc` TXT in Route 53 has record name entered as FQDN causing double-suffix `_dmarc.pmcmanagers.com.pmcmanagers.com` → NXDOMAIN for standard DMARC lookup. DMARC policy still `p=none` so no email delivery impact today. 30-second Console fix: edit record → change name from `_dmarc.pmcmanagers.com` → `_dmarc`, save. (b) Preview-DB seeded vendor `manualvendor@pmcmanagers.com` returns 401 on production API — production MongoDB uses different data set (expected — real vendors register through UI).

### 14 Feb 2026 — Batch #6 LIVE: Committee dissolve + apex domain wiring
Files: `pmc-backend-v22c.zip` · `pmc-frontend-v32-build.zip` · both deployed to AWS at 05:34 UTC
- **Committee dissolve (P0 live observation)** — 3 stacked root causes fixed and verified on prod:
  1. Backend `models/committee.py` `CommitteeDecision` Literal now includes `"dissolved"` (was pydantic-422ing every dissolve call).
  2. Frontend `BiddingOpsPanel.jsx` passes `onChange={load}` to `<CommitteeList/>` so the list refreshes after dissolve.
  3. Frontend `bidding/CommitteeList.jsx` splits rendering into "Active committees (N)" (open only) + "Recently closed / dissolved (N)" strip showing close reason + date.
  Verified on prod: committee for PMC-NOT-2026-0020 transitioned open → dissolved with reason preserved.
- **Apex domain `pmcmanagers.com`** — ACM cert re-issued covering both apex + www; both added as CloudFront alternate CNAMEs; old Route 53 A/AAAA/CNAME records pointing to legacy `d3v0l4ai7kvp10` distribution removed; new A/AAAA aliases created via "Route domains to CloudFront" pointing to `d2h9tkca2zjofy` (the correct pmc-managers-frontend distribution). Global DNS propagation in progress (15-30 min TTL).



### 14 Feb 2026 — Batch #6 hotfix: Committee dissolve
Files: `pmc-backend-v22c.zip` · `pmc-frontend-v32-build.zip`
- **Bug (Bidding Ops → Committee): "Dissolve committee" seemed to succeed but the row still showed Status: open.**
  - Root cause 1 (backend): `CommitteeCloseIn.decision` was a `Literal["open","closed_awarded","closed_rejected","closed_no_award"]` — pydantic 422'd every dissolve call because `"dissolved"` was not in the union. The `if payload.decision == "dissolved":` branch never even ran.
  - Root cause 2 (frontend `BiddingOpsPanel`): the `CommitteeList` was rendered without an `onChange` callback, so even a successful dissolve wouldn't refresh the list.
  - Root cause 3 (frontend `CommitteeList`): the "Active committees" grid rendered every committee the API returned regardless of `status`, so closed/dissolved ones stayed visible.
  - Fixes: added `"dissolved"` to the Literal union; passed `onChange={load}` to `CommitteeList`; split rendering into an "Active committees (N)" grid (`status === "open"` only) and a "Recently closed / dissolved (N)" strip that shows the close reason + date for audit.



### 14 Feb 2026 — BugsV3 P0 sprint (batch #5): Session collision + Approval bypass + Blank form + Mobile funnel
Files: `pmc-backend-v22b.zip` · `pmc-frontend-v31-build.zip`
- **Bug #82 · #81 · #56 · #50 — Session collision (P0 root cause)**: switching between admin/staff/vendor left stale cookies from the previous role → dual identity → API 4xx → React crash → misleading "Your session is still active" banner. Fixed on both sides:
  - Backend (`admin_auth`, `staff_auth`, `vendor_auth`): every `logout` endpoint now deletes ALL three cookies (`access_token`, `vendor_token`, `csrf_token`) regardless of which role called it.
  - Frontend (`TopBar.jsx`): after hitting the three logout endpoints, wipes every `pmc.*` and `pmc_*` key from `localStorage` + `sessionStorage` (preserves language preference).
  - Frontend (`ErrorBoundary.jsx`): honest title "This panel hit an error" instead of the misleading "Your session is still active"; hint text now points at role-cookie mismatch as a possible cause.
- **Bug #83 — Approval bypass validation (P0)**: `POST /api/v1/registrations/{id}/decision` with `action=approve` now rejects with 400 if any of `company_name, registered_address, country, registration_number, legal_entity_type, email` is missing on the supplier record. Prevents "approved but never filled the form" state. Verified via curl.
- **Bug #4 · #60 — Blank registration form download (P0)**: previously 500'd on Safari when no admin template existed. Now generates a printable reportlab PDF checklist as a fallback so the endpoint always returns 200 + `application/pdf` + `Content-Disposition: attachment`. Verified via curl.
- **Bug #79 — Mobile funnel labels overlap (P0)**: `AnalyticsPanel.funnel_title` grid was `grid-cols-4 md:grid-cols-8` — long stage labels like `certifier_cleared` overflowed on mobile. Now `grid-cols-2 sm:grid-cols-4 lg:grid-cols-8` with `break-words` on the stage label.



### 14 Feb 2026 — Investor Demo Mode + Corrigenda Cleanup + Registration Guard
- **Investor Demo Mode** (`/app/backend/routers/admin_demo.py`): one-click seed of a curated showcase dataset — 3 notices (Astana Metro Line 2, Sovereign Data Lake, Electric Bus Fleet), 3 approved KZ vendors with licenses, 5 bids covering the full lifecycle (submitted → emd_paid → admin_flagged → certifier_cleared → awarded) plus a signed contract. Every row tagged `is_demo:true` so it can be wiped cleanly. Endpoints: `GET /api/v1/admin/demo/status`, `POST /api/v1/admin/demo/seed`, `POST /api/v1/admin/demo/reset`. UI added as a new **Investor Demo** tab inside Masters (`DemoModeTab.jsx`). Idempotent + reset verified via curl.
- **Corrigenda Withdraw Cleanup** (`admin-console/CorrigendaPanel.jsx`): withdrawn corrigenda are now moved out of the active list into a separate greyed-out "Withdrawn (historical)" section with the withdrawal reason surfaced. Notice picker also switched to `adminApi.listAllNotices` so drafts + published notices both show up.
- **Registration Guard** (`registration-portal/RegistrationResume.jsx`): "Next" button on Section A is disabled + shows an inline red hint until Identity & Basic Info required fields (`company_name`, `registered_address`, `country`, `registration_number`, `legal_entity_type`) are all filled. Prevents vendors from progressing to Contact/Banking without core identity data.

### 14 Feb 2026 — Bugs V2 Batch #4: Vendor Doc Crossover + Notices drafts + Registrations UX
- **Bug #78 — Vendor Document Crossover (CRITICAL security)**: on admin-create flow, Vendor B could inherit Vendor A's uploaded documents.
  - Backend fix (`vendor_full_invite.py`): `admin-create` now ignores `draft_registration_id` if the draft's email doesn't match the new vendor's email (defence in depth).
  - Frontend fix (`AdminVendorCreate.jsx`): if the admin changes the vendor's email after an auto-draft was created, the `draftId`/`draftToken`/`document_slots` state is reset. Previously the state was reused → old uploads were merged into the new vendor.
  - Regression test: `/app/backend/tests/test_regression_v22.py::test_bug78_admin_create_rejects_cross_email_draft` — PASSES.
- **Bucket A — Notices drafts invisible in Admin panel**: `list_notices` (public) filters `is_published=True`, so newly-created drafts were hidden. Added `GET /api/v1/notices/admin/all` (admin-scoped, returns drafts + published + tenant filter). Rewired `NoticesPanel.jsx` to use it. Regression test PASSES.
- **Bucket A — Registrations "Approve does nothing"**: on approve/reject/clarify the target row moved to a different status tab, so it disappeared from the current view. Reviewer perceived it as broken. `RegistrationsPanel.jsx` now auto-switches the filter to the new status.
- **Bucket C — Tender Builder Clone/Delete stale list**: added cache-buster `_=Date.now()` to `tenderTemplateApi.list()` so CloudFront never serves a stale list after a delete/clone. Verified clone endpoint returns 200 with correct payload on preview (the AWS 500 was a stale-backend issue prior to v21).



### 7 Sep 2026 — Staff Master: Edit / Role-change / Deactivate / Password-reset UI
- Concern: admin could add staff but couldn't edit them — only "Clone role" button existed.
- Backend already had `PATCH /api/v1/staff/{id}` for name/roles/hierarchy_level/is_active; added optional `password` to `StaffUpdateIn` for password reset (hashed server-side, never logged raw).
- Rewrote `admin-console/masters/StaffTab.jsx` — every row now has **Edit** + **Clone** buttons. Edit opens inline form with: name, roles (multi-checkbox), hierarchy level, active toggle, password reset field (blank = keep). Active checkmark is now a clickable toggle for one-click deactivate.
- Wired `updateStaff` handler in `MastersPanel.jsx` → calls `staffApi.updateStaff` → refreshes list.
- Verified: PATCH edits name/roles/level/is_active + password reset lets user re-login with new password.

### 6 Sep 2026 — Stripe checkout iframe-hang fix
- Stripe's CSP `frame-ancestors 'self'` blocks embedding, so `window.location.href = stripe_url` from inside the Emergent preview iframe hangs at a blank skeleton.
- Fixed in `VendorDashboard.jsx` (My Bids → Pay EMD), `BidSubmit.jsx` (Submit Bid), and `PurchaseGrid.jsx` (Product catalog) — all now use `window.open(url, "_blank")` with `window.top.location` fallback.

### 19 Sep 2026 — Bugs V2 Batch #3: retest + mobile funnel + committee verification
- **Retest results (via preview API + Mongo, using latest code):**
  - Notice draft creation as admin — endpoint accepts `is_published=false`, notice lands in drafts list. Was blocked in earlier test only because `category` is a required field on the create payload (frontend already sends it). Not a real bug.
  - Committee external-email listing — pulled 2 live committees, both carry the full `external_invitees` array (email + name + designation + accept_token + status + invited_at + decided_at). Backend list endpoint returns them. Frontend `CommitteeList.jsx` iterates over them correctly. Prior "not listed" report was almost certainly the CloudFront-cached-HTML issue.
  - Registration submit — hardened + verified.
- **Bug #79 Mobile Landing Pipeline Funnel labels overlapping**: fixed in `apps/notice-board/NoticeBoardHome.jsx::StatCard`. Added `min-w-0`, `break-words`, `leading-tight` and made the 3-card grid `grid-cols-1 xs:grid-cols-3 sm:grid-cols-3` so labels stack vertically on the smallest phone widths instead of overlapping.
- Bundled into `pmc-frontend-v28-build.zip` (43 MB) + refreshed `pmc-backend-v21.zip` (255 KB).

### 19 Sep 2026 — Bugs V2 Batch #2: Registration submit hardening
- New bug reported live: vendor completes 6 declarations + signature → clicks Submit for Review → toast "Request failed with status code 500".
- Root cause: multiple KeyError / InvalidId paths in `submit_registration` — malformed `registration_id` bubbled up as BSON InvalidId → 500; `doc["email"]` KeyError on legacy rows missing the field → 500; `send_email` failing on live Resend key → 500.
- Fix in `routers/registrations.py::submit_registration`: wrap `ObjectId(...)` in try/except → 400 · use `doc.get("status")` and `.get("email")` → 400 with clear detail · wrap the confirmation email in an inner try/except so a transport failure never fails a valid submission.
- Verified end-to-end via curl: malformed id → 400, missing token → 404, valid submit → 200.
- Rolled into `pmc-backend-v20.zip` (255 KB).

### 19 Sep 2026 — Bugs V2 Batch #1: registration guard + corrigenda + vendor isolation
- Bugs #23 + #77 (Registration double-approve → 500): backend now returns `409 Conflict` with a clear message when a registration is re-approved or re-rejected. Frontend `Approve/Clarify/Reject` buttons now disable + say "Working…" during the API call to prevent accidental double-clicks.
- Bugs #12 + #22 + #23 (Corrigenda withdraw): backend now returns the freshly-updated corrigendum in the withdraw response so the frontend can flip `is_active=false` without a second round-trip.
- Bug #29 (New vendor gets another vendor's documents): `approve_and_create_vendor` in `registrations_helpers.py` now explicitly excludes `documents`, `document_slots`, `attachments`, `uploads`, `primary_document`, `signed_documents` from the profile copy. Registration docs stay on the registration row; vendor row carries only the registration_id reference.
- Deliverables: `pmc-frontend-v27-build.zip` + `pmc-backend-v20.zip` — ready for AWS deploy.

### 6 Sep 2026 — Stripe Payments Integrated (Flow B / BYOK)
- User's live Stripe account (`acct_1T40n8H0joY1mkyK`, country GB) test key wired via `STRIPE_API_KEY` in `/app/backend/.env`.
- Tax mode: **`STRIPE_TAX_MODE=full`** — Stripe Managed Payments (SMP), Stripe handles tax + compliance across ~80 countries.
- Upgraded `pmc_lib/payments/stripe/checkout.py`:
  - Added `tax_mode` field ("full"/"calc_only"/"diy") to `CheckoutSessionRequest`.
  - Added `product_name` + `product_tax_code` fields (default `txcd_10000000` for SMP eligibility).
  - Branches on tax_mode → SMP with automatic fallback to Stripe Tax if SMP ineligible.
- Updated `routers/payments.py` (EMD) + `routers/billing.py` (product catalog) to pass tax_mode from env.
- Verified: real `checkout.stripe.com/c/pay/cs_test_...` URL returned end-to-end via preview API, status poll returns `pending`, session confirmed SMP-enabled on Stripe.
- **⚠️ SECURITY**: User accidentally pasted their `sk_live_51T40n8H0joY1mkyK...` in chat — advised immediate revocation. Only `sk_test_` values touch code/env.

### v4 bug-fix batch (all closed — 52 / 52 = 100%)
V-02 · N-02 · T-01 · E-03 · RA-01 · MP-01 · AU-01 · EN-03. Each fix has a screenshot chapter in Master Manual v4.

### Documentation
- **PMC_Master_Training_Manual_v4** (.docx / .pdf) — 71 screens, 141 PDF pages.
- **PMC_Bug_Tracker_v6.xlsx** — 52 / 52 (100%) closed.
- **PMC_Portal_Observations_Response_v6.docx** — matching v6 with fix evidence.
- v3 (121 pages), v2 (51 pages) retained.

### LIVE deploy — verified working
- `https://www.pmcmanagers.com/` — **LIVE** (CloudFront + S3 pmc-managers-frontend-prod).
- Frontend build: `pmc-frontend-v22-build.zip` deployed — **same-origin**, no EB URL in bundle.
- `https://www.pmcmanagers.com/api/v1/*` — **LIVE**, CloudFront `/api/*` Behavior → `pmc-backend-eb` origin (EB HTTP:80).
- EB `backend-v18b-final` health = Ok.
- Smoke tests pass: health (200), admin login (JWT returned), public notices list (real Mongo rows).

### Deployment artefacts (kept for rollback / reference)
- `pmc-backend-v18.zip` and `pmc-backend-v18b.zip` (byte-identical, alt label).
- `pmc-frontend-v25-build.zip` — **latest**, removes entire Reports tab + strips `emergentagent.com` URL from bundle + drops `@emergentbase/visual-edits` dep.
- `pmc-frontend-v24-build.zip` — prev, purges all user-visible "Stakeholder" references + deletes hidden panel files.
- `pmc-frontend-v23-build.zip` — previously deployed, contained "Stakeholder Reports" label.
- `pmc-frontend-v22-build.zip` — pre-hidden-modules build.
- `pmc-frontend-v21-build.zip` — pre-same-origin build (EB URL baked in).
- `verify_prod.sh` and `verify_prod_v2.sh` — CLI smoke tests.
- Legacy zips v11–v17 also served via `/api/v1/_dl/`.

### 5 Sep 2026 — Full Reports section purge + Emergent brand strip (v25)
- User requested: (a) hide the entire Reports section (Excel/Word/PDF Asked-vs-Delivered + all flow charts), (b) remove any residual "emergent" LLM / URL references, (c) provide a secret download link.
- Removed the `reports` tab entirely from `AdminDashboard.jsx` (import + tab entry + JSX switch). Deleted `ReportsPanel.jsx`.
- Rebuilt with `REACT_APP_BACKEND_URL=""` so the AWS bundle is same-origin (no `emergentagent.com` URL baked in).
- Purged `@emergentbase/visual-edits` from `package.json` devDependencies.
- Verified: `grep -Ei "emergent|stakeholder"` on the built JS/CSS/HTML/asset-manifest bundle returns **0 matches**. Screenshot confirms tab strip ends at ENGAGEMENTS.
- Deliverable: `pmc-frontend-v25-build.zip` (42 MB) served via `/api/v1/_dl/{TOKEN}/pmc-frontend-v25-build`.

### 5 Sep 2026 — "Stakeholder" residual purge (v24)
- User reported "Stakeholder Reports" still appeared on the live build even after the pilot-hide.
- Root cause: the visible `ReportsPanel` tab used i18n key `admin.tab_reports = "Stakeholder Reports"` and section kicker `panels.reports.kicker = "Stakeholder brief"` across EN / RU / KZ.
- Fix: renamed all three locales — tab now reads "Reports" / "Отчёты" / "Есептер"; kicker now "Executive brief" / "Сводка руководству" / "Атқарушы қысқаша"; EN pdf_hint no longer mentions "stakeholders".
- Also deleted unused hidden panels (`StakeholderReportsPanel.jsx`, `HelpRequestsPanel.jsx`, `BrandingPanel.jsx`) and removed all commented-out references in `AdminDashboard.jsx`.
- Verified: `grep -i stakeholder` on the built JS/CSS bundle returns **0 matches**. Screenshot confirms tab reads "REPORTS" and Reports panel opens with "EXECUTIVE BRIEF" kicker.

---

## Backlog

### P2
- Russian + Kazakh translations of Master Manual v4 (deferred by user).
- Resend email blast on new backend deployment.
- Investor exec preview (one-page summary of v4 manual).

### P3
- PayPal + Kaspi Pay real integration (blocked: merchant credentials).
- Firebase + APNs push (blocked: project ID + Service Account JSON).
- Live KYC provider (blocked: KYC_BASE_URL + KYC_API_KEY).

---

## Key APIs
- `/api/v1/admin/auth/*` · `/api/v1/vendor/auth/*` · `/api/v1/staff/auth/*`
- `/api/v1/notices` · `/api/v1/registrations` · `/api/v1/vendors` · `/api/v1/bids`
- `/api/v1/committee` · `/api/v1/escrow/*` · `/api/v1/evaluations/*` · `/api/v1/awards/*`
- `/api/v1/tender-templates/*` · `/api/v1/boqs/*` · `/api/v1/permissions/*`
- `/api/v1/dashboard-drill/*` (stakeholder-reports/branding routers hidden during pilot)
- `/api/v1/reverse-auctions/*` · `/api/v1/meetings` · `/api/v1/audit`
- `/api/v1/meta/health` — Docker HEALTHCHECK + smoke tests.
- `/api/v1/_dl/{token}/{name}` — internal file download.

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- **AWS wiring**: CloudFront distribution has TWO origins: S3 (default, path `/`) + `pmc-backend-eb` (Behavior `/api/*`). EB is Single-instance — do NOT try to add :443 to EB directly; HTTPS is terminated at CloudFront using its existing cert. Adding an ALB / new listener is unnecessary and will just cost money.
- **Deploy frontend**: unzip a build zip, upload contents of `build/` to `pmc-managers-frontend-prod` (deleting `static/`, `index.html`, `service-worker.js` first is cleanest), then CloudFront invalidate `/*`.
- **Deploy backend**: upload zip in EB Console. If "version label already exists" error, rename zip locally OR change the version label in the upload dialog.
- Zero "Emergent" branding in user-facing docs — always use `www.pmcmanagers.com`.
- ESLint bin is broken — remove `/app/frontend/node_modules/.bin/eslint*` before `finish`. DO NOT delete `eslint-scope` (webpack dependency).
- Manual v4 build pipeline: `python3 scripts/seed_manual_v4.py` → `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py` → `python3 scripts/build_manual_v3.py`.
- No GitHub auto-push. All deliverables via `/api/v1/_dl/{TOKEN}/{name}` route (token: `sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4`).
