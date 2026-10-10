# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v52bl — Evaluation crash fix + EMD on public page + Notice validation + Engagements meetings + Masters Currencies tab (10 Oct 2026)

Backend
- `routers/notices.py`
  - `_out()` now computes a flat `emd_amount` / `emd_currency` / `emd_percentage`
    from `emd_config` + `budget_amount` so the public notice page can display
    real EMD figures instead of "—".
  - `POST /notices` rejects `budget_amount <= 0` (422) and rejects notices with
    no positive EMD (either `fixed_amount > 0` or `percentage > 0`) — fixes
    "notices with 0 are being created".
- `routers/packages.py` — new `GET /api/v1/packages/import/sample.csv` returns
  a 3-row sample matching the importer schema (title, category, phase, value,
  currency, float_target_date, status).
- `routers/engagements.py` — new `POST /{eid}/meetings` and `GET /{eid}/meetings`.
  Lightweight PMC-internal meetings; stored on the engagement doc, audit-logged,
  best-effort buyer email via `notify.vendor_confirm`.
- `routers/engagements.py` — `POST /{eid}/cancel` already required a reason;
  frontend now matches with a modal instead of `window.confirm`.

Frontend
- `apps/admin-console/evaluation/AwardReport.jsx` — guard against partial
  reports: `return null` when `report.notice_ref` missing, and read
  `report.rubric?.minimum_technical ?? 60` so the else-branch never crashes.
- `apps/admin-console/EvaluationPanel.jsx` — passes `report` directly (not
  `report || {}`) so AwardReport's new guard fires correctly.
- `lib/pmcELiveData.js` `useNoticeDetailLive`:
  - EMD facts cell now reads the flat `emd_amount`/`emd_percentage`/`emd_currency`
    fields with legacy `emd_config` fallback.
  - **Key dates timeline** patched from real notice data (`published_at`,
    `corrigenda[*]`, `clarification_deadline`, `pre_bid_meeting_date`,
    `submission_deadline`) — replaces hard-coded Sep 2026 demo dates.
  - Submission countdown + "closes" datetime in the aside now reflect
    `notice.submission_deadline`.
- `apps/admin-console/NoticesPanel.jsx` — client-side block when
  `budget_amount <= 0` or EMD missing (fixed/pct both zero).
- `apps/admin-console/EngagementsPanel.jsx` — new `CancelModal` (reason
  textarea, min 5 chars) + new `MeetingModal` (date/time, duration, agenda,
  attendee role, link, prints agenda).
- `apps/admin-console/PackagesPanel.jsx` — "Sample CSV" link (`pkg-import-sample`)
  next to "Import CSV".
- `apps/admin-console/masters/CurrenciesTab.jsx` (NEW) — full CRUD UI backed by
  `/api/v1/masters/currencies`: add, edit (name/symbol/decimals), deactivate.
- `apps/admin-console/MastersPanel.jsx` — new tab chip "Currencies" between
  Categories and Legal entity types.

### L1 comparison logic (plain-English explainer, no code change)
1. **Scope**: run only on **published** notices with at least one bid; drafts
   admins can dry-run too via `adminApi.listAllNotices`.
2. **Eligibility filter**: drop withdrawn / non-cleared bids. A bid is kept
   only if its **Technical envelope is cleared** (`technical_clear=True`).
3. **Compliance flags per bid** (don't disqualify alone):
   `missing_price`, `no_documents`, `no_technical_docs`, `no_commercial_docs`,
   `above_budget_150pct`, `suspiciously_low` (<40 % of budget).
4. **Normalisation**: all `price_amount` values converted to the notice's own
   currency (`FX_TO_USD` map in `pmcELiveData`) so cross-currency bids compare
   like-for-like.
5. **Sort**: ascending by normalised price → the lowest compliant bid is L1.
6. **Tie-breaker**: by submission timestamp (earliest wins). If still tied, by
   vendor rating.
7. **Output**: the Engine returns `{ eligible_count, l1_winner, flags_per_bid }`;
   the UI shows the winner banner + flagged-bids pills.
8. **Audit**: every L1 run is written to the ledger (`l1.run` event) with input
   bid refs so an auditor can reproduce the shortlist.

Verified visually (iteration smoke): Evaluation panel no longer crashes;
Masters → Currencies lists 20+ seeded ISO codes; Engagements cancel modal
opens with required reason input.

---



## v52bk — Currency master + auth-aware public chrome + hardened Create Notice (10 Oct 2026)

Backend
- New `routers/currencies.py` with ISO-4217 CRUD under `/api/v1/masters/currencies`:
  - `GET /currencies/public` (anon) + `GET /currencies` (admin/reviewer/support/committee)
  - `POST` / `PATCH` / `DELETE` (admin only; DELETE = soft deactivate)
  - `seed_defaults()` idempotent — 25 common currencies on cold start (USD, EUR, GBP, INR, KZT, AED, SAR, RUB, CNY, JPY, SGD, AUD, CAD, CHF, HKD, ZAR, TRY, BRL, QAR, OMR, KWD, BHD, UZS, KGS, AZN).
  - `CurrencyIn.symbol` capped at 8 chars.
- Wired into `server.py` startup after `_seed_categories()`.

Frontend
- `lib/useAuthSession.js` — probe hook that calls admin/staff/vendor `/me` with
  `_skipAuthRedirect: true` so public pages can detect auth without hijacking
  the UI on 401.
- `lib/api.js` — axios response interceptor honours `config._skipAuthRedirect`.
  `mastersApi.listCurrencies` / `listCurrenciesPublic` / CRUD helpers added.
- `apps/shared/TopBar.jsx` — on public routes, when signed-in: hides
  Sign in / Register, shows `Dashboard` chip (avatar + label) + `Sign out`
  (testid `topbar-dashboard`, `topbar-signout-public`; mobile drawer equivalents).
- `apps/notice-board-e/NoticeDetailE.jsx` — hero `pmc-chrome` now auth-aware:
  anon → `notice-topbar-signin` + `notice-topbar-register`; signed-in →
  `notice-topbar-dashboard` + `notice-topbar-signout`. Start-bid / Download
  pack links also route to `/vendor/workspace/new?notice=<ref>` or the
  signed-in dashboard instead of `/register`.
- `apps/admin-console/NoticesPanel.jsx` Create Notice form:
  - `Category *` — hard-blocked, required <select> (toast if empty).
  - `Budget currency *` — static `<input>` replaced with 25-option master-driven
    `<select>` (`notice-currency`).
  - `Tender / RFP / RFQ documents *` — primary document is MANDATORY to submit.
    Row renders Upload / View / Modify / Print / Delete controls with testids
    `notice-primary-view`, `-modify`, `-print`, `-delete` once a file is picked.

Verified by testing_agent (iteration_49):
- Backend: 4/4 pytest (`test_v52bk_currencies.py`).
- Frontend: 12/12 scenarios — anon + admin + vendor header, 25-option currency
  dropdown, both block-paths (missing category, missing primary), happy-path
  POST `/notices` returning `PMC-NOT-2026-0035` as draft.

---



## v52bj — Stuck-bid recovery + losing-bidder EMD workflow (10 Oct 2026)

Backend
- `POST /api/v1/bids` 409 now returns `{code, message, existing_bid_id,
  existing_bid_ref, existing_status}` so the frontend can offer direct
  recovery actions.
- `POST /api/v1/bids/{bid_id}/decision` with `status=awarded` now:
  flags every other active bid on the notice as `non_winner`, sets
  `emd_refund_state="pending_release"` + `emd_refund_due_at` (today +
  `EMD_LOSER_RELEASE_DAYS`, default 14) when the bid holds a paid EMD,
  emails each losing bidder, and notifies the accounting role.
- `GET /api/v1/bids/admin/emd-refunds?status=` — list pending/released
  refunds (admin / accounting / auditor).
- `POST /api/v1/bids/{bid_id}/emd/release-to-vendor` — mark a loser's
  EMD released with external reference + audit log + vendor email.

Frontend
- `BidSubmit.jsx` renders two recovery buttons on a 409: **Open my bids**
  and **Withdraw stuck bid** (confirmation + `bidApi.withdraw`).

Release artifacts:
- `/downloads/pmc-frontend-v52bj-prod-build.zip`
- `/downloads/pmc-backend-v52bj.zip`
- `/downloads/DOWNLOAD_v52bj.md`

Deploy order: backend v52bj first, then frontend v52bj.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v52bi — HOTFIX: /api/v1/bids/mine 500 (10 Oct 2026)
- The v51bd draft-sync edit accidentally consumed the
  `@router.get("/mine")` decorator in `routers/bids.py`, orphaning
  `list_my_bids`; `/bids/mine` fell through to `/{bid_id}` with
  `bid_id="mine"` → `InvalidId` → 500 for every vendor's My Bids page.
- Restored the decorator; added a malformed-id 400 guard to `get_bid`.
- Verified: `/bids/mine` → 200 with 8 bids; `/bids/zzz` → 400.
- Backend-only hotfix: `pmc-backend-v52bi.zip` (+ `DOWNLOAD_v52bi.md`).
  Frontend stays on v52bh. Deploy backend v52bi first.
- LESSON: when search_replace anchors include a decorator/route boundary,
  always re-verify the full route table afterwards (`grep -n "@router"`).

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v52bh — Corrigenda acknowledgement deadlock + "[object Object]" toast (10 Oct 2026)
- Backend `routers/corrigenda.py`: `POST /corrigenda/{cid}/acknowledge` no
  longer requires an active bid — breaks the chicken-and-egg deadlock that
  produced HTTP 412 on bid submission for tenders with active corrigenda.
- Frontend `lib/api.js`: `formatApiError` renders structured 412 details
  (`{code, message, corrigenda:[…]}`) as readable text instead of
  "[object Object]".
- `BidSubmit.jsx`: inline corrigenda acknowledgement panel — lists every
  active corrigendum (title/summary/new deadline) with an acknowledge
  button; Submit disabled until all acknowledged.
- Verified: ack without a bid now returns `{ok:true}`; test corrigendum
  withdrawn after verification.
- Releases: `pmc-frontend-v52bh-prod-build.zip` + `pmc-backend-v52bh.zip`
  (+ `DOWNLOAD_v52bh.md`). Backend deploy REQUIRED this time.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v52bg — Vendor Intel modal UX fix (10 Oct 2026)
- Whitelist (and approve-with-whitelist) now auto-close the manage modal
  and return the admin to the triage list — the blacklist window no
  longer lingers.
- Added a visible ✕ header close button and restyled the bottom Close
  link into a full-width bordered button.
- Frontend-only: `/downloads/pmc-frontend-v52bg-prod-build.zip`
  (+ `DOWNLOAD_v52bg.md`). Backend unchanged from v52bf.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51bf — Vendor Intel readability fix (10 Oct 2026)
- Scoped CSS carve-out for `[data-testid="admin-vendor-intel-panel"]` +
  `[data-testid="blacklist-dashboard-panel"]` in `frontend/src/index.css`
  so the Option E theme no longer remaps slate text / white surfaces into
  cream-on-cream. Fixes unreadable triage KPIs, blacklist modal buttons
  (Upload document / View / Download / Print), and evidence rows.
- Frontend-only release: `/downloads/pmc-frontend-v51bf-prod-build.zip`
  (+ `DOWNLOAD_v51bf.md`). Backend stays on v51be.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51be — Appeal decision workflow + CSRF resilience (10 Oct 2026)

Bug fix
- `frontend/src/lib/api.js` — cache the `csrf_token` returned in
  admin/staff/vendor login JSON into sessionStorage and use it as a
  fallback when the JS-readable `csrf_token` cookie is dropped by
  strict-tracking / partitioned-cookie browsers. Fixes the "HTTP 403
  CSRF token missing or invalid" seen when clicking Blacklist in the
  preview environment.

Feature
- `routers/vendor_intel.py` — `POST /blacklist/{ref}/appeals/{idx}/decision`
  (admin-only, CSRF). `AppealDecisionIn{decision, note, whitelist}`.
  Updates the appeal with `status/decision_note/decided_by/decided_at`,
  optionally removes the blacklist, writes an audit log, and fires
  `vendor_confirm` + `notify_role("admin", …)`.
- Admin `VendorIntelPanel.jsx` — inline AppealRow with Approve / Reject
  buttons, note textarea, "Also whitelist on approval" toggle. Decided
  appeals display status badge, decider, timestamp, and note.

Release artifacts:
- `/downloads/pmc-frontend-v51be-prod-build.zip`
- `/downloads/pmc-backend-v51be.zip`
- `/downloads/DOWNLOAD_v51be.md`

Deploy order: backend v51be first, then frontend v51be.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51bd — Compliance triage, appeal notifications, draft server sync (10 Oct 2026)

Backend
- `routers/bid_drafts.py` (new) — per-vendor server-side bid drafts
  (`GET/PUT/DELETE /api/v1/bids/drafts/{notice_ref}` + `GET
  /api/v1/bids/drafts`). `POST /api/v1/bids` auto-deletes the matching
  draft on success.
- `routers/vendor_intel.py`
    - `GET /api/v1/vendor-intel/blacklist-dashboard` — one row per
      blacklist with evidence/appeal counts for compliance triage.
    - Appeal filed → `notify_role("admin", …)` + confirmation email to the
      vendor; whitelist decision → vendor "account whitelisted" email +
      admin notification.
- `server.py` — registers the new `bid_drafts` router.

Frontend
- `lib/api.js` — `bidApi.getDraft/saveDraft/deleteDraft/listDrafts`,
  `vendorIntelApi.blacklistDashboard`.
- `apps/vendor-portal/BidSubmit.jsx` — draft load prefers the server with
  localStorage fallback; "Save draft" pushes to the backend;
  successful submit clears both the local and the server draft.
- `apps/admin-console/BlacklistDashboardPanel.jsx` (new) — triage table
  with KPI tiles, search, filter chips, and a Manage button that opens
  the existing VendorIntel modal.
- `apps/admin-console/VendorIntelPanel.jsx` — renders the triage panel
  above the legacy summary table.

Release artifacts:
- `/downloads/pmc-frontend-v51bd-prod-build.zip`
- `/downloads/pmc-backend-v51bd.zip`
- `/downloads/DOWNLOAD_v51bd.md`

Deploy order: backend v51bd first (new endpoints), then frontend v51bd.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51bc — Bid submission UX + blacklist/appeal (10 Oct 2026)

Fixes:
- Vendor "View" button on uploaded Technical/Commercial PDFs no longer
  returns `401 Sign in to download tender documents`. The file is now
  fetched through the authenticated axios client (`uploadsApi.openInNewTab`)
  and streamed as a blob URL.
- `412` and other submit errors now surface the real backend detail in the
  toast title (`Submission blocked — pre-condition failed · KYC verification
  required…`) instead of the generic "Something went wrong".
- Backend requires BOTH Technical and Commercial envelope PDFs on
  `/api/v1/bids` POST (adds a commercial-doc check next to the existing
  technical check).

Vendor Intelligence — blacklist, whitelist, evidence, vendor appeal
(models + routes in `routers/vendor_intel.py`):
- `GET /vendor-intel/blacklist/{ref}` — admin fetches full record
- `POST /vendor-intel/blacklist/{ref}/evidence` — admin attaches doc/photo
- `PATCH /vendor-intel/blacklist/{ref}/evidence/{idx}` — admin edits note
- `DELETE /vendor-intel/blacklist/{ref}/evidence/{idx}` — admin removes
- `DELETE /vendor-intel/blacklist/{ref}` — whitelist / full removal
- `GET /vendor-intel/my-blacklist` — vendor sees their own record
- `POST /vendor-intel/my-blacklist/appeal` — vendor submits an appeal
- `POST /vendor-intel/my-blacklist/appeal/evidence` — vendor attaches
- `DELETE /vendor-intel/my-blacklist/appeal/evidence/{idx}` — vendor removes

Frontend:
- `components/EvidenceManager.jsx` — reusable widget with upload-document,
  capture-photo (`<input accept="image/*" capture="environment">`), view,
  download, print, delete, optional per-item note. Used on both admin and
  vendor sides.
- Admin `VendorIntelPanel.jsx` modal: emerald "Whitelist / remove from
  blacklist" with confirmation, admin evidence manager, vendor appeals
  (read-only evidence viewer).
- `VendorBlacklistAppeal.jsx` rendered at the top of `VendorHomeE` for
  blacklisted vendors: shows reason + timestamp, lets them submit an
  appeal and attach documents or camera-captured photos.

Release artifacts:
- `/downloads/pmc-frontend-v51bc-prod-build.zip` (~3.0 MB)
- `/downloads/pmc-backend-v51bc.zip` (~529 KB) — EB root-level Docker layout
- `/downloads/DOWNLOAD_v51bc.md`

Deploy order: backend v51bc FIRST (new endpoints) → frontend v51bc.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51bb — Admin add-vendor UX fixes (10 Oct 2026)
- Back button on `/admin/vendors/new` now reads "Back to vendors" and lands on
  the Vendors tab (`/admin?tab=vendors`) — same as Edit full profile.
  EN/RU/KZ labels updated.
- Verified Section D "Business categories" is database-driven (Categories
  master, `GET /api/v1/masters/categories/public` — 105 categories). Not
  hardcoded; no change required.
- Brighter, higher-contrast styling for the admin vendor create + edit forms
  (scoped CSS carve-out): light-grey page, white raised card, dark-slate
  labels, 1.5px visible input borders, dark-green focus ring, emerald info
  banner on the create page.
- Frontend-only release: `/downloads/pmc-frontend-v51bb-prod-build.zip`
  (+ `DOWNLOAD_v51bb.md`). Backend stays on v51ba.

---


# PMC Managers v2 — PRD (last touched 10 Oct 2026)

## v51ba — Admin bid detail & Award record (10 Oct 2026)
- Fixed cream-on-cream unreadable text in the admin bid detail page by
  adding a scoped CSS carve-out for `[data-testid="admin-bid-page"]`
  (`frontend/src/index.css`).
- Added a dedicated **Award Record** panel on `/admin/bids/:bidId` that
  shows, for awarded bids only:
    * award ref, PO no., awarded by/at
    * tender ref, title, delivery country, published date, submission deadline
    * bid submission, technical cleared, financial opened timestamps
    * winning vendor + awarded price
    * lifecycle sign-offs (escrow, PMC admin, certifier, legal, accounts, committee)
    * escrow dual-signature ledger entries (PMC + institution officer stamps)
    * DocuSign envelopes with completion timestamps
    * Print Award Letter / Download PDF, Print Contract / Download PDF
- New admin-only backend endpoints under `routers/awards.py`:
    * `GET /api/v1/awards/bid/{bid_id}/summary`
    * `GET /api/v1/awards/bid/{bid_id}/award-letter.html`
    * `GET /api/v1/awards/bid/{bid_id}/award-letter.pdf`
    * `GET /api/v1/awards/bid/{bid_id}/contract.html`
    * `GET /api/v1/awards/bid/{bid_id}/contract.pdf`
- Verified end-to-end against awarded bid `PMC-BID-2026-00005`
  (award ref `PMC-AWD-2026-00003`): page readable, summary API returns
  full timeline, HTML print view renders, PDF export streams
  WeasyPrint-rendered A4 (admin-only — 401 without auth, 404 for
  non-awarded bids).
- Release artifacts:
    * `/downloads/pmc-frontend-v51ba-prod-build.zip` (≈ 3.0 MB)
    * `/downloads/pmc-backend-v51ba.zip` (≈ 523 KB)
    * `/downloads/DOWNLOAD_v51ba.md`

---


# PMC Managers v2 — PRD (as of Feb 2026 — Mobile App Store Stream)

## Current Objective
Publish PMC Managers to the Apple App Store and Google Play under
**THE PMC MANAGERS LTD** (UK Co. 17031540, D-U-N-S **234578668**,
Chiswick Park, London W4 5YG), as a unified Capacitor app with
Public / Vendor / Buyer / Admin roles.

## Mobile stream — current status
| Milestone | Status |
|---|---|
| D-U-N-S Number acquired | ✅ 234578668 |
| Apple Developer Program enrollment | 🟡 user filling form now |
| Google Play Console enrollment | 🟡 Identity docs submitted, under Google review (few days). Phone verification (+447724545222) gated behind identity approval. App creation locked until all verifications complete. ⚠️ Public developer name currently "Harneet" (was "Shweta Vaswani") — recommend changing to "PMC Managers" |
| Capacitor 8 native projects scaffolded | ✅ `/app/frontend/android` + `/app/frontend/ios` |
| Native project archives for the dev machine | ✅ `pmc-mobile-android-v1.0.0.tar.gz`, `pmc-mobile-ios-v1.0.0.tar.gz` |
| App icon 1024×1024 | ✅ `mobile_assets/icon_1024.png` |
| iOS launch screen | ✅ `mobile_assets/splash_portrait.png` |
| Google Play feature graphic 1024×500 | ✅ `mobile_assets/android_feature_1024x500.png` |
| iOS 6.7" screenshots (Public / Vendor / Admin / Auction) | ✅ 4 shots |
| Android phone screenshots (Public / Vendor / Admin / Auction) | ✅ 4 shots |
| Website ownership verified (Search Console) | ✅ "Ownership verified" via HTML tag (07 Oct 2026) — the `google-site-verification` meta tag in `public/index.html` must NEVER be removed, or verification is revoked |
| Store asset bundle | ✅ `pmc-mobile-store-assets-v1.0.0.zip` (13 files: 3 brand assets + 10 store screenshots + README) |

## Account email
`managerspmc@gmail.com` (both Apple ID and Google Account owner).

## Mobile build identity
- `appId` / Bundle ID: `com.pmcmanagers.tenders`
- Device name: `PMC Tenders`
- Store listing title: `PMC Managers`
- Marketing version: `1.0.0` • build / versionCode: `1`
- Palette: forest green `#0b3d2e`, navy `#0b1e3f`, brass `#d4af37`

## Store-submission docs (`/app/docs/store_submission/`)
- `PMC_APP_STORE_PLAY_STORE_MASTER_GUIDE.md`
- `GOOGLE_PLAY_ACCOUNT_SETUP_WALKTHROUGH.md`
- `GOOGLE_PLAY_SIGNUP_CHEATSHEET.md` (field-by-field for in-form filling)
- `APPLE_DEVELOPER_ACCOUNT_SETUP_WALKTHROUGH.md`
- `NATIVE_APP_BUILD_INSTRUCTIONS.md`
- `/app/scripts/scaffold_native_apps.sh`
- `/app/scripts/generate_app_icons.py`

## Downloadable deliverables (preview-hosted)
- `/downloads/pmc-mobile-android-v1.0.0.tar.gz`
- `/downloads/pmc-mobile-ios-v1.0.0.tar.gz`
- `/downloads/pmc-mobile-store-assets-v1.0.0.zip`
- `/downloads/MOBILE_STORE_ASSETS_README.md`
- `/downloads/DOWNLOAD_mobile_v1.0.0.md`

## Latest web releases
- **v51az** — Bidding Ops video-verified fixes: pipeline step tiles now
  clickable with stage filtering + active highlight (they had counters but
  no click handler); Review / Open bid restored to full-page navigation
  (`/admin/bids/{id}`). Frontend-only.
- **v51ay** — Bidding Ops usability: supplier rows now always show Review
  alongside Send link; detail panel notice ref is a link to the public
  notice page; new Envelope documents block with direct download links;
  removed double panel re-open after hold/resume/reject. Frontend-only.
- **v51ax** — Bug-sheet clearing batch: DocuSign envelope completion now
  stamps bids by `_id` ObjectId (was `{"id": ...}` which silently matched
  nothing — vendor status never flipped, xlsx #17); $0-EMD bids no longer
  stuck at Step 4 (`emdSettled = emdDue <= 0 || emdOutstanding === 0`,
  xlsx #14); registration number fields accept commas (employees +
  turnover inputs switched from `type=number` to text + comma-stripping
  parse, xlsx #11). Corrigendum-public verified as correct pipeline
  (is_active=true → public endpoint attaches). Bundles:
  `pmc-frontend-v51ax-prod-build.zip` + `pmc-backend-v51ax.zip`.
- **v51aw** — Register-on-behalf `*` marks sweep completed across Sections
  B (contact/signatory), C (banking) and E (signature block). Backend
  unchanged (still v51au).
- **v51av** — Blacklist modal stale-state fix (button flips immediately),
  `Field.required` prop + red `*` marks, "Save & next →" button in
  AdminVendorCreate, DocuSign key-rotation walk-through.
- **v51au** — P0/P1 closing batch: Evaluation page crash guard, NIT public
  download fix (`/api/v1/uploads/public-files/{key}` anon endpoint +
  NoticeDetail attachment links), Stakeholder Reports link restored to
  Bidding Ops sidebar.
- **v51at** — L1 Award page crash guard, vendor-list cache-bust after approve,
  PDF-only enforcement on bid envelope dropzones.
- **v51as** — Bidding Ops "Review" button opens inline detail panel instead
  of navigating away; "Invited undefined" toast hardened.
- **v51ar** — Login-page escrow registration entrypoint.
- **v51aq** — Duplicate escrow transaction guard (409), admin cancel row,
  release CSV export, EMD ledger search bar.

## Mobile Store Status
- **Google Play Developer Console**: **SUBMITTED FOR REVIEW** 🚀
  - App ID: `com.pmcmanagers.tenders` (PMC Managers — Tender Management)
  - Release: `1 (1.0.0)` signed production `.aab` (Target SDK 36, 7.73 MB)
  - Distribution: 177 countries & regions + rest of world
  - Policy & Store Listing: Complete with IARC PEGI 3 rating, 18+ audience, data safety, full copy & graphics.
  - Review Status: In Review with Google Play team (~2-5 business days).

- **Apple App Store**: Ready for next phase (Xcode project archive + TestFlight upload).
  download fix (`/api/v1/uploads/public-files/{key}` anon endpoint +
  NoticeDetail attachment links), Stakeholder Reports link restored to
  Bidding Ops sidebar.
- **v51at** — L1 Award page crash guard, vendor-list cache-bust after approve,
  PDF-only enforcement on bid envelope dropzones.
- **v51as** — Bidding Ops "Review" button opens inline detail panel instead
  of navigating away; "Invited undefined" toast hardened.
- **v51ar** — Login-page escrow registration entrypoint.
- **v51aq** — Duplicate escrow transaction guard (409), admin cancel row,
  release CSV export, EMD ledger search bar.
- **v51ap** — Escrow auto-ledger deduplication.
- **v51an** — Signatory password auth/login/reset, dashboard transactions grid,
  notice account routing picker, expiry watchdog cron.
- **v51am** — Admin Escrow review queue, approval magic-link email, step-4 KYC
  document upload wiring.
- **v51al** — P0/P1 hardening + Escrow Institution module scaffolding.

## Mobile Store Status
- Google Play Developer Console: Account "The PMC Managers Limited" verified.
- App created: `com.pmcmanagers.tenders` (PMC Managers — Tender & EMD Escrow).
- Policy setup completed: Privacy Policy, Sign-in details (App Access), Ads,
  Content Ratings (IARC PEGI 3 / Everyone), Target Audience (18+), Data Safety
  (5 data types declared, encrypted in transit).
- Store Assets: Rebuilt `pmc-mobile-store-assets-v1.0.0.zip` with true PNGs
  (icon 1024x1024 RGBA, feature graphic 1024x500 RGBA, 5 phone screenshots).
- Ready for tomorrow: Upload graphics to Main store listing, build signed `.aab`,
  and submit to Production release track.
  download fix (new `/api/v1/uploads/public-files/{key}` anon endpoint +
  NoticeDetail routes attachments through it), Stakeholder Reports link
  restored to Bidding Ops sidebar. Backend bundle: `pmc-backend-v51au.zip`.
  Frontend bundle: `pmc-frontend-v51au-prod-build.zip`.
- **v51at** — L1 Award page crash guard, vendor-list cache-bust after
  approve, PDF-only enforcement on bid envelope dropzones.
- **v51as** — Bidding Ops "Review" button opens inline detail panel instead
  of navigating away; "Invited undefined" toast hardened with fallbacks.
- **v51ar** — Login-page escrow registration entrypoint. SignInE's
  subtitle + bottom register button are now role-aware: selecting
  "Escrow Institution" swaps "Register as a supplier" for
  "Register as an escrow institution — bank / trustee onboarding"
  pointing at `/escrow/register`. Card subtitle updated to
  "dual-signature sign-off". Frontend-only; backend stays on v51aq.
  Bundle: `pmc-frontend-v51ar-prod-build.zip` (downloads/ excluded).
  Verified: register button href `/escrow/register` on preview.
- **v51aq** — Dup cleanup + Officer-email guard on PATCH + Release CSV
  export + Transaction search bar.
  **Dup cleanup**: new `GET /api/v1/escrow/transactions/duplicates`
  returns every bid holding more than one open row. Admin EscrowPanel
  shows a prominent red "Unresolved duplicates" banner listing offenders
  with click-to-filter. Also auto-cleaned the stale PMC-BID-2026-00048
  test rows (status cancelled, audit trail retained).
  **Officer-email guard on PATCH**: carries Bug G1's governance rule into
  `PATCH /api/v1/escrow/accounts/{aid}` — refuses the update with 400 if
  the resulting pmc/escrow officer emails would collide.
  **Release CSV export**: new `GET /api/v1/escrow/exports/releases.csv?year=`
  streams a compliance-grade CSV of every closed release
  (released_to_contractor / released_to_vendor / forfeited) with signatures,
  timestamps, account snapshot, officer emails, audit-trail comments.
  Admin EscrowPanel has an "Export releases · CSV" button inline with the
  new toolbar.
  **Transaction search bar**: single input filters the ledger by bid-ref /
  notice / vendor / amount / currency / status (fuzzy, case-insensitive);
  pager now walks the filtered list. "{n} of {total} shown" counter.
  Verified E2E: dup init → 409; dup scan → json; CSV export → 200 streamed
  text/csv; PATCH same-email → 400; yarn build clean.
- **v51ap** — Duplicate-ledger fix + admin cancel. One bid can now hold
  only ONE open escrow transaction at a time (status pending / received /
  awaiting_signatures). `POST /api/v1/escrow/transactions/init` returns 409
  with a human-readable detail when a dup is attempted; the auto-ledger
  (`escrow.auto_init_from_emd_payment`) also short-circuits and backfills
  the `payment_session_id` on the existing row instead of creating a
  parallel one. New `POST /api/v1/escrow/transactions/{tid}/cancel` lets
  admins clear mis-entries or legacy duplicates (allowed only while open;
  audit-logged with `escrow.tx_cancel`). Admin EscrowPanel row grew a
  "Cancel row" button for every open ledger entry alongside the Sign
  buttons. Verified E2E: duplicate init → 409 "Bid already has an open
  escrow transaction"; cancel on duplicate → status=cancelled.
- **v51ao** — Round 3 polish: Dashboard KPI, password reset, audit trail,
  bulk notice routing + action-mismatch UX fix.
  **Dashboard KPI**: new `EscrowInstitutionsKPI` tile appears in the
  AdminDashboardE "Needs attention" rail whenever an institution
  registration is sitting in `submitted` state — count + click-through to
  the review queue.
  **Password reset**: new `POST /api/v1/escrow-signatories/auth/forgot-password`
  (always 200 to avoid user enumeration; emails a 1hr Resend link) +
  `POST /auth/reset-password` (token + new_password; marks used atomically).
  Frontend `EscrowSignatoryLogin` now exposes a "Forgot password?" link and
  renders the reset form when hit with `?reset=1&token=…`.
  **Signature audit trail**: every escrow transaction row in the admin
  EscrowPanel grew a "Show signature audit trail" toggle rendering the full
  `audit_trail` chronology (received / signed_by_pmc / signed_by_escrow_institution
  with timestamps, actor emails, intended actions and comments). Plus a
  prominent amber mismatch banner when PMC and Escrow have signed DIFFERENT
  actions — explaining why the Release button is still disabled and what
  needs to change (this is the user's "signed twice and nothing fired"
  pattern).
  **Bulk notice routing**: `NoticeAccountPicker` on
  `/admin/e/escrow-institutions` now has a checkbox column, select-all,
  bulk-apply dropdown and single-click Apply — assign one escrow account
  across any subset of published notices in one shot.
  Verified E2E: forgot-password 200, reset-password 400 for bad token / 200
  for real token, login with new password 200; yarn build clean.
- **v51an** — Escrow Institution portal round 2: real signatory auth,
  dashboard transactions grid, notice-level account routing, and a cron
  expiry watchdog. Backend: new `routers/escrow_signatories.py` with
  `POST /claim?token=` (sets a password for a registered signatory,
  protected by the institution magic token), `POST /auth/login` → HttpOnly
  `escrow_sig_token` cookie + CSRF, `/auth/me`, `/auth/logout`, and
  `GET /dashboard` returning joint accounts + every tied transaction with
  `awaiting_my_signature` flags. Approval email now deep-links to
  `/escrow/login?claim=1&iid=&token=` so signatories land on the
  password-claim screen. `models/notice.py` gets an official
  `escrow_account_id: Optional[str]` field so
  `escrow.auto_init_from_emd_payment()` honours per-notice overrides. New
  cron webhook `POST /api/v1/cron/escrow-expiry-watchdog` + schedule in
  `.emergent/crons.yml` (daily 09:00 Europe/London) emails 30/7/1-day
  reminders and "already expired" alerts to institutions whose
  `licence_expiry` is within the window; idempotent on `X-Webhook-Id`,
  bearer-auth against `WEBHOOK_CRON_SECRET` (added to backend/.env).
  Frontend: `/escrow/login` (password login + claim mode), `/escrow/me`
  (post-login dashboard), rewritten `EscrowInstitutionDashboard` with KPI
  row, pending-signature table (per-row action dropdown + Sign off button
  calling `/escrow/transactions/{tid}/sign`), and a full transactions
  table. SignInE's "Escrow Institution" role now does a real password
  login (no longer bounces users to the registration form).
  AdminEscrowInstitutionsE grew a bottom section "Notice ↔ Escrow account
  routing" — table of every published notice with a dropdown picker that
  PATCHes `escrow_account_id` on the notice.
  Verified E2E: register → approve → claim → login → /me → /dashboard
  all 200 (/me returns institutions attached); notice PATCH 200; cron 401
  without secret / 200 queued with secret; yarn build clean.
- **v51am** — Escrow Institution portal: full close-out of the integration
  gaps. Backend `POST /api/v1/escrow-institutions/{iid}/decision` now
  auto-dispatches a magic-link approval email (recipients = primary contact
  + every registered signatory) with the direct `/escrow/dashboard/{iid}?token=…`
  deep-link; reject + needs_clarification send tailored emails too. Admin
  review queue page live at `/admin/e/escrow-institutions` (sidebar entry
  under Money &amp; compliance): status filter, drill-in panel with core
  details / signatories / banking / uploaded documents, three decision
  buttons (approve / request clarification / reject) with a required
  reviewer-note textarea for the non-approve paths. Registration step-4
  "Documents" step now ships a fully functional presign+direct uploader for
  all 8 KYC document slots (incorporation / regulatory licence / tax / 2x
  audited financials / insurance / letterhead / authority resolution) with
  per-slot upload, view, remove and auto-persistence back to the draft.
  Payments side: `payments._mark_paid()` now calls
  `escrow.auto_init_from_emd_payment()` the moment a vendor's EMD payment
  clears Stripe — creates the receive-side ledger row keyed on
  `payment_session_id` (idempotent on webhook retries) against the notice's
  `escrow_account_id` or the newest active account; failure is logged but
  non-fatal so admins can still record manually.
  Verified E2E: QA institution registered → submitted → listed → approved
  (returns magic_token for the dashboard link); yarn build clean.
- **v51al** — P0/P1 hardening + Escrow Institution portal integration.
  Backend: `POST /api/v1/bids` now rejects orphan submissions up-front
  (price_amount must be > 0, at least one technical envelope document
  required) AND enforces the corrigenda-acknowledgement 412 gate
  (`ensure_corrigenda_acknowledged(notice_ref, vendor_id)`) before any DB
  write — fixes the Bid 48 class of empty-shell rows. New admin-only
  `DELETE /api/v1/bids/admin/{id}` cleans up legacy orphan rows (only when
  price/docs/paid are all empty and status ∈ draft/submitted/emd_pending).
  Escrow Institution module wired into `server.py`
  (`routers.escrow_institutions`): public self-register at
  `POST /api/v1/escrow-institutions/register` returns a magic token;
  resume + submit + admin decision endpoints live; dashboard at
  `/{iid}/dashboard?token=...` surfaces joint-account + pending-signature
  counts. Frontend routes added: `/escrow/register`, `/escrow/resume/:token`,
  `/escrow/dashboard/:iid`. Unified login grew a 6th portal card
  ("Escrow Institutions · BANK · TRUSTEE", purple accent, lucide `Landmark`
  icon) — selecting it routes new institutions to the registration flow and
  approved ones to the dashboard via emailed magic link (no password login
  yet, matching external-trustee model). AdminBidDetailPage now auto-detects
  orphan bids and renders a red "Delete orphan bid" banner that calls the
  new admin DELETE endpoint. Verified: register API returns 200+magic token;
  escrow card renders on login page; backend restart clean.
- **v51ak** — Escrow "Record inbound EMD" bid picker: Bid ref free-text
  replaced with a dropdown of live bids (withdrawn/rejected excluded,
  EMD-paid floated to top with amount annotation); picking a bid auto-fills
  notice ref, vendor ref, amount, currency; manual-entry fallback retained.
  Frontend-only ZIP: `pmc-frontend-v51ak-prod-build.zip`.
- **v51aj** — Bidding ops hold/resume clarity: detail panel on an on_hold bid
  now shows an "On hold — reason — held by" note plus a **Resume bid** button
  (Hold… hidden), and the panel auto-refreshes after hold/resume/reject so the
  disabled-in-flight "greyed Hold" state can't get stuck (the user's
  "greyed hold → normal hold" mystery). Envelope-edit gate widened:
  `PATCH /api/v1/bids/{id}` + workspace "+ Add file" now allow edits in
  emd_paid and escrow_accepted too (everything before admin evaluation,
  deadline still enforced; on_hold stays locked until resumed).
  Bundles: `pmc-frontend-v51aj-prod-build.zip` + `pmc-backend-v51aj.zip`.
- **v51ai** — Vendor workspace "unable to proceed" fix. New backend
  `PATCH /api/v1/bids/{id}` (vendor-owner scoped; editable while
  draft/submitted/emd_pending and before deadline; audit-logged
  `bid.documents_update`; held bids get 400). Workspace: "+ Add technical /
  commercial file" upload buttons, per-file View/Download/Remove, clickable
  stepper steps 2/3, amber "on hold by PMC" callout. Verified E2E: real PDF
  upload through UI, remove, on-hold gate (hold → 400 → resume).
  Bundles: `pmc-frontend-v51ai-prod-build.zip` + `pmc-backend-v51ai.zip`.
- **v51ah** — Bidding ops: pipeline step tiles now render above the filter
  bar (user-requested order). Vendor bid workspace: EMD=0 bids no longer
  dead-end on "Pay the EMD" (step auto-completes as "Not required", compact
  info card replaces the payment form, checklist shows EMD ✓); envelope panel
  now reads real `bid.documents` (kind technical/commercial) instead of the
  never-populated `bid.envelopes.*.files`, listing each file with in-page
  View + Download — vendors can always inspect their own submissions.
  Verified in preview with PMC-BID-2026-00019 (submitted, EMD 0, docs
  present). Frontend-only ZIP: `pmc-frontend-v51ah-prod-build.zip`.
- **v51ag** — Vendor requests + Profile changes gain search/date-range filters;
  BOQ, Bidding ops, Escrow filters now actually hide non-matching rows (DOM
  row tags: `data-row`, `data-status`, `data-created-at`); Work packages
  Kanban switched to horizontal-scroll with 280 px cards; package View modal
  lists attached documents with View/Download links; MoneyFilterBar enforces
  Created-to ≥ Created-from and Expires-to ≥ Expires-from on every panel; each
  pending Escrow transaction shows an "Officer identity hint" explaining which
  side the signed-in admin will sign as (or that they're neither officer, so
  the sign call will be rejected and both officers must log in separately).
  Frontend-only ZIP: `pmc-frontend-v51ag-prod-build.zip`.
- **v51af** — Fix: Registrations "Edit sections" button (verified in preview:
  editable form opens + saves on a submitted registration). Bundles built:
  `pmc-frontend-v51af-prod-build.zip` + `pmc-backend-v51af.zip` +
  `DOWNLOAD_v51af.md`. Google verification meta tag carried forward.
  Root cause: 11/74 registrations (legacy rows) have no `magic_token`, so the
  resume link was built with `token=` empty and RegistrationResume bounced to
  `/register`. Backend `admin_resume_link` now mints+persists a token when
  missing; new admin-only `PATCH /api/v1/registrations/admin/{rid}` lets admins
  save edits on submitted/under_review registrations (public token PATCH only
  allows draft/needs_clarification); RegistrationResume uses the admin path
  when opened with `?from=admin&rid=...`.
- **v51ae** — Google Search Console verification meta tag added to
  `index.html` (`t7scPgT9ZxpjYxkyRAyB8cCvfrCh04IAO6XcvAvS4r0`) so Play
  Console "Verify your organization's website" resolves on pmcmanagers.com.
  Frontend-only ZIP: `pmc-frontend-v51ae-prod-build.zip`.
- **v51ad** — Corrigenda full workflow & saved filter presets
- **v51ac** — Vendor registration per-row edit links; expires-filter cleanup
- **v51aa-ab** — Full 5-section bulk CSV, full vendor editor, MoneyFilterBar,
  reverse auction edits

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key, Gemini 3.1 Flash (image generation for brand assets),
Capacitor 8 native bridge (iOS + Android).

## Up next
- User completes Apple + Google Play enrollments and ships us the two
  approval emails.
- Once approved, build `.aab` on dev machine, upload to Google Play
  Internal Testing track.
- Once Apple Account Holder is live, archive in Xcode and upload to
  TestFlight.
