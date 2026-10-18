# PMC Managers — PRD (reset: 16 Feb 2026)

> Oversized history relocated. This file now carries ONLY the live product
> requirements + current status. Changelog and backlog live in the sibling
> files.

## Product
PMC Managers is a React + FastAPI + MongoDB procurement/tender SaaS with
reverse auctions, bid governance, EMD escrow workflows, vendor/staff/
institution portals, AWS deployment bundles, and transactional notifications
(Stripe, Resend, DocuSign, Emergent crons).

## EMD → Escrow flow (validated on preview, 18 Jun 2026)
Lifecycle: bid `emd_paid`→`escrow_accepted` (auto) → admin records EMD receipt
(`POST /api/v1/escrow/transactions/init`) against a joint account with DISTINCT
officers → tx at `received` → dual sign (in-app / magic-link / DocuSign) →
`Release`. DocuSign hand-off = `POST /api/v1/escrow/transactions/{tid}/docusign`
(503 if DocuSign not configured; magic-link email is the fallback). Preview E2E
confirmed: EMD USD 500,000 recorded, tx `received`, governance_ok, both officers
distinct, ready for signature hand-off.

## v56d/v56e (18 Jun 2026) — escrow DocuSign signing reflects on dashboards
- v56d: Safari fix — institution portal "Open in DocuSign to sign" now works
  (open tab synchronously then navigate; was window.open after await → blocked).
- v56e: completed escrow DocuSign envelope now reconciles the escrow TRANSACTION
  (`_apply_live_status` escrow_tx branch): mirrors status + marks both officer
  signatures Signed on completion. New admin **Refresh DocuSign** button +
  `POST /escrow/transactions/{tid}/docusign/refresh` pulls status on demand
  (works even without the Connect webhook). Curl-simulation verified.
- Open next: signed-PDF download into the dashboard; PMC-officer signing view +
  sidebar inside the Staff portal (confirmed, not yet built); DocuSign "completed"
  email to signers is an account-level Connect setting.

## Current deployable: v56e
Production kept returning "CSRF token missing or invalid" on POST/PATCH (escrow
Save, Backfill) even after v56a + CloudFront invalidation + incognito. Root
cause: the `csrf_token` cookie was not reaching the origin through CloudFront,
so the classic cookie==header double-submit failed (while the access_token
cookie worked). Fix: `require_csrf` now also accepts header == HMAC(JWT_SECRET,
"csrf:"+session_sub); login + csrf-refresh issue this session-bound token — no
cookie required, still unforgeable cross-site. Curl-verified with the csrf
cookie stripped. Bundles: pmc-backend-v56b.zip / pmc-frontend-v56b-prod-build.zip.

## Prev — v56a (18 Jun 2026) — footer version, country-name pickers, company city/zip, CSRF refresh endpoint + escrow backfill endpoint
Completes the v55 phase. All four verified in preview (testing_agent iter 89
Bidding Ops 100%; iter 88 the other three PASS):
1. **Bidding Ops assignment UI** (`/admin/e/bidding`): click a bid row → detail
   panel → **Assign specialists** modal (one dropdown per role, staff tagged by
   country scope / Global) → `POST /api/v1/bids/{id}/assign`.
2. **Company Master (full)** (Admin → Masters → Companies): profile
   (country→state→city→ZIP + incorporation details) + documents (Incorporation
   Certificate / MOA / AOA single slots) + Licenses (multi-file); profile save
   never wipes docs.
3. **Staff company picker**: Company dropdown on New/Edit staff → `company_id`.
4. **Escrow institution country scope**: per-institution scope editor (blank =
   Global); `?country=` filter returns global-or-matching.
Bundles: `pmc-backend-v56.zip`, `pmc-frontend-v56-prod-build.zip` — ONE combined
upload. STATUS: preview-verified; awaiting user prod deploy + confirmation
(Malaysia staff no longer see LATAM unassigned bids).

## Prev P0 — v54v (17 Jun 2026) — unified /login fix (CloudFront HTML-200 error pages)
Staff could log in via /staff/login but NOT via the unified /login. Root cause:
CloudFront "Error Pages" rewrites a backend 403/404 on /api/* into index.html
with HTTP 200. The unified /login "PMC staff" option probes each staff role; the
first wrong-role attempt got a 403 that CloudFront turned into a fake 200+HTML,
which the app read as a successful sign-in → navigated to /staff with NO cookie →
/me 401 → bounced to /login?expired=1. (/staff/login works because you pick the
exact role, no wrong-role attempt.) Fix (frontend): (1) central axios guard in
lib/api.js rejects any /api response whose body is HTML (a CloudFront error page)
so it is handled as the error it is — protects staff loop, escrow login, and all
future calls; (2) SignInE staff loop only treats a JSON object with active_role as
success. Verified in preview: unified /login as PMC staff → reviewer 403 →
escrow_agent 403 → certifier 200 → /me 200 → lands on /staff. Bundles:
pmc-backend-v54v.zip (code == v54u + version bump), pmc-frontend-v54v-prod-build.zip.
Recommended complete server-side fix: replace CloudFront custom error responses
with a CloudFront Function for SPA routing so /api errors pass through untouched.
STATUS: verified in preview; awaiting user prod deploy + confirmation on /login.

## Prev P0 — v54u (17 Jun 2026) — REAL staff-login fix (Safari / first-party cookie)
ACTUAL confirmed root cause of "staff can't log in" on the real domain. Proven
live: server + CloudFront are correct (clean Chromium logs in, /me 200, lands on
/staff; curl gets Set-Cookie). It failed in SAFARI (incl. Private) + the user's
browser even in Incognito → never a cache or CloudFront problem. Cause: backend
set the session cookie SameSite=None;Partitioned (CHIPS) — needed ONLY for the
cross-site preview iframe. On the same-origin production domain
(www.pmcmanagers.com serves both site + /api), Safari/ITP REJECTS that cookie
first-party, so it's never stored → next /me is unauthenticated → bounce.
Fix (security.py): cookies are now context-aware. Production/same-origin/localhost
→ SameSite=Lax;Secure. Preview sandbox only (Origin contains preview.emergentagent.com)
→ SameSite=None;Secure;Partitioned. Applied to staff+admin login, switch-role,
and logout clears (clears match set attrs). Verified locally: prod-origin login →
access_token+csrf_token = Lax, /me 200; preview-origin → None;Partitioned.
No CloudFront change needed (/api/* already CachingDisabled + AllViewer = correct).
Bundles: pmc-backend-v54u.zip, pmc-frontend-v54u-prod-build.zip. STATUS: built +
verified locally; awaiting user prod deploy + Safari confirmation.

## Prev P0 — v54s (17 Jun 2026) — staff-login attempt (SameSite=None cookie) [SUPERSEDED by v54u]
Reproduced on prod: staff login returns 200 but the next /me returns 401 →
bounced to /login ("staff can't log in"). Cause: access_token cookie was
SameSite=Lax, which prod CloudFront drops (preview ingress rewrote it to
None;Partitioned, masking it). Fix: set access_token with
HttpOnly;Secure;SameSite=None;Partitioned (security.set_access_cookie) + matching
clear on logout. Verified via local Set-Cookie. Affects all staff+admin logins.

## Prev P0 — v54r (17 Jun 2026) — ROOT CAUSE of recurring login crash
Production ran v54q on the server but browsers ran OLD v54n JS: the SW
CACHE_VERSION was frozen at pmc-shell-v54n across v54o/p/q, so the SW never
updated and served the stale cache (old buggy /undefined login). CloudFront also
edge-cached service-worker.js + index.html. Fix: bumped SW to pmc-shell-v54r so
the SW bytes change on deploy → browsers reinstall → activate purges old cache.
Deploy REQUIRES a CloudFront /* invalidation. Recommended: no-cache on
service-worker.js + index.html.

## Prev P0 — v54q (17 Jun 2026) — Account type (Admin vs Staff)
Added an explicit `account_type` (admin|staff) to staff records. Staff-type
accounts cannot hold admin/reviewer and only reach /staff; admin-type reach the
admin console. Enforced server-side on create+update (`staff_auth._validate_account_type`),
legacy records backfilled on read, Staff Master UI has an Account Type radio that
hides Admin/Reviewer for staff. SUPERSEDES v54p (which had a privilege-escalation
bug — reverted). Verified: 6 curl scenarios + UI + iteration_87 RBAC suite.

## Prev P0 — v54p (17 Jun 2026) — Staff login hardening
Production report: staff set to `admin + escrow_agent` crashed on login
("Signed in · undefined" → blank `/undefined`). Root cause = STALE production
build; current code is safe (verified). Shipped hardening in `SignInE.jsx`: the
"PMC staff" card also tries `admin` fallback; navigation never reads an
undefined role; high-risk-role-without-MFA now shows the exact "enable 2FA"
message. Deploying v54p backend makes `/api/v1/_version=v54p`, which triggers the
version guard to auto-clear stale clients. Artifacts: pmc-{backend,frontend}-v54p.

## Prev P0 — v54o (17 Jun 2026) — Staff RBAC end-to-end
Specialist staff (escrow signer / certifier / etc.) were seeing the FULL
admin console. Root cause: `/admin` + `/admin/e/*` had no frontend role
guard. Fix: `RequireAdmin` guard (admin + reviewer only; others → `/staff`)
+ tightened all remaining any-staff backend endpoints to `require_role(...)`.
Verified: certifier → 403 on admin data, bounced from `/admin`; admin → full
console. See CHANGELOG v54o for the enforced role→access map.

## Previous P0 — v54h all-in-one (17 Feb 2026)
v54h = v54g + default-country-fix + upload polish:
- `/register` default country now blank with localStorage memory of last
  pick (no more "Kazakhstan by default").
- DocSlot captures the actual rid/tok used for the upload call and uses
  them as a fallback for the View/Download links so the action buttons
  render immediately on upload, not only when parent re-renders.
- `saveDraft` logs stray non-whitelisted fields to the browser console
  and drops them (defence in depth) so the opaque "Extra inputs are not
  permitted" 422 can't block a user — the exact offending field name is
  now diagnosable from console logs.
- Build stamp bumped to v54h.
Deploy the v54h pair and skip all earlier v54x bundles.

## Current P0 — v54g all-in-one (17 Feb 2026)
v54g = v54f + visible build stamp + prod URL fix:
- `.env` default `FRONTEND_URL` changed from the Emergent preview to
  `https://pmcmanagers.com` — root cause of "upload works, then file is
  gone when I open the emailed resume link" was that production emails
  were pointing to the preview environment, so clicking the link opened
  a different environment where the file never existed.
- Public `/api/v1/_version` endpoint + footer stamp showing frontend AND
  backend bundle versions, so we can confirm which bundle is live from
  any browser before testing.
Deploy the v54g pair and skip all earlier v54x bundles.

## Current P0 — v54f all-in-one (17 Feb 2026)
v54f = v54e + resume-link repair: the SEC-002 existing-draft path no longer
navigates to `token=undefined` (root cause of "upload view/download broken
+ email not populated" from the emailed resume link), invalid tokens get a
clear message, the resume page shows the vendor's email, and legacy rows
without magic tokens get one minted on first use. Deploy the v54f pair and
skip all earlier v54x bundles.

## Current P0 — v54e all-in-one (17 Feb 2026)
v54e = v54d + registration validation pack: country-format regex checks
(reg no / tax ID), mandatory non-future incorporation date, ISD phone
dropdowns, country-filtered bank datalist with SWIFT autofill, numeric-only
turnover, UNSPSC mousedown-click fix + comma custom chips, upload
view/download/persist verified via 13-check browser run.
Deploy the v54e pair and skip all earlier v54x bundles.

## Current P0 — v54d all-in-one (17 Feb 2026)
v54d = v54c (registration + escrow fixes) + searchable country combobox in
Section D Operating Regions (type-to-filter with matches on top, full list
below; verified live). Deploy the v54d pair and skip v54c.

## Current P0 — v54c FINAL all-in-one (17 Feb 2026)
v54c bundles = v54a (escrow EMD pack) + v54b (registration unblocked) +
v54c (signature whitelist + upload persistence). Deploy ONLY the v54c pair.

v54c root fixes on top of v54b:
- `REGISTRATION_UPDATE_FIELDS` whitelist (api.js) was missing
  `signature_name/title/date` and `directors` — the browser silently
  dropped the signature block on every save → Submit always 400'd with
  "Missing signature field: signature_name". Whitelist extended.
- `adminApi.registrationAdminUpdate` bypassed the whitelist → admin
  "Edit sections" 422'd on extras. Now routed through `_stripRegExtras`.
- `document_slots` deliberately excluded from save whitelist — upload
  state is owned exclusively by the slot endpoints; stale-tab PATCHes
  can no longer wipe uploaded files.
- Verified E2E against preview: create → upload → save → resume →
  view file 200 → submit 200.

## Current P0 — Escrow EMD operational pack (v54a, 16 Feb 2026)
Delivered in this release:
- Signatory-pool returns `{pmc_officers, institutions}` reliably; now also
  surfaces each approved institution's **primary contact** as a fallback
  signatory so the institution-officer dropdown is never empty for a
  correctly approved institution.
- Admin → Joint Escrow Accounts → Edit signers now includes an **Escrow
  institution** picker that rebinds the account to an approved master
  (fixes "institution signatory dropdown locked forever" when legacy
  free-text institution name doesn't match any master).
- Admin → EMD transactions ledger → **Send DocuSign envelope** per row.
  Builds a 2-signer PDF, emails both officers the DocuSign hosted link,
  mirrors status onto the transaction.
- Escrow institution dashboard transaction rows are now clickable and
  open a **Transaction Detail Modal** showing: both signatories with
  signature state, DocuSign envelope status + Open-in-DocuSign button,
  **payment entries ledger** (payment-in / release / refund / fees) with
  proof upload + dual-sign per entry, and the full audit trail.
- Payment entries sub-collection with per-entry dual-signature workflow.
- Resilient DocuSign fallbacks: auth/consent failures surface as 503;
  both admin-side and institution-side `docusign-url` degrade to
  `{mode: 'email_only'}` and the UI tells the signer to open the
  DocuSign email instead of showing a 502.
- `transactions/init` now enforces the same-email governance guard at
  init time, so broken legacy accounts can never accept inbound EMD.
- Legacy joint-account rows show "institution not set" instead of a
  blank "· ·" separator.

Testing status: backend pytest `test_v54a_escrow_payment_entries.py`
(15/15) + E2E review `test_v54a_e2e_review.py` (15/15, iteration_85:
signatory pool, account create/edit+rebind, ledger init + duplicate
guard, DocuSign graceful 503, magic-link issuance, institution-portal
dashboard + tx detail + payment-entry create/sign/void, 403 foreign-tx
authorisation). Verified live via curl: missing-officer 400 guard,
503 DocuSign fallback, cancel 200. Frontend smoke (Playwright): both
portals render without 500s. Production verification pending — user
must upload v54a bundles to EB + S3/CloudFront.

## Must-have invariants
- Escrow institution status `approved` is NOT enough — the institution
  must have `signatories[]` registered (or an opted-in primary contact)
  for admin dropdowns and dual-sign to work end-to-end.
- At least one active staff flagged `is_escrow_signatory=True` must exist
  for the PMC side of every joint account.
- EMD payments auto-create a ledger transaction via
  `routers.escrow.auto_init_from_emd_payment`. Zero-EMD bids skip the
  escrow-staff step but keep the audit trail.
- Both officers must sign the identical release action before Release
  fires. Same-email on both officer slots is rejected at create + patch.
- Payment entries also require dual-signature (admin PMC side + institution
  side) before they are considered posted.

## Known production operability gaps
- Production deployment bundles must be uploaded by the user — we cannot
  push directly to AWS from this environment. Latest bundle to upload is
  `pmc-backend-v54a.zip` + `pmc-frontend-v54a-prod-build.zip`.
- Institution portal signatory onboarding depends on the institution's
  primary-contact completing the "Invite a teammate as signatory" form.
  v54a backfills the primary contact as a signatory option so the
  institution is never un-pickable just because that form wasn't run.

## Live stack
- Backend: FastAPI (`/app/backend/server.py`) with motor/MongoDB, JWT +
  CSRF double-submit cookies. New escrow routers:
  `escrow`, `escrow_institutions`, `escrow_signatories`, `escrow_accounts`,
  `escrow_payment_entries` (v54a).
- Frontend: React/CRA. Escrow surfaces: `admin-console/escrow/*`,
  `escrow-portal/*`, admin institutions management under
  `admin-console-e/AdminEscrowInstitutionsE.jsx`.
- Integrations: Stripe (EMD payments + webhook), DocuSign (award + escrow
  envelopes), Resend (transactional emails), AWS EB/S3/CloudFront
  (manual deploys), Emergent crons (vendor digest, escrow jobs).

See `/app/memory/CHANGELOG.md` and `/app/memory/ROADMAP.md` for history
and backlog.

## Status note — v54i (17 Feb 2026): registration upload "still broken" = stale client
- The long-running "uploads don't View/Download / vanish on save" report was
  reproduced against the user's EXACT production resume link in a clean
  browser and found to be ALREADY WORKING on the deployed build: Sections A,
  C and D upload, render VIEW/DOWNLOAD/DELETE, and persist through Save +
  reload; backend returns all `document_slots` and the file endpoint 200s.
- Root cause of the user still seeing it: their browser ran a cached older JS
  bundle (service worker / CloudFront edge). Fix shipped in v54i: version
  self-heal guard (`frontend/src/lib/versionGuard.js` + `index.js`) that
  reloads stale clients once when `/api/v1/_version` > baked build version,
  plus SW `skipWaiting()` and `CACHE_VERSION=pmc-shell-v54i`.
- Action for user: deploy v54i pair + CloudFront `/*` invalidation. After
  that, stuck clients auto-recover on next load.

## Status note — v54j (17 Feb 2026): reference-data expansion
- Seeded postal/ZIP regex for ~86 countries (`scripts/seed_postal_formats.py`)
  — ZIP validation in the Section D office editor now fires (was dead: 0
  countries had regex).
- Country ID formats 17 → 34 (added MY/ID/TH/VN/PH/PK/BD/AE/SA/QA/EG/KE/CA/
  MX/NL/ES/IT/TR/PL); banks 159 → 198 across 26 countries. Startup bootstrap
  now upserts formats + postal on every boot so new data reaches prod.
- Section D office editor: State/City are now type-or-pick (manual entry
  allowed) for renamed/missing places. (`RegionOfficeEditor.jsx`)
- Verified by testing_agent iter 86 (100% frontend pass).
- HONEST LIMITS: complete global bank+SWIFT+routing and authoritative
  per-country license codes for all 250 countries are not public data —
  seeded major markets + kept free-text/admin-curation for the long tail.
  Backlog: expand more countries' formats/banks/licenses on request;
  optional GeoNames city-level ZIP lookup if true ZIP↔city match is needed.
- Bundles: `pmc-backend-v54j.zip`, `pmc-frontend-v54j-prod-build.zip`.


## Status note — v54k (17 Feb 2026): approve-registration 500 fix
- Approving a SUBMITTED registration threw HTTP 500 when a vendor with the
  same email already existed (same company also added via Admin→Vendors, or a
  duplicate approved earlier). Root cause: `vendors.email` UNIQUE index +
  un-caught `DuplicateKeyError` in `approve_and_create_vendor`.
- Fix: `admin_decide` approve pre-checks for an existing vendor by email →
  clear 409 naming the vendor; insert also guarded with DuplicateKeyError→409.
  (`routers/registrations.py`, `routers/registrations_helpers.py`)
- Verified in preview: collision→409 (was 500), clean approve→200 (vendor
  created), double-approve→409.
- Bundles: `pmc-backend-v54k.zip`, `pmc-frontend-v54k-prod-build.zip`.

## Status note — v54l (17 Feb 2026): vendor "Request change" document 400 fix
- Vendor Account → Company name → Request change returned HTTP 400 "supporting
  document is required" even with a file attached. Root cause: uploader set
  `evidence.key` from the direct-upload response (`r.data.key`) instead of the
  canonical presign key (`pres.data.key`); null key → backend (correctly)
  rejected. Production was running an OLD frontend (main.0dfca871.js) with this
  path; current repo now uses the presign key + requires `evidence.key`.
  (`frontend/src/apps/vendor-portal-e/VendorAccountE.jsx`)
- Verified on preview via real UI (success toast + Pending request) and API
  (WITH evidence → 200, WITHOUT → 400). Backend already correct.
- Bundles: `pmc-backend-v54l.zip`, `pmc-frontend-v54l-prod-build.zip`.

## Status note — v54m (17 Feb 2026): LatAm + Africa data + upload audit fix
- ID formats 34→67 (added LatAm AR/CL/CO/PE/UY/EC/CR/DO/GT/VE/BO/PY/PA/SV/HN +
  Africa GH/MA/CI/SN/CM/TZ/UG/ET/DZ/TN/RW/MZ/ZM/ZW/AO/CD), banks 198→252,
  postal regex 86→93 (+CR/DO/GT/PY/HN/MZ). All idempotent on startup.
- Upload audit fix: `uploadsApi.uploadFile` now uses the presign key
  (`pre.key`) not the upload-response key (same null-evidence class as v54l;
  affects escrow/shared evidence uploaders). (`frontend/src/lib/api.js`)
- Verified: CL RUT format+regex, GH labels, CL/MA banks with SWIFT.
- HONEST LIMITS unchanged: long-tail bank SWIFTs best-effort; ID regex only
  where reliable (else label+example guidance, no hard block).
- Bundles: `pmc-backend-v54m.zip`, `pmc-frontend-v54m-prod-build.zip`.
- De-dup guidance given to user (MongoDB, not SQL): dry-run aggregation to
  find dup emails in registrations/vendors, then delete older copies keeping
  newest. Preview DB had 0 duplicate emails.

## Status note — v54n (17 Feb 2026): escrow registration document View/Download
- Escrow registration wizard (EscrowAccountWizard) → 4. Documents: uploaded
  KYC files only had Replace/Remove. Added View (SPA blob fetch → new tab) and
  Download (save with original filename) buttons to each slot with a file.
  Buttons render on upload + resume. (`frontend/src/apps/escrow-portal/EscrowAccountWizard.jsx`)
- Frontend-only; backend identical to v54m. Compiles clean; mirrors the proven
  uploadsApi.openFile/blob pattern used in vendor docs.
- Bundles: `pmc-backend-v54n.zip`, `pmc-frontend-v54n-prod-build.zip`.
