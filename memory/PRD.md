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
