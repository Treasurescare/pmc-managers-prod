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
