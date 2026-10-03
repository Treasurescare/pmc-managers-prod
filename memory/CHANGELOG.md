# PMC Managers v2 — Changelog

## 2026-10-02 — v50r Post-prod fix pack

- **Vendor Home redirection** (prod bug): the 4 remaining static Option-E
  vendor pages (My bids, EMD, Reviews, Alerts) kept the mockup's
  `href="#"` sidebar; PmcLinkPatcher's text-match fallback sometimes
  routed Home to the public landing page. Replaced every sidebar entry
  with real `/vendor/*` hrefs — Home always stays inside the portal now.
- **Admin Vendor requests crash** (`This panel hit an error`): the
  `vendor_categories` router was registered AFTER `vendors.router`, so
  the `/{vendor_ref}` catch-all swallowed `/api/v1/vendors/category-requests`
  and returned a dict → the panel's `rows.map` blew up. Router order fixed
  (now BEFORE `vendors.router`, same guard as `vendor_profile_changes`),
  and both admin panels hardened to coerce non-array payloads.
- **Sidebar reorg**: Vendor requests + Profile changes moved out of
  Masters into the Market section as top-level items —
  `/admin/e/vendor-requests` (AdminVendorRequestsE) and
  `/admin/e/profile-changes` (AdminProfileChangesE). Masters tabs still
  render those panels under "(moved → Market)" labels for one release.
- **Help centre back button**: `/help` and `/help/:slug` headers used to
  hard-link to `/admin/e/dashboard`. Replaced with a real
  `window.history.back()` button (fallback: `/help` root). Vendors return
  to the vendor page, admins return to the admin page.



## 2026-10-02 — v50q (activation verified · blank form regenerated · DocuSign archive tool · EMD editor)

- **#6 Vendor activation** — full flow re-tested end-to-end via API
  (admin-create → activate/set_password → listed active → sign-in with
  must_change_password). No code change needed; marked Fixed.
- **#60 Blank registration form** — regenerated a branded 2-page PMC blank
  form (sections A–E + K declarations + signature block) with reportlab and
  uploaded it as the live registration template; download endpoint verified
  (application/pdf, valid %PDF payload).
- **DocuSign admin Archive-PDF tool** — `POST /api/v1/docusign/envelopes/{id}/archive-pdf`
  fetches the combined signed PDF from DocuSign and stores it in PMC storage;
  vendor/admin download endpoints serve the archive first; `has_document`
  reflects archived envelopes; new "⇩ Archive" buttons on completed
  envelopes in the admin DocuSign console (row + view modal).
- **EMD Master Editor UI** — new Masters tab "EMD rules"
  (`EmdMastersPanel.jsx`): create/edit/delete rules with country / kind /
  category scope, currency, active toggle, notes; slab editor (fixed or %
  with min/max caps); quick calculator against the compute endpoint.
  Verified: 2% of 1.2M = USD 24,000 (capped), 100k → fixed USD 5,000.


## 2026-10-02 — v50p PmcLinkPatcher guard (Signatures Download fix)

- `PmcLinkPatcher`: the legacy action-label click map (`/^download$/i` →
  `handleSigDoc`) hijacked the Download button on the rewritten Signatures
  page before React's onClick, surfacing "This document isn't linked to an
  envelope yet." Fully-React vendor pages (`vendor-home-e`,
  `vendor-find-tenders-e`, `vendor-signatures-e`, `vendor-account-e`,
  `vendor-company-kyc-e`) are now exempt from the label map — component
  handlers always win on those pages.


## 2026-09-23 · v46f HOTFIX — production bundle had preview API URL baked in (login CORS-blocked)

### Incident
After user deployed v46f, login on pmcmanagers.com failed with "No matching employee account" (generic toast). Root cause found via browser automation + console logs: the bundle was built with `REACT_APP_BACKEND_URL=https://pmc-forest-green.preview.emergentagent.com` from `frontend/.env`, so the browser called the PREVIEW API cross-origin → CORS blocked (wildcard origin + credentials) → every auth call failed before reaching the server. curl to production API worked fine the whole time — purely a build-env mistake.

### Fix
Rebuilt with `REACT_APP_BACKEND_URL="" yarn build` (shell env overrides .env in CRA; empty → same-origin relative /api calls, exactly how the working v46e was built). New bundle `main.35c2896b.js` — verified zero `tender-hub-57` references. Repacked with `build/` prefix.

### v46i · 24 Sep 2026 — Admin sidebar shell + editorial public site + 5-portal sign-in + new roles

**Design refresh delivered from `/app/design_guidelines.json` (Big-4 editorial · Emerald-inspired hybrid, PMC navy + gold retained).**

- **Admin sidebar shell** (`admin-console/AdminShell.jsx`) — collapsible left sidebar grouped into 5 sections (Overview / Procurement / Market / Money & Compliance / Events), 24 panels wired. Nav mode toggle: `full` (icon + label), `icons` (icon-only rail), `hamburger` (drawer) — persisted in `localStorage.pmc_admin_nav`. Mobile always uses the drawer.
- **Public site editorial pass**:
  - `/about` — About Us page (masthead, 3-stat band, 1-stop lifecycle prose)
  - `/vision` — Vision & Mission page (side-by-side navy/white cards, 6-values grid)
  - `/tenders/:mode` (`live | completed | all`) — filterable card grid with status chip (Live=emerald, Closed=slate, Awarded=navy), country + query filters
  - `TopBar` public nav → Live tenders · Completed · About us · Vision · Register · Sign-in
  - `PmcFooter` — 4-column footer with Snapchat + Instagram + WhatsApp social icons (URLs override via `window.__PMC_SOCIAL__`), Legal column, © bar
- **5-portal sign-in** — `UnifiedLogin` role selector now includes `management`, `partner`, `agent` on top of admin/reviewer/escrow/certifier/legal/accounting/committee/auditor/support.
- **Backend roles** — `StaffRole` literal + `ALL_STAFF_ROLES` extended with `management`, `partner`, `agent` (`backend/models/staff_user.py`). No new endpoints needed — existing `require_role()` guards accept them, and the seeder / admin `staff/create` UI now offers the new roles.

Deploy: frontend zip `pmc-frontend-v46i-prod-build.zip` (`main.6838b149.js` — 0 preview URL refs). Backend restart needed to pick up the role literal.

---



---

## 2026-09-23 · v46g — DPR DEEP-DIVE (multi-pass, KMT verified 5 → 26 sections)

### User request
"Is the workflow now able to deep-dive and read the FULL KMT file?" — no; the old pipeline clipped extracted text to 16 KB (~5–8 pages) and asked the AI for only 5 generic sections (`sec-1 … sec-4, annex-III`), so the financial schedules and back-of-document annexures were skipped.

### Delivered (`backend/routers/tender_pro.py`)
Rewrote `_run_dpr_analyze` with two modes:

**Template-aware (master picked)** — same single-call flow but excerpt bumped from 16 KB → 60 KB, plus a warning if the document was longer.

**Deep-dive (no master)** — multi-pass:
1. **Pass 1** feeds head 60 KB + tail 30 KB to the LLM to (a) extract the full header and (b) dynamically discover 12–30 real chapters (project overview, financials, schedules, risk, annexures…). Returns codes `dpr-1…dpr-N`, titles and hints — no bodies yet.
2. **Pass 2** drafts each discovered section's body in parallel (asyncio.Semaphore(6)) from the passage of the DPR most relevant to that section title (`_chunk_for_section` searches the extracted text for the title and returns ±3.5 KB of surrounding context; falls back to an even slice if no hit).

Result payload also now returns:
- `sections_blueprint`: the ordered list of discovered sections
- `meta.chars_total`, `chars_analysed`, `sections_discovered`, `sections_drafted`, `passes`
- Truncation warnings when the DPR exceeds 90 KB of extracted text.

### Verified against KMT DPR (1.37 MB PDF, 68 704 chars extracted)
- Header: work_title, work_description, tender_value USD 6.0–6.2 B, EMD USD 62 M, all populated.
- **26 sections discovered and drafted**: Executive Summary, Keys to Success, Market Analysis, Kazakhstan Medical Township Solution, SWOT, Organizing Structure, Project Site, Academic & Clinical Delivery, Staff Plan, Project Investment, Operating Expense Detail, Projected Operational Results, Fund Requirement, Returns & Scenario Analysis, Installation & Commissioning Schedule, Risk Factors & Mitigation, Corporate Details, Tender Submission Forms, Financial Statements & Models, Legal and Compliance Requirements, FAQs, Annexures, and more.
- End-to-end LLM time ~34 s (27 parallel calls); 0 warnings.

### Artifacts
- `/app/deliverables/v46c/pmc-backend-v46g.zip` (EB Docker bundle) — DEPLOY THIS.
- `/app/deliverables/v46c/pmc-frontend-v46f-prod-build.zip` (repacked with `build/` prefix so your existing deploy script works verbatim — no frontend code change from v46f).

### Deploy (both)
Backend — EB console → Upload and Deploy → `pmc-backend-v46g.zip` → label `v46g-dpr-deep-dive`.  
Frontend — same S3 sync + CloudFront invalidation you used for v46e (refresh CloudShell if AWS token expired).

---



### User request
1. KMT DPR uploaded fine but output differed from template-based runs (no KZ master existed → generic fallback structure).
2. After AI reads the file, let the user EDIT the auto-generated tender name before saving; saved draft must be searchable in the left-column search.

### Root cause found during audit
v46e "Build a new master from this DPR" only created a DRAFT: `POST /api/v1/tender-templates` forces `is_master=false` and drops top-level `country`. The "saved as new master" toast was false.

### Delivered (frontend `DprGenerateModal.jsx`)
- After create, when no-master mode is on and no base master picked, the draft is promoted via `POST /api/v1/tender-pro/templates/{id}/save-as-master` (real master, top-level country/industry, name `"{chosen} · {CC} master"`).
- Per-file EDITABLE name input (`data-testid=dpr-name-{idx}`) pre-filled from AI `work_title`; used as the saved draft name (searchable via `tb-filter-q`).
- Base-master select gets a `— New master from this DPR —` placeholder option + `value={p.masterId || ""}` (React null-value warning fixed).
- Testing agent iteration_24: backend 6/6 pytest, frontend full happy path 100%. QA masters purged from preview Mongo.
- Artifact: `/app/deliverables/v46c/pmc-frontend-v46f-prod-build.zip` (main.21ab3717.js), also at `/downloads/pmc-frontend-v46f-prod-build.zip`. Backend unchanged — no backend deploy needed.

### Deployment note
User deploys via CloudShell: download zip → unzip → `aws s3 sync build/ s3://pmc-managers-frontend-prod/ --exact-timestamps` (NEVER `--delete`) → CloudFront invalidation.

---



### User request
"Reverse Auction: real-time bidding room with invites, countdown, live view. Fee Types: subscription/premium/transaction/data-intel end-to-end into payments. Then deploy."

### Delivered
**Backend**
- `POST/GET /api/v1/reverse-auctions/{aid}/invite(?)` — admin invites bidders by email; per-email token; dedupes with resent_at (auction_live.py)
- `GET /api/v1/reverse-auctions/invite/resolve/{token}` (public) + `POST /api/v1/reverse-auctions/invite/accept/{token}` (vendor) — auto-registers vendor as auction participant
- `POST /api/v1/billing/fee-checkout` — takes fee_master_id + tender_value, computes slab, creates Stripe Checkout session (billing.py). Amount is server-authoritative from EMD/fee master. Works with any of the 7 fee kinds (emd, tender_fee, registration, subscription, premium_subscription, transaction, data_intel).

**Frontend**
- `admin-console/auction/AuctionInvitations.jsx` — inline widget under each non-closed auction row (invite list, textarea, note, generate + copy link)
- `vendor-portal/AuctionInviteAccept.jsx` — `/vendor/auction/invite/:token` landing page with auction summary + accept flow
- `admin-console/masters/FeeCharger.jsx` — Charge Fee tab under Masters → picks master, previews slab amount, opens Stripe checkout
- `MastersPanel` — new "Charge Fee" tab (data-testid `masters-tab-fees`)
- `App.js` — new route `/vendor/auction/invite/:token`
- `lib/api.js` — `reverseAuctionApi.invite/listInvitations/resolveInvite/acceptInvite` + `feeBillingApi.feeCheckout`

### DPR robustness confirmed
Tested user's Kazakhstan Medical Township DPR: HTTP 200, extracted work_title, work_description, tender_value USD 6.0–6.2B, budget_currency USD, period_days 1825, location "Almaty & Astana, Kazakhstan" cleanly. No OCR needed — existing pypdf pipeline handled it.

### Testing
- `/app/backend/tests/test_v46b_auction_invites_and_fees.py` — 20 tests. Combined suite: 45/45 pytest pass.
- testing_agent iteration_23 — Backend 100%; frontend verified (invitations widget + vendor invite landing; Charge Fee tab wired after fix).

### Not yet deployed to AWS · user awaiting deployment step

---

# PMC Managers v2 — Changelog

## 2026-02-24 · v46d — PRODUCTION INCIDENT FIX · stale service worker + wrong baked API URL

### Incident chain (user-reported: site not loading → login fails → "signed in" but bounced)
1. Frontend zip initially built with preview backend URL baked in (`tender-hub-57.preview.emergentagent.com`) → all API calls cross-origin to the wrong backend → login hung with zero network requests.
2. Rebuilt with `d2h9tkca2zjofy.cloudfront.net` → login POST succeeded but session cookie set `SameSite=Lax` on the cloudfront.net host is NOT sent on cross-site XHR from www.pmcmanagers.com → `/auth/me` 401 → bounced back to /login after "Signed in" toast.
3. FINAL ROOT CAUSE masking all fixes: `src/index.js` registered an offline-first service worker (`/service-worker.js`, precaches "/") which kept serving the STALE broken bundle from Cache Storage even after correct builds shipped to S3+CloudFront.

### Fix (v46d)
- `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com` baked in (same-origin — CloudFront routes /api/* to EB; cookies become first-party).
- Service worker registration removed from `src/index.js`.
- `public/service-worker.js` replaced with a SELF-DESTRUCTING worker: skipWaiting → delete all caches → clients.claim → unregister → force window reloads. Every returning browser heals itself on next visit.
- Production bundle: `main.eab42f05.js` · zip `pmc-frontend-v46d-prod-build.zip` sha256 `bb78e34d7df3e208ffd8e34439f352830bbb8d3db78271b6cb5cb46f02d472b7`.

### Permanent lessons (added to PRD)
- ALWAYS build the production frontend zip with the production REACT_APP_BACKEND_URL (env override at build time — never edit .env).
- This app must NOT ship a cache-first app-shell service worker until an update-notification flow exists. If PWA/push is revived, use network-first for navigations.
- Verified via curl: same-origin login + /me round-trip 200 on prod.

---

## 2026-02-24 · v46c — Spectator + invite templates + fee refunds + DEPLOY

### User request
"Live Auction Spectator public view · Invitation Templates + auto-send · Fee Refunds via Stripe · Deploy v46b to AWS."

### Delivered
**Backend**
- `GET/POST/PATCH/DELETE /api/v1/reverse-auctions/invite/tpl(/{tid})` — invitation-template CRUD (auction_live.py). Supports placeholders `{{invite_url}} {{auction_title}} {{notice_ref}} {{vendor_email}} {{starting_price}} {{currency}} {{admin_note}}`.
- Invite endpoint extended: `template_id`, `auto_send`, `origin_url`. Sends via managed email proxy (`emails.send_email`), returns `auto_sent` count.
- `POST /api/v1/billing/refund/{session_id}` (billing.py) — admin refund. Retrieves PaymentIntent from Stripe checkout session, `stripe.Refund.create`, marks transaction `refunded`.
- Public `/state` (already existed) reused for spectator view.

**Frontend**
- `shared/PublicAuctionRoom.jsx` — `/auctions/:aid/live` public spectator (2s polling, countdown, masked bid feed, closed banner). No auth.
- `admin-console/BillingTransactionsPanel.jsx` — new "Billing & Refunds" tab (data-testid `admin-tab-billing`) with transactions table + per-row Refund button.
- `admin-console/auction/AuctionInvitations.jsx` extended with template picker (`ai-tpl-{aid}`) + auto-send toggle (`ai-autosend-{aid}`).
- New route `/auctions/:aid/live` in App.js.

### Testing (preview)
- Curl: templates CRUD OK; invite with template_id + auto_send → `auto_sent: 1`; refund on pending tx → 400 with clear message; public /state → 200 with masked bids.

### Deployment
Dispatched to deployer agent — job 60f300ec-7443-4bb9-ae84-d2df7002707a. Deploying both backend (Elastic Beanstalk) and frontend (S3/CloudFront) with v46c payload.

---

# PMC Managers v2 — Changelog

## 2026-02-24 · v46 — Vendor Ratings & Reviews portal (preview only)

### User request
"Peer vendors + PMC management + public buyers should rate vendors. Anonymous but verified. Trust badges on landing page. This needs to be worked properly."

### Delivered
**Backend** — new router `/api/v1/vendor-ratings/*` in `routers/vendor_ratings.py`
- Public: `GET /public/rubric`, `GET /public/top`, `GET /public/{vendor_ref}`, `POST /public/submit` (3-per-email/day rate limit, pending moderation)
- Peer vendor (cookie auth): `GET /directory`, `POST /peer/submit` (self-rating 400-block, auto-approve if is_active), `GET /peer/mine`
- PMC admin (Bearer+CSRF): `POST /admin/submit` (auto-approved), `GET /admin/reviews`, `POST /admin/reviews/{id}/moderate` (approve/hide), `DELETE /admin/reviews/{id}`, `GET /admin/pending-count`
- Trust badge tiers: platinum (≥85/≥10), gold (≥70/≥5), silver (≥55/≥3), bronze (≥1), none

**Frontend**
- `components/VendorTrustBadge.jsx` — reusable badge with tier styling
- `shared/TrustedVendorsSection.jsx` — landing "Trusted vendors" strip with badge legend + top-rated cards
- `shared/PublicVendorProfile.jsx` — `/vendors/:ref` public page (aggregate, criteria averages, moderated comments, public buyer review form using `/public/rubric`)
- `vendor-portal/RateAVendor.jsx` — vendor dashboard "Rate a vendor" tab (directory search, sliders, own review history)
- `admin-console/vendor/ReviewModerationSection.jsx` — admin moderation queue with pending/approved/hidden/all tabs and approve/hide/delete per row (data-testids `rm-tab-*`, `rm-approve-{id}`, `rm-hide-{id}`, `rm-delete-{id}`)
- Wired into `App.js` (`/vendors/:vendorRef`), `NoticeBoardHome`, `VendorDashboard` (new tab), `VendorIntelPanel` (badge column + moderation section)

### Testing
- `/app/backend/tests/test_v46_vendor_ratings.py` — 24/24 pytest pass (public/top, public aggregate, public submit + 429/422/404, admin submit + upsert + CSRF, moderate approve/hide/delete + aggregate reflect, peer submit self-block + upsert, public rubric, directory + q filter + auth)
- testing_agent iterations 21 & 22 — Backend 100%, Frontend 100% after two blocker fixes (public rubric + vendor directory endpoints replacing admin-scoped calls)

### Not yet deployed to AWS · user deferred deployment

---

## 2026-02-22 · v44 — Vendor Admin UI + Directors registration (preview only)

### User report
"A) all the 5 fixes in one go" — Directors registration missing, vendors disappearing from UI after activation, inability to activate existing vendors, temp test account needed.

### Fixes (v44)
**Backend (`vendor_invites.py`)**
- New endpoint `POST /api/v1/vendors/{vendor_ref}/activate` (admin + CSRF)
  - `mode=resend_link` → regenerates magic token and re-emails the verify link
  - `mode=set_password` → force-activates immediately with an admin-supplied password (≥8 chars) and flags `must_change_password=True`
  - Guards: 404 on missing vendor, 400 on already-active, 400 on `set_password` missing password, 401 unauth, 403 CSRF

**Frontend — Admin Vendors panel (`VendorsPanel.jsx`)**
- Inline green **"Activate now"** button on every inactive vendor row (`data-testid=vendor-activate-<vendor_ref>`)
- Auto-scroll to and emerald-ring highlight (3.5 s fade) on any vendor row that was just invited, activated or force-activated — newly-created vendors no longer feel like they "disappeared"
- `window.confirm` flow: OK = resend magic link, Cancel = admin sets a temporary password inline; success/failure surfaced via `showApiError` + sonner toasts

**Frontend — Registration flow (Directors section)**
- New `SectionDirectors.jsx` with unlimited add/remove rows: Full legal name, Role (Director / Shareholder / UBO / Officer / Other), Nationality, ID/Passport #, Ownership %, Residential address
- New step inserted between D and E: `STEPS = ["a","b","c","d","directors","e"]`
- Submit gate: at least one row with non-empty `full_name` required. Reason surfaced inline (red text) + toast
- Persisted at `reg.directors` (array). No backend schema change — `RegistrationUpdateIn` already uses `extra="allow"`
- Localised in EN / RU / KK (register.section_directors, register.directors_required, section_directors.*)
- Stepper CSS tightened (`px-3 py-2`, `whitespace-nowrap`, `gap-2`) so 6 steps sit compactly

### Testing status
- `/app/backend/tests/test_v44_activation.py` — 8/8 pytest cases pass
- testing_agent iteration_20 — 100 % pass on both backend + frontend flows; window.confirm/window.prompt handled correctly
- Verified end-to-end via curl on preview: `resend_link` ✓, `set_password` ✓ (vendor can then log in with new password), 404 ✓, already-active guard ✓

### Not yet deployed to AWS · awaiting user verification on preview

---

## 2026-09-19 · Batch #9d — Loud, verbatim error handling everywhere (v40 frontend, backend unchanged)
**Not yet deployed to AWS · awaiting user verification on preview**

### User report
"Error message handling is very bad. When such a thing happens clear-cut error message needs to be flashed then and there."

### Fixes (v40)
**Global `Toaster` (App.js + index.js)**
- Moved to **top-right** (was bottom-right, easy to miss)
- **`richColors`** + **`closeButton`** + **`expand`** so toasts stack readably instead of overlapping
- Default duration **6s** for info/success · **12s** for 4xx errors · **8s** for 5xx errors
- Custom classes: red 4px left border on errors, emerald on success, amber on warnings, brand navy on info
- Larger footprint on errors (`min-w-[380px] max-w-[560px]`) and `whitespace-pre-line` on descriptions so long remediation text is not clipped

**New `showApiError(err, {fallbackTitle})` helper in `lib/api.js`**
- Splits backend `detail` into a short **title** (HTTP status + first sentence) and a long **description** (rest of the remediation text)
- Automatically mirrors to `console.error` with the full response body so support can copy-paste the exact server reply
- Long-form 4xx guidance messages (e.g. escrow "same email on both officers") now display fully instead of being silently truncated in a 4-second bottom-corner toast

**Migrated critical call sites**
- `EscrowTransactionsSection` — `sign`, `release`, `createTx` all use `showApiError`
  - **Sign** now inspects the returned `signatures` payload and shows **either**:
    - ✅ `"Both officers signed — Release is now unlocked"` (green, with the action)
    - 🔵 `"Signed as {side} — awaiting {other side}. Nothing has been transferred yet."` (blue info, so the user is NEVER left thinking a release fired when only one side signed)
  - **Release** with mismatched actions shows a red error explaining exactly what the two sides have signed
- `CommitteeList` — dissolve + resend-invite use `showApiError` and success toasts include the notice ref + reason preview
- `BiddingOpsPanel` — committee-create surfaces missing-field validation as a proper red error with description and uses `showApiError` on the backend call

### Rollout note
This is a frontend-only change (v40); backend v22f from Batch #9c remains the target for the paired push.

---

## 2026-09-19 · Batch #9c — Escrow governance guard (v39 frontend · v22f backend)
**Not yet deployed to AWS · awaiting user verification on preview**

### User report
"I am sending a document for signing and release to contractor. It shows signed. But nothing has been triggered."

### Root cause (P0)
The joint escrow account `PMC-KZ EMD Escrow #1` had `adminsupport@pmcmanagers.com` on BOTH the PMC officer AND the Escrow officer. When the admin clicked **SIGN · RELEASE TO CONTRACTOR**, the backend `sign_off` handler's `if/elif` short-circuited on the PMC side, recorded the signature only under `signatures.pmc`, and left `signatures.escrow_institution` empty forever. `_dual_signed()` therefore returned `False` and the **RELEASE** button stayed permanently disabled with "needs both signatures". The account was created before the "different-emails" guard was added, so it slipped through.

### Fixes (v39/v22f)
**Backend (`routers/escrow.py`)**
- `sign_off` now detects `pmc_email == escrow_email` BEFORE selecting a side and raises HTTP 409 with a plain-English message telling the operator exactly what to fix and where.
- `list_accounts` now returns per-row `governance_ok: bool` + `same_email_email` + tenant-wide `governance_summary: {ok, broken}`.
- `list_transactions` now returns per-row `governance_ok` + `same_email_email` so the panel can render banners without a second round-trip.

**Frontend (`EscrowTransactionsSection.jsx`)**
- Red governance warning banner on every affected transaction row explaining:
  1. Which email is on both sides
  2. Why release will never fire
  3. Exactly how to fix it (edit the Escrow officer to a different email)
- Sign + Release buttons on affected rows disabled with tooltip pointing to the banner
- Uses the backend `governance_ok` flag with a snapshot-based fallback for older cached responses

### Verified in preview
- `POST /api/v1/escrow/transactions/{tid}/sign` → HTTP 409 with the full remediation message ✓
- `GET /api/v1/escrow/accounts` → `governance_summary: {ok: 0, broken: 1}` ✓
- Frontend build → `Compiled successfully`

### Immediate remediation for production
Ask the customer to open **Escrow → Joint Escrow Accounts → PMC-KZ EMD Escrow #1**, edit the **Escrow officer** email to a distinct trustee (or issue a magic-link to the external escrow institution via `POST /api/v1/escrow/magic-tokens`). Once the two officers are distinct, existing pending transactions can be re-signed by each side and Release will fire cleanly.

---

## 2026-09-19 · Batch #9b — Committee dissolve/create hotfix (v38 frontend, backend unchanged)
**Not yet deployed to AWS · awaiting user verification on preview**

### Root cause (P0)
`CommitteeList.jsx` used a raw `fetch()` call for the Dissolve + Resend-invite actions that
did NOT attach the `X-CSRF-Token` header. Backend responded with **HTTP 403 "CSRF token
missing or invalid"** for every dissolve attempt, so committees stayed `status="open"`
forever. That in turn made every subsequent **Form committee** attempt on the same tender
fail with **HTTP 409 "Open committee already exists for this tender"** — which the user
correctly reported as "committee is neither formed".

### Fix (v38 · main.<new-hash>.js)
- `CommitteeList.jsx` migrated from raw `fetch` to the shared `api` axios instance
  (`api.post()` auto-attaches `X-CSRF-Token` from the `csrf_token` cookie via the
  request interceptor in `lib/api.js`).
- Error toasts now show the actual backend detail via `formatApiError()` so future
  auth/CSRF regressions are visible to the operator.
- Prod cleanup: the 2 zombie committees still open on preview were dissolved via curl
  with CSRF header. Any zombie committees left on prod (pmcmanagers.com) will now
  dissolve cleanly from the UI once v38 is deployed.

### Verified in preview
- Dissolve committee button → HTTP 200 with `{"ok": true}` ✓
- Both zombie committees moved to "Recently closed / dissolved" ✓
- Form committee no longer blocked by 409 on the same tender ✓
- Production build compiles cleanly (`Compiled successfully`)

---

## 2026-09-19 · Batch #9 — Final bug-tracker clearance (v37 frontend · v22e backend)
**Not yet deployed to AWS · awaiting user verification on preview**

### Frontend (v37 · main.2d540e4e.js)
- **#21** — NoticesPanel: `isMasterAdmin` role check now case-insensitive and tolerates spaces/hyphens (`master admin`, `MASTER_ADMIN`, `Master-Admin` all accepted)
- **#28** — Added trilingual `panels.vendors.*` and `panels.registrations.*` keys (EN/RU/KK) to `lib/i18n-strings.js`; `VendorsPanel.jsx` and `RegistrationsPanel.jsx` fully rewired via `useI18n`
- **#29** — (paired with backend) fresh avatar visible on next tab immediately (no more stale `/me`)
- **#30** — New `EmailInput` and `PhoneInput` helpers in `FormPrimitives.jsx` with inline error styling; wired into `SectionB.jsx`
- **#49** — `RubricEditor.jsx` computes weightSum, per-criterion bounds, commercial weight range, and cutoff bounds; disables "Save rubric" and shows inline error list when invalid
- **#63** — `AdminVendorCreate` redirects to `/admin?tab=vendors` after successful create; `AdminDashboard` reads `?tab=` from URL on mount and on every `location.search` change
- **#84** — `VendorIntelPanel` table wrapped in `overflow-x-auto` container with `min-w-[640px]` for horizontal scroll on mobile

### Backend (v22e)
- **#29** — `/api/v1/admin/auth/me` + `/api/v1/vendor/auth/me` now emit `Cache-Control: no-store, no-cache, must-revalidate`
- **#49** — `models/evaluation.py::ScoringRubricIn` migrated from `model_post_init` (which silently swallows ValueError) to `@model_validator(mode="after")` so invalid rubrics return proper 422s. Also added `minimum_technical` 0-100 bound
- **#52** — `evaluations.submit_score` now reads `notice.{kind}_locked_at` and returns HTTP 409 with the lock timestamp when the envelope is locked; per-criterion max_score bound enforced (422 on overflow); commercial score forced 0-100

### Verified in preview
- Login → /admin OK
- `Cache-Control: no-store` on `/me` ✓
- Rubric weight=2 → 422 with clear message ✓
- Rubric min_tech=150 → 422 ✓
- Deep-link `/admin?tab=evaluation` lands on Evaluation panel ✓
- Publish checkbox enabled for master admin (`disabled = None`) ✓
- Production build compiles cleanly (`craco build` → `Compiled successfully`)

---

## Prior session (2026-02-19) — Batches #6, #7, #8 (v22c/d, v32/34/35)
Complete GoDaddy → Route 53 DNS migration. Same-origin frontend (bypasses Safari ITP). CloudFront apex→www 301 redirect. 100% purge of "Emergent" branding from prod bundles. Notice draft flow, vendor invite pipeline, and Tender Builder Clone/Delete/History fixes.

## Earlier session (2026-01) — Batches #1–#5 (v20/21, ≤v30)
57 bugs closed covering Auth, Bidding Ops, BOQ, Committee, Escrow, L1, Reverse Auctions, Registrations, Audit, Vendors invite pipeline, and Analytics anomaly scoring.

## v50s — 2026-10-03 (vendor UX hotfixes)
- Supporting-document upload tiles on Bid Submit now use amber dashed boxes with "+ Click to upload" labels (previously ghosted text was invisible on the cream background).
- Fixed re-upload after delete: both the onChange handler and removeDoc() now reset the file input value so the SAME filename can be picked again.
- Rewrote /vendor/mybids from the static mockup into a fully live React page (bidApi.mine with notice_title/submission_deadline join). Every bid the vendor submits now appears here immediately.
- VendorPortalChrome now fetches live sidebar counts (Find tenders / My bids / Signatures) so badges match reality on every page (previously "29" was hard-coded).
- /vendor/auth/me now returns business_categories, country, kyc_status — approved categories now show up in Company & KYC header.
- /vendor/categories page gets a "← Back" button to return to Company & KYC.

## 2026-10-03 — v50u Vendor portal navigation consistency
- My Bids View/Continue buttons routed to non-existent `/vendor/bids/:id` (fell through to notices catch-all) → now open live Bid Workspace `/vendor/workspace/:bidId`.
- Removed hardcoded mockup sidebar badges (29/1/1) from static vendor pages: VendorEmdE, VendorReviewsE, VendorAlertsE, VendorBidWorkspaceE — fixes the 29↔33 count flip when navigating between static and live pages.
- VendorBidWorkspaceE sidebar `href="#"` links replaced with real `/vendor/*` routes.
- Verified on preview: action hrefs correct, zero stale badges, workspace nav routes live. Built with REACT_APP_BACKEND_URL="" (v50t guard retained).

## 2026-10-03 — v50t Critical prod API routing fix
- Root cause of prod login/reset-link failures: frontend bundle had preview REACT_APP_BACKEND_URL baked in; browsers on pmcmanagers.com called the preview backend (different DB/JWT secret) → reset tokens "invalid", logins failed.
- Fix: runtime domain guard in api.js (non-preview hostnames force same-origin "") + build with REACT_APP_BACKEND_URL="".
- password_reset.py: email dispatch failures now logged (log.error + audit_log auth.reset_email_failed) instead of silently swallowed.

## 2026-10-03 — v50v Bid Workspace live + Reviews/KYC/Signatures polish
- VendorBidWorkspaceE: full rewrite from static mockup → live bid data via /api/v1/bids/{id}, functional radios (Transfer-to-escrow / Bank guarantee), working proof upload (uploadsApi.presign), Save-and-finish → My bids, Pay EMD now → Stripe checkout. Fixes vendor-reported a/b/c.
- VendorSignaturesE: heading now context-aware ("N signed documents" / "Nothing to sign yet"); download has document.pdf fallback when combined-pdf 502s.
- VendorCompanyKycE: new "Bidding categories" tab fed by vendorApi.myCategories() showing approved + pending + recent decisions; header counter prefers live data so admin-approved categories appear without re-login.
- VendorReviewsE: rewritten as React component; Reply opens a dialog that drafts a mailto to tenders@pmcmanagers.com with review context. Fixes reply→bids catch-all.
- PmcLinkPatcher: added vendor-reviews-e, vendor-bid-workspace-e, vendor-mybids-e to REACT_OWNED and short-circuited the full label-map on React-owned pages (previously matchVendorCta("Reply") routed to /vendor/mybids even after REACT_OWNED skip).
- Verified end-to-end on preview: workspace title/status/EMD/radios live; reply dialog opens; KYC tab shows pending; signatures heading context-aware.
