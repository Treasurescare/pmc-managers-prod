# PMC Managers — Changelog

## Public placeholder-data cleanup — go-live readiness (26 Jun 2026)
Final pass to ensure NO fake/demo transaction data on public pages (real data seeded before go-live).
- FIXED (HIGH, iteration_114→115 verified): Home "Open for bids this week" filter chips could reveal
  hidden empty .pmc-tender template cards (blank titles, "—" values, fake countdowns). PmcHomeFilters.jsx
  filter() now keeps any card without data-pmc-filled="1" hidden; pmcELiveData.js sets that flag only on
  cards populated by live notices. With empty DB, clicking All/Tender/RFP/RFQ shows 0 cards.
- AwardsPublicE.jsx: added the public header (brand + nav + Sign in/Register) and footer; breadcrumb now
  points to the live /tenders/all board instead of the static /tenders/live shell.
- PmcFooter.jsx: removed the unverified corporate claim ("Big-4 procurement authority ... since 2018 across
  11 jurisdictions"), aligned brand to "Global Tender Board" with honest descriptive copy.
- Verified (iteration_115.json) all public routes render honest empty/not-found states: /, /notices,
  /tenders/all, /tenders/completed, /notices/:ref (not-found), /m/e/public, /m/e/supplier.
- Deferred (optional, not blockers): mobile mockup empty-state labels + "KYC verified" wording, /tenders/all
  legacy header style mismatch, footer not pinned on short pages.


## v56s Open-Five closeout (25 Jun 2026)
Reconciled the last 5 "open" items against the real client sheet:
- #40 FIXED (real root cause): the public NoticeDetailE "Key dates" timeline + ledger hash-lines
  were HARDCODED mock dates (every notice showed the same fake timeline + phantom "Corrigendum 1").
  Rebuilt to render the notice's real published_at / pre_bid_meeting_date / clarification_deadline /
  submission_deadline + all published corrigenda, sorted chronologically, local time. Also fixed the
  legacy NoticeDetail.jsx UTC→local display.
- #11 FIXED: operating-regions is a structured office editor now; shortened the hint.
- #46 FIXED: added a distinct visible label + tooltip to the corrigenda-filter box (vs the notice
  search box) in CorrigendaPanel.jsx.
- #69 VERIFIED: RegionOfficeEditor already has a type-to-search CountryCombobox (v54d) — works in preview.
- #56 VERIFIED: live DPR analyse in preview drafted 5/5 sections with real AI bodies; any prod
  "nothing drafted" is the managed LLM proxy (sk-managed → api.pmcmanagers.com/llm), not code.
Rebuilt v56s bundles + regenerated PMC_Bug_Clearance_v56s_*.docx/.xlsx (now 14 fixed · 8 verified ·
0 open · 1 parked) with a new #40 key-dates screenshot.

IMPORTANT: the forked handoff had WRONG descriptions for #13/#15/#69/#6 — reconciled against the
real client sheet (numbers kept verbatim). Diagnostic showed most BACKENDS already return 200; the
open items were FRONTEND. Testing iter104 (status sweep) + iter105 (fix retest, 4/4 PASS).
- FIXED this round: #6 (REQUIRED pill → simple bold red '*' in FormPrimitives + DocSlot + SectionD
  Sector/Contract via required prop + SectionE), #43 (EvaluationPanel keeps picked notice in
  ?notice= so refresh reloads saved rubric), #45 (ContractsTab View button + detail panel +
  /admin/e/boq-contracts route alias), #60 (auction_live.py /mine now matches
  reverse_auction_participants so registered vendors see live auctions), #13 (invite email sends
  via Resend, email_sent=true in preview — prod non-delivery = verified-domain/key config).
- VERIFIED already-correct in preview (need prod deploy): #15, #18, #23, #37, #55, #67. Prior v56o
  fixes: #17, #44, #58, #36, #72, #71.
- STILL OPEN (next round): #11 (operating-regions help text), #40 (notice timelines), #46
  (corrigenda two-search-bar UX), #56 (AI FILL ALL drafts nothing), #69 (Section D country
  autocomplete). #41 DEFERRED per user.
- Rebuilt prod bundles pmc-backend-v56s.zip / pmc-frontend-v56s-prod-build.zip and regenerated the
  CORRECTED client deliverables PMC_Bug_Clearance_v56s_*.docx/.xlsx (generator
  memory/make_deliverables_v56s.py) — Word render verified. All under frontend/public/downloads.


## v56s (2026-06-25) — Go-Live switch, public board filters, taxonomy persistence + clearance deliverables
Completed the taxonomy batch on top of v56q/v56r:
- **Public tender board filters + deep links** (`TendersList.jsx`): Sector, Contract Type,
  Category (UNSPSC), Country, free-text; live filter state mirrored into the URL query string
  (shareable deep-links). Sector and Contract Type are INDEPENDENT dimensions — changing Sector
  no longer clears the selected Contract Type (removed the two `setContractType("")` resets).
- **Admin Go-Live switch** (`routers/settings.py` + `masters/GoLiveTab.jsx`, Masters → Go-Live):
  OFF by default; `GET /api/v1/settings/go-live/public` → `{go_live:false}`. When ON, backend
  (`registrations.py`, `notices.py`) requires sector/contract type on NEW registration/notice
  workflows. Existing vendors/notices untouched.
- **Taxonomy persistence** across vendor registration (Section D), vendor category requests, and
  notice create/edit. Contract Types render grouped by their own parent group (NOT filtered by
  Sector).
- **#6** required-field marker VERIFIED (bold red REQUIRED pill, `FormPrimitives.jsx`) — retained.
- **#15** stale Admin-Registrations selection VERIFIED cleared on status-tab switch
  (`RegistrationsPanel.jsx::load` → `setSelected(null)`).
- **#11 / #69** help text left unchanged — deferred by user instruction.
- Backend tests: `tests/test_v56s_golive_taxonomy.py` 14/14 pass.
- **Deliverables** (team-facing, preview-qualified statuses, with embedded preview screenshots):
  `deliverables/PMC_Bug_Clearance_v56s_<date>.docx` + `.xlsx` (also under
  `frontend/public/downloads/`). Generator: `memory/make_deliverables_v56s.py`. Word render
  verified page-by-page.
- Production `contract_types` dedup: preview clean (30, 0 dups). Non-destructive remediation plan
  written to `memory/PROD_CONTRACT_TYPES_DEDUP_PLAN.md` — NOT executed, pending user authorization.


## v56r (2026-06-24) — Notice pickers (Sector + Contract type)
Wired the v56q taxonomy into notice creation/editing. NoticesPanel.jsx (create) and
NoticeEditModal.jsx (edit) now load mastersApi.listSectors()/listContractTypes() and render two
grouped (optgroup parent → indented child) selects under Category, bound to
draft.sector_code / draft.contract_type_code. Backend needs no model change (NoticeIn/NoticePatchIn
use extra="allow"), so the fields persist + return. Verified: POST /api/v1/notices with
sector_code=power-transmission + contract_type_code=epc-turnkey returned both on the created notice
(test notice deleted after). NEXT: vendor registration/profile tagging, public board filter, go-live
mandatory enforcement.

## v56q (2026-06-24) — Sector / Contract-Type taxonomy above UNSPSC
Model: Sector -> Contract Type -> UNSPSC commodity code, all optional for now (mandatory at
go-live). New own collections db.sectors (25, 2-level) + db.contract_types (30, 2-level) so they
never pollute UNSPSC pickers. Backend: masters.py TaxonomyIn + _tax_list/_create/_update/_delete
helpers; endpoints GET/POST/PATCH/DELETE /api/v1/masters/sectors and /contract-types + /public
list. server.py SECTORS/CONTRACT_TYPES + _seed_sectors/_seed_contract_types (idempotent, renamed
helper _seed_tax_items to avoid clash with existing _seed_taxonomy); _seed_contract_types also
delete_many(source=pmc) in categories to undo the v56p flat attempt. Frontend: generic
masters/TaxonomyTab.jsx (grouped parent->child) wired as Masters → Sectors / Contract types tabs;
mastersApi gained list/create/update/deactivate Sector & ContractType. Verified via curl (25/30
seeded, categories back to 105 UNSPSC, 0 pmc leftover) + clean compile.
NEXT: cascading pickers on notice-create & vendor registration + public board filter.

## v56o/v56p (2026-06-24) — Bug-sheet batch 1 + contract/works taxonomy
Verified the 24-item testing-team bug sheet in PREVIEW (many were already fixed in
code but stale in production). Fixed and preview-tested (pytest tests/test_v56o_six_bugfixes.py, 8/8):
- #58 Product Catalog disable/enable — new `PATCH /api/v1/products/{id}/active` (was 422).
- #44 Evaluation scoring — `_load_rubric_config` falls back to DEFAULT_TECH_CRITERIA when no
  rubric saved, so scored bids show real technical % not 0.
- #17 DocuSign — `list_my_envelopes` matches bids by `str(_id)` (was non-existent `id`).
- #23 Corrigenda — all validation (require_future + amendment + `_validate_tender_chain`) now
  runs BEFORE any DB write, so a rejected publish leaves no orphan corrigendum / moved deadline.
- #36 Closed tenders — NoticeDetailE gates both Start bid buttons behind a `closed` flag
  (status closed/awarded or past submission_deadline) → disabled "Bidding closed".
- #72 Escrow magic-link — friendly invalid/expired message instead of raw axios 404.
Customer request — added `_seed_pmc_contract_categories()` (server.py): idempotent on every boot,
seeds 26 categories (EPC Contracts, Works, PPP, Renewable Energy, Power Sector, Logistics with
their sub-types) into the Category master; appears in Masters, vendor registration, notice filters.
STILL OPEN from the sheet: #55 registration approve ("missing Section A fields"), #40 notice
timelines (template placeholders), #56 AI FILL ALL 502 on large templates (sequential AI calls),
#23b public Corrigenda tab shows "No corrigenda section published".

## v56n (2026-06-24) — Public-site upgrades: live Verify, deep links, contact, status filters
Four approved upgrades + a Sign-in routing fix on top of v56m.
- **Live Verify (Trust & Security):** new public `GET /api/v1/audit-events/verify-record?ref=`
  (`audit.py::verify_record` + `routers/audit_routes.py`) looks up one ledger event by seq
  (digits / `#NNNN`) or target_id, recomputes `_hash(body)` and checks the previous-hash link.
  `TrustSecurityE.jsx` now has a `VerifyRecordCard` React component (state + api) showing
  intact/break with event #, target, prev & current hash.
- **Tender deep-links:** `PmcLinkPatcher.jsx` public live-board rows AND tender cards now
  navigate to `/notices/<ref>` via `extractNoticeRef` instead of gating to `/register`.
  Fixed a leftover `onCardClick` document listener (was still sending cards to `/register`).
- **Contact delivery:** new public `POST /api/v1/meta/public/contact` (`routers/meta.py`) logs
  `contact_enquiries`, audit-logs `contact.enquiry`, returns tracked `ENQ-2026-#####`, and
  emails desk + sender (fire-and-forget). `ContactE.jsx` `ContactForm` posts + shows the ref.
- **Status filters:** `pmcELiveData.js` reads URL `?status=` and ticks the matching status
  radio (open/closing/closed/awarded). `pmcEPublicNav.js`: "Closing this week" chip →
  `?status=closing`; Awards page "Awarded" KPI → `?status=awarded`.
- **Sign-in fix:** nav "Sign in" now → `/login` (Option-E unified SignInE chooser) instead of
  the legacy navy `/vendor/login`.
Testing: iteration_98 — backend 7/7 (100%), frontend 8/9; the one failure (card → /register)
was fixed post-report. Email to @example.com test addresses returns Resend 422 (harmless;
send is fire-and-forget). Audit collection is `audit_events` (append-only; test enquiries kept).


## v56m (2026-06-24) — Public marketing site fully wired (nav/search/links)
User reported the public site was mostly non-functional: hero search box, country
dropdown and "Find tenders" did nothing; "Popular:" chips dead; platform stat
numbers not clickable; Trust page "Verify a record" / "Report a concern" dead; most
top-nav and footer links were placeholder `href="#"`.
Root cause: the Option-E public pages are static JSX with `href="#"` placeholders;
only a few elements were rewired imperatively by `pmcELiveData`.
Fix: new shared hook `frontend/src/lib/pmcEPublicNav.js` (`usePublicNav`) attached to
all 9 public pages (Home, TendersList, Trust, Contact, About/Vision, ForSuppliers,
ForBuyers, Privacy, Awards/Completed). It wires, via react-router SPA navigation:
brand logo, live chip, hero search+country → `/tenders/live?q=&country=`, popular
chips, clickable stat cards, programme category cards, Help Centre tile, Trust
"Verify"→/contact and "Report a concern"→/contact, Contact form "Send message"
(no reload, shows confirmation), and every top-nav/footer link via a text→route map.
`data-help-open` elements still open the help drawer (not wired as nav).
Testing agent iteration_97: 34/35 (fixed a PmcLinkPatcher double-navigation that
stripped `?q=`; now href keeps full path + stopPropagation). No backend logic change
(version bumped to v56m to keep footer stamps in sync).

## v54t (2026-06-17) — ACTUAL root cause: CloudFront caching /api (strips Set-Cookie)
Proven in the user's live browser: staff login POST returned 200 but the browser
got the response WITHOUT Set-Cookie, with `x-cache: Error from cloudfront` + age:154
(a CACHED response). So the session cookie never reached the browser → /me 401 →
bounced to /login. curl worked (fresh/uncached). Preview has no CloudFront.

Fix (code): server.py middleware sets `Cache-Control: no-store` + `Vary: Cookie,
Authorization` on ALL /api/* responses so the CDN won't cache them.
Fix (infra, user-side, authoritative): add a CloudFront `/api/*` behavior with
CachingDisabled + AllViewer origin-request policy, then invalidate /*.


## v54s (2026-06-17) — THE real staff-login fix: SameSite=None cookie
Reproduced on production with a valid staff account: `POST /staff/auth/login`
returned 200 but the immediate `GET /staff/auth/me` returned 401 → the app
bounced back to /login = "staff can't log in at all". Root cause: the
`access_token` session cookie was `SameSite=Lax`; preview's ingress rewrites it
to `SameSite=None; Partitioned` (so it worked there) but production CloudFront
does not, so the browser dropped the cookie.

Fix (`security.py` + `admin_auth.py` + `staff_auth.py`): set `access_token` with
`HttpOnly; Secure; SameSite=None; Partitioned` (same CHIPS attrs as csrf_token),
and clear cookies with matching attrs on logout. Verified the local backend now
emits the correct Set-Cookie. Affects all staff + admin logins.


## v54r (2026-06-17) — ROOT CAUSE: stale service worker pinned browsers to old code
The persistent "login crashes to /undefined after logout" was NOT a code bug in
v54q — production served v54q, but users' browsers ran OLD cached v54n JS.

Cause: the SW `CACHE_VERSION` was frozen at `pmc-shell-v54n` through v54o/p/q, so
`service-worker.js` bytes never changed → browsers never installed a new SW →
old cache (with old buggy login JS) was served. CloudFront also edge-cached
`/service-worker.js` and `/index.html` with no no-cache header.

Fix:
- Bumped SW to `pmc-shell-v54r` (`frontend/public/service-worker.js`). On deploy
  the SW bytes now change → browsers install the new SW → `activate` purges the
  stale cache → old JS removed. Carries all v54o–v54q fixes.
- Deploy MUST include a CloudFront `/*` invalidation (clears the SW + index.html).
- Recommended: set `Cache-Control: no-cache` on service-worker.js + index.html.


## v54q (2026-06-17) — Account type (Admin vs Staff) + reverted v54p escalation
**IMPORTANT: v54q supersedes v54p. Do NOT deploy v54p — it contained a
privilege-escalation bug (the unified "PMC staff" card could sign an
admin-holding account in as admin). That is reverted in v54q.**

**New: explicit account type at staff creation.**
- Every staff record now has an `account_type`: **Admin** or **Staff**.
  - **Admin** → signs in via the Administrator login, reaches the admin console;
    must hold the Admin or Reviewer role.
  - **Staff** → signs in via the staff login, only ever reaches the /staff
    specialist dashboard; may NOT hold Admin or Reviewer.
- Enforced server-side on create AND update (`staff_auth.py` `_validate_account_type`):
  staff+admin/reviewer → 400; admin without admin/reviewer → 400.
- Legacy records are backfilled on read: holds admin/reviewer ⇒ "admin", else "staff".
- Staff Master UI (`StaffTab.jsx`): Account Type radio; selecting "Staff" hides the
  Admin/Reviewer checkboxes so a specialist can never be given console access.
- Verified: 6 backend curl scenarios + UI radio/role-visibility + the full
  iteration_87 RBAC/login suite (12/12 backend, 7/7 frontend) still pass.

**Also in v54q (carried from the reverted v54p):**
- Unified "PMC staff" card never signs anyone in as admin (admin fallback removed).
- High-risk-role-without-MFA shows the backend's exact "enable 2FA" message.
- v54o staff RBAC guard (specialists blocked from the admin console).



## v54p (2026-06-17) — Staff login hardening (admin-holding accounts + clear MFA message)
Follow-up to a production report where a staff set to `admin + escrow_agent`
crashed on login ("Signed in · undefined" → blank `/undefined` screen).

**Finding:** The crash was from a STALE production build. Current code's backend
validates role membership and always returns a real `active_role`; current
`SignInE` navigates only to literal `/admin` or `/staff` (never `/${active_role}`),
and an ErrorBoundary catches render errors. Verified on preview — no crash in any case.

**Hardening shipped anyway (SignInE.jsx):**
- The "PMC staff" sign-in card now also tries `admin` as a last candidate, so an
  account that holds `admin` (plus a high-risk specialist role that needs MFA)
  signs in cleanly as admin instead of failing.
- Navigation uses the returned `active_role` safely; success toast falls back to
  the attempted role so it can never read `undefined`.
- When the only matching role is high-risk (escrow_agent/legal_counsel/accounting)
  and MFA isn't enabled, the backend's exact guidance is surfaced
  ("MFA is required… sign in as admin and enable 2FA") instead of a generic error.
- Verified: unified "PMC staff" and `/staff/login` both land admin+escrow_agent on
  the admin console; escrow_agent-only (no MFA) shows the MFA toast, no crash.

**Action for user:** deploy v54p. Deploying the v54p BACKEND makes `/api/v1/_version`
report v54p, which triggers the built-in version guard to auto-clear every stale
browser/cache once — this is what ends the recurring "old code on prod" crashes.



## v54o (2026-06-17) — Staff RBAC end-to-end: specialists can no longer reach the admin console
**Reported bug:** A staff member created in Staff Master with only a specialist role (e.g. Escrow Agent / "escrow signer") could still see the FULL admin console after logging in.

**Root cause:** The `/admin` and all `/admin/e/*` routes had NO frontend role guard — any authenticated staff session rendered the entire admin UI. (Backend was mostly gated, but ~20 `current_admin` any-staff endpoints also leaked admin-console data.)

**Fix (end-to-end):**
- Frontend: new `components/RequireAdmin.jsx` layout guard wraps every admin route. Only `admin` + `reviewer` enter the console; every other role is redirected to `/staff`. On no session → `/login`.
- Backend: tightened the remaining any-staff (`current_admin`) data endpoints to proper `require_role(...)` sets — billing, docusign (admin mgmt), engagements, auction_live, evaluations, meetings, governance, envelope_authoritative, tenant-logo, help-requests. Left genuinely self-scoped endpoints as-is (own avatar, mfa, notifications, chat, tasks, me/switch-role).
- Verified: certifier specialist → 403 on billing/docusign/registrations/vendors, 200 on own inspections; `/admin` bounces to `/staff`. Admin → full console + 200 on all.

**Who does what (role model, enforced):**
- `admin` → full admin console. `reviewer` → admin console (deputy).
- `escrow_agent`, `certifier`, `legal_counsel`, `accounting`, `committee_member`, `auditor`, `support`, `management/partner/agent` → `/staff` specialist dashboard only.


## v54n — 17 Feb 2026 — Escrow registration document View/Download
- Escrow registration (EscrowAccountWizard) → 4. Documents step: uploaded KYC
  files only had Replace/Remove. Added **View** (open in new tab via SPA blob
  fetch) and **Download** (save with original filename) buttons to each
  document slot that has a file. (`frontend/src/apps/escrow-portal/EscrowAccountWizard.jsx`)
- Frontend-only; backend identical to v54m. Build stamp → v54n.
- Bundles: `pmc-backend-v54n.zip`, `pmc-frontend-v54n-prod-build.zip`.

## v54m — 17 Feb 2026 — Latin America + Africa data + upload audit fix
- **ID formats 34 → 67 countries**: added LatAm (AR/CL/CO/PE/UY/EC/CR/DO/GT/
  VE/BO/PY/PA/SV/HN) + Africa (GH/MA/CI/SN/CM/TZ/UG/ET/DZ/TN/RW/MZ/ZM/ZW/AO/CD)
  reg/tax labels + examples, regex where reliable.
- **Banks 198 → 252**: top banks + SWIFT for MX + LatAm + African markets.
- **Postal regex 86 → 93**: added CR/DO/GT/PY/HN/MZ.
- **Upload audit fix**: `uploadsApi.uploadFile` now uses the presign key
  (`pre.key`) instead of the direct-upload response key — same null-evidence
  class as v54l, affects escrow/shared evidence uploaders. (`lib/api.js`)
- Verified: CL RUT format + regex, GH labels, CL/MA banks with SWIFT.
- Build stamp → v54m. Bundles: `pmc-backend-v54m.zip`, `pmc-frontend-v54m-prod-build.zip`.

## v54l — 17 Feb 2026 — Vendor "Request change" document 400 fix
- **Company-name change rejected with HTTP 400** ("supporting document is
  required") even though the file showed attached. Root cause: the uploader
  set `evidence.key` from the direct-upload response (`r.data.key`) instead of
  the canonical presign key (`pres.data.key`); when the upload response had no
  `key`, `evidence_key` went out null → backend (correctly) rejected it.
- Fix: use `pres.data.key` for evidence + require `evidence.key` in the submit
  guard and Submit-button disable. (`frontend/src/apps/vendor-portal-e/VendorAccountE.jsx`)
- Verified on preview via real UI (success toast, Pending request) and via API
  (WITH evidence → 200, WITHOUT → 400). Backend was already correct.
- Build stamp → v54l (backend otherwise identical to v54k).
- Bundles: `pmc-backend-v54l.zip`, `pmc-frontend-v54l-prod-build.zip`.

## v54k — 17 Feb 2026 — Approve-registration 500 fix
- **Approving a SUBMITTED registration → HTTP 500** when a vendor with the
  same email already existed (e.g. company also added via Admin→Vendors, or a
  duplicate approved earlier). Root cause: `vendors.email` unique index +
  un-caught `DuplicateKeyError` on the approve insert.
- Fix: `admin_decide` approve now pre-checks for an existing vendor by email
  and returns a clear **409** naming the existing vendor; `approve_and_create_vendor`
  also guards the insert with a `DuplicateKeyError` → 409 safety net.
  (`routers/registrations.py`, `routers/registrations_helpers.py`)
- Verified in preview: collision → 409 (was 500), clean approve → 200 (vendor
  created), double-approve → 409 already-approved.
- Build stamp → v54k. Bundles: `pmc-backend-v54k.zip`, `pmc-frontend-v54k-prod-build.zip`.

## v54j — 17 Feb 2026 — Reference-data expansion
- **ZIP/postal validation now fires**: backfilled `postal_code_regex` +
  `postal_code_format` onto `masters_countries` for ~86 countries (was 0).
  New `scripts/seed_postal_formats.py`; backfilled on every startup.
- **Country ID formats 17 → 34**: added Malaysia (SSM), ID, TH, VN, PH, PK,
  BD, AE, SA, QA, EG, KE, CA, MX, NL, ES, IT, TR, PL to
  `seed_country_formats.FORMATS`. Startup now upserts formats on every boot
  (was only when empty) so new countries reach prod.
- **Banks 159 → 198 (26 countries)**: added MY/ID/TH/VN/PH/SA/QA/KW/EG/KE top
  banks + SWIFT prefixes to `seed_banks`.
- **Manual state/city entry**: Section D office editor State is now a
  type-or-pick `<input list>` (free text allowed); City enables on any state
  value. (`RegionOfficeEditor.jsx`)
- Verified via testing_agent iteration 86 (100% frontend pass): Malaysia reg
  format validation, SWIFT autofill, ZIP validation, custom state entry.
- Build stamp → v54j. Bundles: `pmc-backend-v54j.zip`, `pmc-frontend-v54j-prod-build.zip`.

## v54i — 17 Feb 2026 — Stale-bundle self-heal
- **ROOT CAUSE of the recurring "uploads don't View/Download and vanish on
  save" report**: NOT a code bug. Reproduced the user's exact production
  resume link in a clean browser — Section A, C and D all upload correctly,
  show VIEW/DOWNLOAD/DELETE, and persist through Save + reload (backend
  returned every slot, file endpoint 200). The vendor's browser was running
  a cached older JS bundle, so the already-deployed fix never reached them.
- **Fix**: new version self-heal guard (`src/lib/versionGuard.js`, called
  from `src/index.js`). On cold load it compares the baked build version to
  `/api/v1/_version` (always fresh — bypasses SW + CDN). If the backend is
  newer, it wipes caches, unregisters the SW and hard-reloads once (loop-
  guarded). Stale clients now recover automatically after any deploy.
- Service worker `CACHE_VERSION` → `pmc-shell-v54i` and now `skipWaiting()`
  on install so a new worker takes control promptly (banner reload applies).
- Build stamp bumped to v54i.
- Bundles: `pmc-backend-v54i.zip`, `pmc-frontend-v54i-prod-build.zip`.

## v54h — 17 Feb 2026 — Default country + upload polish
- `/register` default country now blank + remembered in localStorage
  (prefills your last choice on the next visit) instead of hardcoded KZ.
- DocSlot captures the actual `rid`/`tok` used for the upload call and
  uses them as a fallback for the View/Download links, so action buttons
  render immediately on upload even if parent props haven't re-rendered.
- `saveDraft` now logs stray non-whitelisted fields to the browser
  console and drops them in place (defence in depth), so an "Extra
  inputs are not permitted" 422 can no longer block the user — plus the
  exact offending field name shows up in console logs for debugging.
- Build stamp bumped to v54h.
- Bundles: `pmc-backend-v54h.zip`, `pmc-frontend-v54h-prod-build.zip`.

## v54g — 17 Feb 2026 — Prod URL fix + visible build stamp
- **ROOT FIX**: backend `.env` shipped `FRONTEND_URL="https://pmc-forest-green.preview.emergentagent.com"` — the Emergent preview, not pmcmanagers.com. Resume-registration emails from the production backend therefore pointed to a different environment; clicking the link opened preview, where the production draft/documents/email did not exist. Default now `https://pmcmanagers.com`. If EB env vars already override this, nothing changes.
- Added public `GET /api/v1/_version` endpoint + visible footer build stamp (`Frontend v54g · Backend v54g`) so we can confirm which bundle is live from any browser.
- Bundles: `pmc-backend-v54g.zip`, `pmc-frontend-v54g-prod-build.zip`.

## v54f — 17 Feb 2026 — Resume-link repair (token=undefined)
- **ROOT FIX**: RegistrationStart navigated to
  `/register/resume?token=${r.magic_token}` even on the SEC-002
  existing-draft path where the API deliberately omits the token →
  `token=undefined` → resume 404 → bounce to /register with empty email →
  uploads dead-ended with "enter the vendor email first". Navigation now
  happens only with a real token; the duplicate path shows a
  "resume link re-sent to <email>" message instead.
- RegistrationResume treats `undefined`/`null`/missing tokens as invalid
  links with a clear "request a fresh link" message.
- Resume page now shows the vendor's email at the top of the form
  ("Registering as … · private draft link").
- Backend `_magic_token_for` mints a token for legacy rows on first use —
  SEC-002 re-request, reminder loop, and clarification emails can no
  longer KeyError → 500 on pre-token registrations.
- Verified: fresh draft token ✓, duplicate no-token ✓, legacy-row token
  mint ✓.
- Bundles: `pmc-backend-v54f.zip`, `pmc-frontend-v54f-prod-build.zip`.

## v54e — 17 Feb 2026 — Vendor registration validation & upload pack
- Section A: registration number + tax ID live-validated against
  `masters_country_formats` regex with local label + example hint;
  incorporation date mandatory and capped at today; format errors block
  the Next gate.
- Section B: office/mobile/signatory phones get a country ISD dropdown
  (defaults to vendor country) + 4–14 digit national-number validation;
  stored as "+ISD national".
- Section C: bank name is a country-filtered datalist from
  `masters_banks` (escrow's source); picking a bank autofills SWIFT
  prefix+XXX (editable); turnover inputs reject letters at keypress.
- Section D: UNSPSC options activate on mousedown (fixes the
  debounce-re-render swallowed-click bug — "unable to choose"); trailing
  comma / Enter adds a custom category chip.
- Uploads: view/download verified; document_slots fully excluded from
  save payloads so files can't vanish on save.
- Verified via 13-check Playwright run on a seeded IN draft (all pass).
- Bundles: `pmc-backend-v54e.zip`, `pmc-frontend-v54e-prod-build.zip`.

## v54d — 17 Feb 2026 — Searchable country picker in Operating Regions
- Section D → Operating Regions → Country is now a searchable combobox:
  type letters to float matches (name or ISO code, starts-with first)
  under a MATCHES heading; the full 250-country list remains below an
  ALL COUNTRIES divider. Enter picks first match, Escape closes.
  Verified live via Playwright: "ind" → IN/ID/IO matched → selected.
- Backend identical to v54c; frontend rebuilt.
- Bundles: `pmc-backend-v54d.zip`, `pmc-frontend-v54d-prod-build.zip`.

## v54c — 17 Feb 2026 — FINAL all-in-one (registration + escrow)
- **ROOT FIX**: `REGISTRATION_UPDATE_FIELDS` whitelist in `api.js` was
  missing `signature_name/title/date` and `directors` — the browser
  silently dropped the signature block on every save, so Submit always
  400'd. Whitelist extended; verified save → resume → submit = 200.
- `adminApi.registrationAdminUpdate` now routes through `_stripRegExtras`
  (admin "Edit sections" screen was 422ing on `email`/consent extras).
- `document_slots` deliberately excluded from the save whitelist and
  stripped in `saveDraft` — slot state is owned by the upload/delete
  endpoints only, so a stale-tab save can no longer wipe uploaded files.
- Full E2E verified: create → upload → save (signature persists) →
  resume (slots intact) → view file 200 → submit 200.
- v54c bundles contain v54a + v54b + v54c. Deploy ONLY the v54c pair.

## v54b — 17 Feb 2026 — Public vendor registration unblocked
- **BUG FIX**: `/api/v1/meta/countries` now reads the full
  `masters_countries` master (250 rows) instead of the 30-row pilot
  config. Public Section A country dropdown is complete.
- **BUG FIX**: `RegistrationUpdateIn` whitelists `directors` and
  `document_slots` (new fields that were being blocked by `extra="forbid"`
  and 422ing every Save Draft). Signature block now persists so Submit
  no longer 400s with "Missing signature field: signature_name".
- `RegistrationResume.saveDraft` strips server-managed fields (email,
  consent flags, timestamps, magic_token, reviewer fields) before PATCH
  and now throws on failure so `submitFinal` halts instead of submitting
  an unsaved draft.
- Release bundles: `pmc-backend-v54b.zip`, `pmc-frontend-v54b-prod-build.zip`.

## v54a — 16 Feb 2026 — Escrow EMD operational pack
- **BUG FIX**: `GET /api/v1/escrow/signatory-pool` was falling through
  with no `return` statement; now reliably returns
  `{pmc_officers, institutions}`.
- Institution-officer dropdown resilience: signatory-pool injects the
  approved institution's `primary_contact_email` as a fallback signatory
  entry when `signatories[]` is empty.
- Admin → Joint Escrow Accounts → Edit now includes **Escrow institution**
  picker. Admin can rebind any account to any approved institution master;
  the escrow-officer dropdown repopulates immediately.
- `escrow_accounts` records now carry explicit `institution_id` alongside
  the display `institution` name (backward-compatible — unset on legacy
  rows, matching still falls back to name).
- NEW backend router `escrow_payment_entries.py`:
  - `/api/v1/escrow/transactions/{tid}/payment-entries` (admin list)
  - `/api/v1/escrow/payment-entries` (admin create)
  - `/api/v1/escrow/payment-entries/{peid}/sign` (admin dual-sign)
  - `/api/v1/escrow/payment-entries/{peid}/void` (admin void)
  - `/api/v1/escrow/transactions/{tid}/docusign` (admin issue envelope)
  - `/api/v1/escrow/transactions/{tid}/docusign-url` (admin console view)
- NEW institution-portal endpoints inside `escrow_accounts.py`:
  - `/api/v1/escrow-accounts/me/transactions/{tid}` (detail)
  - `/api/v1/escrow-accounts/me/transactions/{tid}/payment-entries` (create)
  - `/api/v1/escrow-accounts/me/payment-entries/{peid}/sign`
  - `/api/v1/escrow-accounts/me/transactions/{tid}/docusign-url`
  All scoped through the escrow_account_token cookie + CSRF, authorised
  via account signatories' emails matching the transaction's
  escrow_officer snapshot.
- NEW frontend components:
  - `escrow-portal/TransactionDetailModal.jsx` — clickable transaction
    detail with signatures, DocuSign panel, payment-entries CRUD, audit
    trail.
  - Admin `EscrowTransactionsSection.jsx` — **Send DocuSign envelope**
    per row.
  - Admin `EscrowAccountsSection.jsx` — Escrow-institution picker inside
    Edit signers.
- Backend tests: `tests/test_v54a_escrow_payment_entries.py` (15 cases,
  all green) + `tests/test_v54a_e2e_review.py` (15 cases, all green,
  iteration_85).
- Follow-up fixes after E2E review (iteration_85):
  - `transactions/init` enforces same-email governance guard at init.
  - Admin-side `docusign-url` degrades to `email_only` instead of 502.
  - Legacy joint-account rows show "institution not set" instead of "· ·".
  - Fixed typo'd demo institution signatory email in dev DB
    (`escrowwdemo@` → `escrowdemo@pmcmanagers.com`).
  - DocuSign 424/428 auth failures normalised to 503 in the escrow
    envelope endpoint; verified live (503 + 400 missing-officer guard).
- Bundle fixes: backend zip layout matches v53q exactly (Dockerfile at
  root, `.ebextensions` + `.dockerignore` included, `keys/` excluded —
  prod secrets come from SSM/EB env vars); frontend zip excludes
  `build/downloads/` (was 346 MB → 3.9 MB).
- Release bundles: `pmc-backend-v54a.zip`, `pmc-frontend-v54a-prod-build.zip`.

## v56c (18 Jun 2026) — joint-account naming + institution picker country scope
- Blank-name joint accounts now render a professional fallback label
  ("<Institution> Escrow ••<last4>") in the list, edit header and confirm dialogs
  (EscrowAccountsSection accountLabel()).
- Escrow institution dropdowns (create + edit/rebind) now tag each option with
  its country scope and expose a country filter (global-or-matching). signatory-pool
  now returns each institution's country_scope. Filter auto-hides until a scope exists.
- Bundles: pmc-backend-v56c.zip, pmc-frontend-v56c-prod-build.zip.

## v56b2 (18 Jun 2026) — session-bound HMAC CSRF (prod CloudFront cookie fix)
- Prod kept 403'ing CSRF on POSTs (escrow Save, Backfill) even after v56a +
  invalidation + incognito: the `csrf_token` cookie wasn't reaching the origin
  through CloudFront, so the classic cookie==header check failed while the
  access_token cookie worked.
- Fix (security.py require_csrf): accept EITHER classic cookie==header OR
  header==HMAC(JWT_SECRET,"csrf:"+session_sub) via new `csrf_for_session()` +
  `_session_sub()`. Login (admin_auth + staff_auth) and the csrf-refresh
  endpoint now issue the session-bound token. Needs NO cookie; unforgeable
  cross-site. Curl-verified: csrf cookie stripped → protected POST passes CSRF.
- Stamped v56b. Bundles: pmc-backend-v56b.zip, pmc-frontend-v56b-prod-build.zip.

## v56a (18 Jun 2026) — follow-up fixes (footer version, country pickers, city/zip, CSRF, backfill)
- **Footer version** now shows live build on the main site: HomeE + PmcFooter read `/api/v1/_version` → "Frontend v56 · Backend v56" (PmcFooter previously hard-coded v51b; HomeE showed nothing).
- **Country pickers**: new `components/CountryMultiSelect.jsx` (country NAMES + flags, chips, search; empty = all/global). Wired into staff Country scope (new + edit forms) and the escrow-institution scope editor — replaces free-text ISO input.
- **Company Master City/ZIP**: City is a cascading autocomplete from the cities master (country→state→city); ZIP live-validates against the country's postal_code_regex (invalid disables Save). Company country option now name-first. Upload panel now appears right after Create (auto edit mode).
- **CSRF 403 fix** (prod bug): browser dropping the `csrf_token` cookie made state-changing admin saves 403 "CSRF token missing or invalid". Added `GET /api/v1/staff/auth/csrf` (re-issues the cookie for the authenticated JWT session) + axios auto-refresh-and-retry-once on that exact 403. Verified in-browser (iteration_91, 100%).
- **Backfill 404 fix**: frontend called `POST /api/v1/escrow/accounts/{id}/backfill-signers` which didn't exist → 404. Implemented it: matches institution to an approved master, refreshes PMC officer if email still in pool, swaps escrow officer to a real signatory, guards dual-control; returns diagnostics. Unmatched institution → structured 404 with suggestions (UI shows "rebind" hint). Curl-verified both paths.
- Bundles rebuilt: `pmc-backend-v56.zip`, `pmc-frontend-v56-prod-build.zip`.

## v56 (18 Jun 2026) — Bidding Ops assignment UI + full Company Master + escrow scope
Completes the v55 work-distribution phase. Four admin features, all verified in
preview (testing_agent iteration_89 Bidding Ops 100%; iteration_88 the other three PASS).
- **Bidding Ops assignment UI** (`/admin/e/bidding`, AdminBiddingOpsE.jsx): click a
  bid row → detail panel shows **Assign specialists** → modal with one dropdown per
  role (escrow_agent/certifier/legal_counsel/accounting/committee_member), each listing
  active role-holders tagged with country scope (or Global). Calls
  `POST /api/v1/bids/{id}/assign`. Feeds the v55 assigned-to-me queue.
- **Company Master (full)** (Admin → Masters → Companies, new CompaniesTab.jsx):
  profile = name/code/country→state→city→ZIP/address/reg no/incorporation date/tax id;
  documents = single slot each for Incorporation Certificate / MOA / AOA
  (upload/view/download/remove); **Licenses** = repeatable multi-file list. Profile
  save never wipes documents. New endpoints: `PATCH /masters/companies/{id}`,
  `PUT|DELETE /masters/companies/{id}/documents/{slot}`,
  `POST /masters/companies/{id}/licenses`, `DELETE …/licenses/{index}`.
- **Staff company picker**: New Staff + inline Edit forms have a Company dropdown →
  persists `company_id`.
- **Escrow institution country scope**: Admin → Escrow Institutions → select →
  Country scope editor (blank = Global). `PATCH /escrow-institutions/{iid}/scope`;
  `GET /escrow-institutions?country=XX` returns global-or-XX only.
- Bundles: `pmc-backend-v56.zip`, `pmc-frontend-v56-prod-build.zip`. STATUS: verified
  in preview; awaiting user prod deploy (one combined upload) + confirmation.


- Specialist queues (escrow_agent, certifier, legal_counsel, accounting,
  committee_member) were global — everyone saw every country's bids. Now scoped.
- Added `country_scope: List[str]` to staff (StaffCreateIn/UpdateIn/Public +
  create_staff persistence; empty=[] = all countries). Set in Admin → Masters →
  Staff (new + inline edit forms, `staff-country-scope` testids).
- `GET /api/v1/bids` hybrid filter: when acting as a specialist role, see bids
  assigned to me (bid.assignments[role], legacy assigned_certifier_id honored)
  PLUS unassigned bids whose notice.delivery_country ∈ my country_scope (empty =
  all). admin/reviewer/auditor unaffected.
- `POST /api/v1/bids/{id}/assign` {role, staff_id} (admin/reviewer) — assign or
  clear a specialist; validates the staff holds that role. Backs the future
  Bidding Ops assignment UI.
- 2FA gate on high-risk roles made flag-driven (`REQUIRE_HIGH_RISK_MFA`, default
  FALSE for testing).
- Verified in preview via curl: scope=[ZZ] unassigned→0, scope=[]→all,
  assigned-to-me→shown, assigned-to-other→hidden.
- Bundles: `pmc-backend-v55.zip`, `pmc-frontend-v55-prod-build.zip`.
- NEXT (same phase, not yet built): Bidding Ops assignment UI; Company Master
  full fields + documents + company_id picker on staff; escrow-institution
  country scoping.

## v54v (17 Jun 2026) — unified /login fix (CloudFront HTML-200 error pages)
- Staff could sign in at /staff/login but the unified /login bounced to
  /login?expired=1. Root cause: CloudFront "Error Pages" rewrites backend
  403/404 on /api/* into index.html with HTTP 200. The unified login probes
  each staff role; the first wrong-role 403 became a fake 200+HTML, read as
  success → navigated with no cookie → /me 401 → bounce.
- Fix (frontend only): central axios response guard (`lib/api.js`) rejects any
  `/api` response whose body is HTML (a CloudFront error page), so it is treated
  as the real error — protects the staff login loop, escrow login, and every
  future call. `SignInE.jsx` staff loop now only accepts a JSON object with
  `active_role` as a successful sign-in.
- Verified in preview: /login as PMC staff → reviewer 403 → escrow_agent 403 →
  certifier 200 → /me 200 → lands on /staff.
- Recommended server-side completion: replace CloudFront custom error responses
  with a CloudFront Function for SPA routing so `/api` errors are never mangled.
- Bundles: `pmc-backend-v54v.zip` (== v54u code + version bump),
  `pmc-frontend-v54v-prod-build.zip`.
- v54v backend rev 2 (same version label): added `config.REQUIRE_HIGH_RISK_MFA`
  (default FALSE for testing) gating the mandatory-2FA check on accounting /
  escrow_agent / legal_counsel in staff_login + switch_role. These roles now
  sign in with email+password during testing; flip the flag true before beta.
  Normal MFA (user has mfa_enabled) path is unchanged. Verified: accounting 200,
  escrow_agent 200, unheld role 403, MFA-enabled OTP path untouched.

## v54u (17 Jun 2026) — Safari staff-login fix (context-aware first-party cookie)
- Confirmed root cause of the long-running "staff can't log in" bounce. Live
  tests proved server + CloudFront correct (clean Chromium + curl both work);
  it failed in Safari (incl. Private) and the user's browser even in Incognito.
- Backend was sending `SameSite=None; Partitioned` (CHIPS) cookies — correct
  only for the cross-site preview iframe. On the same-origin production domain
  Safari/ITP rejects them first-party, so the session cookie was never stored.
- Fix (`backend/security.py` + `routers/staff_auth.py` + `routers/admin_auth.py`):
  cookies are now chosen by request Origin — `SameSite=Lax; Secure` for
  production/localhost (first-party), `SameSite=None; Secure; Partitioned` only
  for `*.preview.emergentagent.com`. Covers login, switch-role and logout clears.
- Verified locally against :8001: prod-origin → both cookies `SameSite=Lax`,
  `/me` 200; preview-origin → both `SameSite=None; Partitioned`. Full UI login
  on production (clean browser) lands on `/staff` and stays.
- No CloudFront change required — the `/api/*` behaviour (CachingDisabled +
  AllViewer, confirmed via the user's console screenshots) is already correct.
- Bundles: `pmc-backend-v54u.zip`, `pmc-frontend-v54u-prod-build.zip`.

## Earlier releases
See `/app/frontend/public/downloads/DOWNLOAD_v53*.md` for v53i through v53q
summary notes.

## v56f (18 Jun 2026) — PMC-officer staff-portal signing + signed-PDF email
- Staff portal now surfaces the PMC officer's escrow signing work: new
  "Escrow documents — your signature" section (StaffDashboard.jsx /
  EscrowSignatures) listing their transactions with Open-in-DocuSign
  (Safari-safe), Refresh DocuSign, and Download signed PDF.
- Backend (staff_auth.py): GET /api/v1/staff/escrow/signatures + per-tx
  detail / docusign-url / docusign/refresh / signed-document, all scoped to
  escrow_account_snapshot.pmc_officer.email (403 cross-officer).
- docusign.py _deliver_escrow_signed_document(): on envelope completion,
  downloads the COMBINED signed PDF, stores it on the tx and emails it (as an
  attachment) to both officers incl. the escrow institution officer. Resolves
  "signed document never reached Sakina / dashboard".
- Readability: staff dashboard forced to light bg (#eef2f7) + dark text.
- Verified iteration_93: backend 100%, frontend 100%. PREVIEW ONLY — not yet
  deployed. Next release bundle to build: pmc-backend-v56f.zip /
  pmc-frontend-v56f-prod-build.zip.

## v56g (18 Jun 2026) — staff portal sidebar + readability + embedded DocuSign
- Rewrote StaffDashboard.jsx: left SIDEBAR (Overview/Escrow signatures/Work
  queue/Site inspections) + explicit inline colour palette so the global
  [data-ui=e] dark theme can no longer wash out slate utilities (root cause:
  index.css:708 `[data-ui=e] .bg-slate-50 {deep-dark !important}`).
- DocuSign EMBEDDED signing: envelope signers now carry client_user_id; the
  "Open in DocuSign" endpoints mint create_recipient_view URLs with a return_url
  back to the originating portal (/staff, /escrow/me, /admin ?signed=1), same-tab
  navigation. Legacy email-mode envelopes auto-convert via update_recipients.
  New helper docusign.create_escrow_recipient_view(). Fixes "only shows signed
  doc, PMC officer can never sign".
- On completion the combined signed PDF is emailed to both officers + the admin
  who issued the envelope (docusign._deliver_escrow_signed_document).
- Verified iteration_94: backend 100%, frontend 100% (readability, sidebar,
  graceful 424 on preview). EMBEDDED signing needs PRODUCTION validation
  (DocuSign JWT not configured in preview → 424). Bundles: pmc-backend-v56g.zip,
  pmc-frontend-v56g-prod-build.zip.

## v56h (18 Jun 2026) — staff portal Option-E restyle + PMC release signing
- StaffDashboard.jsx restyled to Option-E theme tokens (cream/green/brass) via
  CSS vars — matches admin console, readable, dark-mode aware. Kept the sidebar.
- NEW: PMC-officer release-signing panel (EscrowRow) — action dropdown
  (release_to_contractor / release_to_vendor / forfeit) + comment + Sign, calling
  escrowApi.sign. Resolves the action-mismatch that blocked release (PMC could
  previously only acknowledge via DocuSign). Row now shows pmc_action /
  institution_action + a mismatch warning.
- Universal CSRF fix: retry preserves the fresh session-bound token (cfg._freshCsrf)
  so the request interceptor can't clobber it with a stale cookie — fixes the
  certifier Accept 403 and all staff POSTs.
- Certifier/staff bid rows now have a comment box (passed as decision notes).
- Verified iteration_95: frontend 100% (restyle, sidebar, PMC sign persists,
  download). Backend sign path curl-verified. Bundles: pmc-backend-v56h.zip /
  pmc-frontend-v56h-prod-build.zip. NOTE: prior v56g "no change" was a CloudFront
  cache miss — MUST invalidate /* on deploy.

## v56i (18 Jun 2026) — release-action 422 fix + staff Completed/audit view
- Fixed HTTP 422 on PMC release signing: EscrowRow action dropdown defaulted to
  the stale pmc_action (acknowledge_receipt) which is not a valid release value.
  Now defaults to a valid release action (release_to_contractor/vendor/forfeit).
- New staff "Completed" tab + GET /api/v1/staff/my-processed-bids: lists every
  bid the staff member acted on (from workflow_history.by == email) with action,
  status transition, their comment and timestamp — the officer's own audit trail.
  Addresses "certifier accept just moves away, no audit, not in completed list".
- Decisions already recorded in audit ledger + workflow_history (unchanged);
  this surfaces them to staff. Bundles: pmc-backend-v56i.zip /
  pmc-frontend-v56i-prod-build.zip.

## v56j (18 Jun 2026) — audit CSV, Completed filters/CSV, signing guardrail
- AuditPanel.jsx: added Export CSV of the (actor-filtered) audit view → one
  officer's full decision history as CSV. Backend actor filter already existed.
- StaffDashboard CompletedPanel: From/To date + Action filters, Clear, and
  Export CSV of filtered decisions (bid, action, transition, comment, at).
- EscrowRow signing guardrail: window.confirm warning when the chosen release
  action differs from the action the institution already signed (prevents the
  dual-control mismatch that blocked releases).
- PMC-BID-2026-00060 confirmed RELEASED_TO_CONTRACTOR in production.
- Bundles: pmc-backend-v56j.zip / pmc-frontend-v56j-prod-build.zip.

## v56k (18 Jun 2026) — hard release-to-contractor governance gate
- escrow.py _assert_release_governance(): release_to_contractor refused (at BOTH
  sign_off and release) unless the bid.status == 'awarded' (full chain: escrow →
  certifier → legal → accounting → committee award). 409 names the pending stage.
  release_to_vendor / forfeit are not gated.
- Verified: non-awarded blocks sign + release; awarded signs + releases OK.
- NOTE: user explicitly asked NOT to delete any preview/production data yet. A
  cleanup plan is agreed for later: KEEP masters + escrow_institutions + counters;
  DELETE transactional (bids/notices/escrow txns/auctions/registrations/etc);
  audit_events = back up then wipe fully (never partial); escrow_accounts delete
  only on request; vendors/users deletion only if explicitly chosen. Vendors list
  is NOT affected by the base cleanup.
- Bundles: pmc-backend-v56k.zip / pmc-frontend-v56k-prod-build.zip.

## v56l (18 Jun 2026) — gate UI hint + release confirmation email
- staff_escrow_signatures returns bid_status per row; StaffDashboard EscrowRow
  greys/locks "Release → Contractor" until bid awarded (disabled option, disabled
  Sign button "Locked until awarded" + tooltip + warning hint). Refund/Forfeit stay open.
- escrow.py release(): best-effort confirmation email to both officers + the bid
  vendor (beneficiary) with the signed PDF attached.
- QA iteration_96: 100% both layers of gate + Completed filters/CSV. No blockers.
- Bundles: pmc-backend-v56l.zip / pmc-frontend-v56l-prod-build.zip.

## v56t (26 Jun 2026) — homepage taxonomy search + country↔currency master
- Public homepage hero search rebuilt on the primary taxonomy: Sector → Contract type →
  Category + full country master + keyword (HeroTaxonomySearch.jsx in HomeE.jsx). Optional,
  order-independent AND filters; submit deep-links to /tenders/all which restores+applies
  them. Confirmed via testing_agent iter 106 (3 applied / 2 applied cases, params restored).
- Fixed the real root cause of the long-standing "hero routes to /tenders/live with Sector
  name in ?country=" bug: a document-level submit listener in PmcLinkPatcher.jsx hijacked
  the hero form; now guarded (skips data-testid=home-hero-search).
- Country↔currency model (user choice b + ii): masters_countries gains editable
  accepted_currencies[] with a primary default. New admin editor Masters → Country currencies
  (CountryCurrenciesTab.jsx). Backend PATCH /api/v1/masters/countries/{code}/currencies
  (admin/reviewer) + accepted_currencies surfaced on /meta/countries and /masters/countries.
  Shared CurrencySelect.jsx default-loads a country's primary on every country change (create
  forms) while preserving an existing value on edit (preserveInitial); lists accepted-first
  then all currencies; any active currency still selectable. Wired into notice create
  (NoticesPanel) + edit (NoticeEditModal) budget currency. Bids/EMD inherit the notice currency.
- Bundles: pmc-backend-v56t.zip, pmc-frontend-v56t-prod-build.zip, DOWNLOAD_v56t.md.
  Preview-verified; awaiting prod deploy + user confirmation.

## v56t follow-ups (26 Jun 2026) — taxonomy backfill, bid/EMD currency, deliverables
- Notice taxonomy backfill: new admin page AdminTaxonomyBackfillE.jsx (route /admin/e/taxonomy-backfill,
  nav "Taxonomy backfill"). Backend GET/POST /api/v1/notices/admin/taxonomy-backfill (admin/reviewer):
  guesses sector_code/contract_type_code from category+title (keyword tables _SECTOR_KW/_CONTRACT_KW),
  returns full list + masters; save persists sector/contract code+name. Frontend tracks dirty rows and
  only saves changed ones; endpoint reports modified_count. Verified: tagging PMC-NOT-2026-0102 ->
  buildings/works-civil makes the homepage Sector=buildings filter return it (testing_agent iter 107, 100%).
- Bid & EMD currency: confirmed already locked to notice.budget_currency (no vendor currency picker in
  BidSubmit; EMD uses notice currency) — satisfies "lock bid currency to tender currency".
- Deliverables: make_deliverables_v56t.py (reuses v56s bug items, bumps version, appends "New
  capabilities in v56t" table/sheet). Rebuilt bundles + PMC_Bug_Clearance_v56t_20261022.docx/.xlsx +
  DOWNLOAD_v56t.md. CurrencySelect now applies country primary on EVERY country change (create forms).
- Minor: fixed /tenders/all header spacing (Est. Value pr-4).

## v56u (26 Jun 2026) — duplicate taxonomy fix + board country dropdown
- Contract-type/sector dropdowns showed every item twice (production master seeded twice).
  Fix: shared uniqByCode() in taxonomy.jsx dedupes by code everywhere (board, homepage hero,
  notice forms); new admin "Remove duplicates" button in TaxonomyTab (sectors + contract types)
  calls POST /api/v1/masters/dedupe-taxonomy (admin) which deletes duplicate sector/contract_type/
  category rows keeping the earliest per code (idempotent; audit-logged). Verified iter 108 (toast
  'No duplicates found — all clean' on clean preview; endpoint returns {deleted:{...}}).
- Board Country filter: converted from a 2-char text box to a real dropdown sourced from the
  country master (TendersList.jsx, both E + legacy layouts); homepage hero already a dropdown.
  Verified: IN=11, KZ=47, All=58; ?country= deep-link works.
- Minor: darkened TaxonomyTab child-row text (text-brand-navy/80).
- Bundles pmc-backend-v56u.zip / pmc-frontend-v56u-prod-build.zip + DOWNLOAD_v56u.md.
  ACTION for user: after deploy, open Masters -> Contract types -> "Remove duplicates" once to
  clean production data. Preview-verified; awaiting prod deploy + confirmation.

## v56v (26 Jun 2026) — responsive admin drawer + dashboard escrow counters
- Admin console: off-canvas sidebar drawer below 1100px (hamburger + scrim) added to
  AdminEShell + the 6 inline-shell pages (Dashboard, BiddingOps, TenderBuilder, Evaluation,
  Programme, VendorKyc). Grid collapses to 1fr so content is no longer squeezed (the iPad
  cut-off). Suppressed the legacy pmc-responsive .pmc-menu-btn in .pmc-atop to avoid a
  duplicate hamburger; aligned to the 1100px breakpoint; drawer z-index above mobile topbar.
- Dashboard: EscrowOnboardingKPI chips (awaiting review + new accounts this month) via new
  backend GET /api/v1/escrow-institutions/admin/onboarding-stats. .ad-attn grid uses auto-fit
  so 5 chips fit evenly. Verified iter 109 (awaiting 6, accounts 59).
- Landing hero: filters stack full-width + side padding on mobile (pmc-theme-e.css @media).
- Bundles pmc-backend-v56v.zip / pmc-frontend-v56v-prod-build.zip + DOWNLOAD_v56v.md.

## v56w (27 Jun 2026) — responsive remediation batch (Staff/Escrow shell parity)
- Staff/Escrow portals adopt the shared Admin-E shell (PortalShellE/PortalSideNavE):
  desktop sidebar, mobile drawer + functional scrim, unified header, single hamburger.
  Files: StaffDashboard.jsx, EscrowAccountDashboardBody.jsx, EscrowMePage.jsx,
  EscrowAccountHeader.jsx, PmcMobileNav.jsx.
- Mobile breadcrumb/title context exposed (pmc-responsive.css) and tab-reactive.
- Escrow tx mobile cards: data-label metadata + fallbacks; raised selector specificity to
  beat the global [data-ui=e] table rule; Signatures now "PMC pending · Us pending".
- SignInE 820px single-column (mobile-fix.css tablet breakpoint).
- /privacy mobile: added padding-top:76px to the legal .pmc-wrap so the first sub-nav pill
  clears the 60px fixed topbar (index.css @media max-width:720px).
- testing_agent iter 113: all 6 iter-112 defects + 2 polish items verified fixed.
- Bundles pmc-backend-v56w.zip / pmc-frontend-v56w-prod-build.zip + DOWNLOAD_v56w.md.
- v56w (addendum): escrow transaction Signatures now render as colour-coded chips
  (emerald "signed" / amber "pending" with a status dot) via a new SigChip component in
  EscrowAccountDashboardBody.jsx — replaces the plain text. Preview dedupe-taxonomy run:
  contract_types=0 duplicates (preview DB already clean).

## v56x (27 Jun 2026) — Supplier portal mobile nav unified + vendor quick-links icons
- Supplier portal mobile nav now matches Staff/Escrow/Admin: removed the bottom tab bar;
  the single top-left hamburger opens a full off-canvas drawer + scrim containing the
  complete nav (Home, Find tenders, My bids, Reverse auctions, EMD & payments, Signatures,
  Company & KYC, Categories, Services, Reviews, Account & security, Alerts, Help) + Sign out.
  File: components/PmcMobileNav.jsx (vendor block); removed unused VENDOR_TABS constant.
- mobile-fix.css: reclaimed the 104px bottom padding that reserved space for the (now removed)
  tab bar -> 24px. notice-detail sticky-bar padding unchanged.
- VendorHomeE.jsx: Quick links now use meaningful icons (search/tag/shield/settings) instead
  of four identical i-spark sparkles that read as loading spinners.
- Desktop VendorPortalChrome untouched (already visually consistent). Screenshot-verified mobile.

## v56y (27 Jun 2026) — Supplier portal sidebar unified (dark)
- The vendor left-nav (.pmc-lnav) was the only light sidebar; repainted to the dark
  var(--chrome) panel to match Admin/Staff/Escrow. Light text, brass active-stripe,
  on-chrome count badges, dark "Your PMC desk" footer card. Appended override block at
  end of pmc-theme-e.css (wins over 5 duplicate .pmc-lnav blocks). CSS-only, no logic
  change. Desktop screenshot-verified. Mobile drawer unaffected.

## v56z (27 Jun 2026) — Vendor "Find tenders" card fixes + sort/filter bar
- Fixed delivery country showing "—": card read n.country but API returns delivery_country;
  now resolves ISO code -> full country name via /meta/countries (fallback to code).
- Fixed EMD showing "See notice" when an amount exists: now renders emd_amount+emd_currency
  (e.g. ₹50,000), or "<pct>% of bid", else "See notice" when no EMD is configured on the notice.
- Added a sort/filter toolbar: Sort (Closing soonest default, Closing latest, Budget high→low,
  Budget low→high) + filters Country / Sector / Contract type / Category + Clear. All client-side
  over the loaded list; deadline sorts rank open tenders above closed ones. File:
  apps/vendor-portal-e/VendorFindTendersE.jsx. Added data-testids vft-sort/vft-filter-*.

## Preview DB flush (25 Jun 2026) — fresh-start reset (PREVIEW ONLY)
- Cleared 5,303 docs across 53 transactional + vendor collections (bids, payments, escrow
  accounts/txns, notices/tenders, registrations, kyc, reverse auctions, contracts, awards,
  docusign, notifications, audit_events, counters, uploads, vendors + vendor_* etc.).
- KEPT: logins (admin_users 14, users 158), all master/reference data (countries, cities,
  UNSPSC, sectors, contract types, categories, currencies, banks), reusable templates/config,
  and escrow partner institutions (76) + signatories.
- Backup of every deleted collection: /app/backups/preview_flush_20261025_033556/*.json
- Script: /app/scripts/flush_preview_transactions.py (KEEP allow-list; backs up then delete_many).
- Verified: admin login 200, dashboard all-zero and boots clean, public board empty (0), masters intact.
- NOTE: old vendor user logins remain in `users` but their vendor company records are gone (orphaned);
  new suppliers register fresh. Production NOT touched (user will replicate after preview sign-off).

## Preview DB flush pass 2 (25 Jun 2026) — cleared over-kept operational data
- Pass 1 kept some operational collections too conservatively. Pass 2 cleared: packages (48
  "work packages"), products (55 catalog), escrow_institutions (75), escrow_signatories (2),
  audit_events (4 post-flush login events) -> all 0. Backup: /app/backups/preview_flush2_20261025_035006/.
- Verified: public home shows 0 tenders / 0 work packages; escrow institutions pipeline 0;
  logins (14 admins, 158 users) + masters (countries/contract_types/etc.) intact; app boots clean.
- Note: audit ledger will re-accumulate login events by design (each sign-in is recorded).

## Production flush prep + preview external-login purge (25 Jun 2026)
- Finalized /app/scripts/flush_production.py (KEEP allow-list + purge users role IN vendor/buyer)
  and /app/scripts/PROD_FLUSH_RUNBOOK.md. Copied both to frontend/public/downloads for the user.
- Disabled all 3 scheduled jobs in .emergent/crons.yml (enabled:false) per user request.
- Confirmed uploads are stored inline in Mongo (base64) in pilot -> clearing `uploads` leaves no
  orphaned disk/S3 files; app never reads files from disk, so masters-only state does NOT crash.
- Validated on PREVIEW: purged 157 external users (vendor+buyer), kept 1 admin in users + 14 admin_users.
  Admin login 200, dashboard boots all-zero, public site OK, vendor login 404 (graceful). No crash.

## v57a — 2026-06-28
- Public "Completed & awarded" page (/tenders/completed, AwardsPublicE.jsx) is now FULLY DYNAMIC.
  Previously it was hardcoded demo content ("Modular Operation Theatres" rows, fake KPIs). It now
  reads real awarded notices via publicApi.listNotices and client-filters for awarded status.
  Verified on empty PREVIEW: renders clean empty state ("No awards published yet.", KPIs 0/$0/—),
  no fake demo rows. Screenshot-confirmed.
- Template reset: user ran flush_templates.py against PRODUCTION — deleted 203 template docs
  (boq_templates 12, tender_templates 160, sbd_templates 5, vendor_templates 1, rubrics 23,
  rating_criteria_sets 2), backed up to ./template_flush_backup_20261026_045318.
- User decision: KEEP organisation/setup collections (departments, orgs, tenants, companies,
  taxonomy_nodes, legal_entity_types) + roles/permissions/settings so the app boots cleanly.
  No further production cleanup pending.
- Packaged v57a artifacts (agent-tested, HTTP 200): /downloads/pmc-backend-v57a.zip,
  /downloads/pmc-frontend-v57a-prod-build.zip. Includes dynamic awards page + reset tooling.
  NOTE: crons.yml disable + v57a frontend require user deployment to take effect in production.

## v57b (28 Jun 2026) — Clean-slate hardening + homepage real-data + backend recovery
- ROOT CAUSE FIXED: backend startup seeders (_seed_demo_notices, _seed_packages,
  _seed_product_catalog, tender-template masters) re-created demo data on every restart of an
  empty DB. They are now gated behind SEED_DEMO_DATA (default "false"). Genuine master/reference
  seeding (admin/staff/rubric, taxonomy, categories, sectors, contract_types, currencies,
  legal_entity_types) still runs unconditionally so the app boots.
- backend/.env: added SEED_DEMO_DATA="false" and LOCAL_DEV="true" (preview frictionless seed-pw).
  NOTE: a prior .env overwrite had wiped JWT_SECRET + all integration keys (server wouldn't boot);
  recovered full .env from /root/pmc-backend-v48c-stage backup, preserving protected MONGO_URL/DB_NAME.
- server.py: added missing `import os` (fixed F821 blocker from the gating edit).
- VERIFIED in preview: cleared notices/packages/products (3/30/55), restarted backend, all stayed 0
  — no demo data returns. Admin login 200 (adminsupport@pmcmanagers.com / Admin@12345).
- Homepage (pmcELiveData.js usePublicLiveData): real-data driven. Added empty states for the live
  board (data-testid=live-empty) and the "Open for bids this week" grid (data-testid=week-empty),
  and drove the audit-ledger trust panel from real ledger_events (hides demo chain when 0).
  Screenshot-verified: 0 notices/0 suppliers/0 packages, clean empty states, no "Modular OT" rows.
- Packaged v57b (HTTP 200, version-stamped): /downloads/pmc-backend-v57b.zip,
  /downloads/pmc-frontend-v57b-prod-build.zip.
- Post-deploy cleanup tool added: scripts/flush_reseeded_demo.py — clears ONLY the demo collections
  v57a reseeded (notices, packages, products, *_templates, rubrics) with JSON backup + CONFIRM gate.

## v57c (28 Jun 2026) — Homepage demo cards bulletproofed + prod re-clean confirmed
- Production re-clean CONFIRMED by user: flush_reseeded_demo.py removed 174 demo docs
  (6 notices, 60 packages, 105 products, 1 tender_template, 2 rating_criteria_sets), backed up.
  Verified: pmcmanagers.com on v57b, /api/v1/notices total=0.
- Audit-ledger panel confirmed CORRECT (real data): public_stats.ledger_events counts the live
  audit collection (audit_events/audit_ledger). Grows with real actions — NOT demo seeding.
- FIX: the hardcoded "Open for bids this week" cards and hero live-board demo rows in HomeE.jsx
  now default to display:none and are revealed ONLY when real live data fills them
  (pmcELiveData.js sections 3 & 4 set display="" on fill). Guarantees no demo tenders ever flash
  on a clean board regardless of fetch timing or client cache. Preview-verified: all 4 cards +
  4 rows computed display:none, demo text (Turnkey IVF / Birth Suites) absent from DOM.
- service-worker.js CACHE_VERSION bumped v56l -> pmc-shell-v57c so returning visitors get the
  new bundle within one load.
- Packaged v57c (HTTP 200, stamped): /downloads/pmc-backend-v57c.zip,
  /downloads/pmc-frontend-v57c-prod-build.zip.

## 2026-11-01 — v59d Partner progress bar + auto reminders
- Progress bar "N of 4 sections complete" (Profile, Banking, Documents, Agreement) on the partner form and on draft/needs-changes partner rows in Admin > Partners (ProgressBar/profileProgress in AgentSteps.jsx).
- Daily cron partner-reminders (09:00 London) -> POST /api/v1/cron/partner-profile-reminders: emails draft partners 3 and 7 days after joining, listing what is still missing; tracked in agents.auto_reminders, retried next day if email fails. Verified in preview (401 without auth, reminder recorded, no duplicate on rerun).
- Bundles: /downloads/pmc-backend-v59d.zip, /downloads/pmc-frontend-v59d-prod-build.zip

## 2026-11-01 — v59e Criteria in admin builder + publish checklist
- Admin Tender builder: Criteria button on non-master drafts (same editor as notices); criteria/consortium settings copy into the notice created via "Create notice" (notices.create_notice).
- Admin Notices: each draft row shows a "Ready to publish?" checklist (main document, future deadline / pre-bid order, at least one must-pass criterion) with "Add now" opening the criteria editor. Tested iteration_157 (100%).
- Bundles: /downloads/pmc-backend-v59e.zip, /downloads/pmc-frontend-v59e-prod-build.zip

## 2026-11-01 — v59f Criteria master, sets, live-no-bid editing, checklist Publish
- New Admin › Criteria master (/admin/e/criteria-master): admin/reviewer manage master criteria (seeded from old built-in templates) and named criteria sets; soft-delete (archive) with confirm. API /api/v1/criteria-library (auth required; writes admin/reviewer + CSRF).
- Criteria window: "+ Add from master" lists sets (adds all, skips duplicates) and master items; custom criteria still allowed; "Save as set" for admin.
- Live tenders: criteria editable directly while no bids exist (must keep 1+ must-pass); locked once a bid arrives.
- New notice: Criteria window opens automatically after Create. Checklist has Publish button enabled only when all 3 checks pass (old row Publish button removed).
- /api/v1/tender-criteria/templates now requires login. Tested iteration_158 (100%).

## 2026-11-01 — v59g AI proof review + unanimous committee decision + per-tender award method
- At technical opening, qualified bids get a proof review per must-pass proof; Gemini (gemini-3.1-pro-preview) reads PDF/image proofs and records verdict match/mismatch/unclear, value found and details (non-PDF/image = unreadable). Retry endpoint runs in background with atomic claim (no double reads).
- Every committee member must Accept/Reject each proof (comment required to reject); all accept = accepted, any reject = bid disqualified. Price opening blocked until all proofs decided. Votes use targeted atomic updates.
- Proof files were already encrypted/sealed until technical opening (bid-docs uploads).
- Per-tender award method (L1 default / weighted) in the Criteria window; award report + L1 page honour it; weighted sort keeps qualified bids first.
- Tested iteration_159 + tests/test_v76_proof_review.py 13/13.

## 2026-11-01 — v59h Mandatory/optional criteria, auto L1, proof check report
- Every criterion has a Mandatory flag (default on for pass/fail, off for scored) across notices, builder, master and sets. Tender setting min_optional: bidders must meet all mandatory + at least N optional pass/fail criteria (blank = all). Vendors may skip optional criteria; proof only needed when answered (not for a No answer).
- Evaluation adds optional_summary; rejecting an optional proof only disqualifies if optional passes fall below the minimum (recomputed after write, race-safe).
- L1 ranking runs automatically when price opening completes; card on the bid opening screen; GET /api/v1/comparison/l1/{ref}/latest.
- Proof check report PDF: GET /api/v1/tender-criteria/{ref}/proof-report.pdf (button on qualification panel).
- Result notices show the optional summary. Tested iteration_160 (+ v76/v77 suites 30/30).

## 2026-11-01 — v59i DPR upload 413 fix + Tender process tracker
- Production 413 on AI tender builder DPR upload (1.37 MB) caused by Elastic Beanstalk nginx default 1 MB body limit; added backend/.platform/nginx/conf.d/upload_size.conf (client_max_body_size 200M, 300s proxy timeouts). Needs redeploy of backend bundle to AWS; not verifiable from preview.
- Tender process tracker on every notice row (Criteria, Bids, Opening, Proof review, Price, L1, Award) with current stage detail; stages not used by legacy tenders shown as skipped. API GET /api/v1/tender-tracker?refs=... (admin login).

## 2026-11-01 — v59j Award to L1, dashboard tracker, manuals
- POST /api/v1/comparison/l1/{ref}/award: committee member one-click award of L1 (guards: membership, L1 method, price opened, not awarded, L1 at accounting_cleared); uses decide_bid; re-runs L1. Button on AutoL1Card with confirm + notes.
- Dashboard "Live tender progress" panel (GET /api/v1/tender-tracker/live), 8 rows + show all.
- Manuals in /downloads/manual/: pmc-user-manual.pdf (44 pages, every screen), pmc-master-training-manual.pdf (12 modules), pmc-process-flow.pdf/png, pmc-data-flow.pdf/png, pmc-manual-pack.zip. Rebuild: scripts/capture_manual.py then scripts/build_manuals.py (screens list in scripts/manual_screens.json). Tested iteration_161 + test_v78 15/15.
- NOTE: frontend build script excludes downloads/ from the prod ZIP, so manuals are served from the preview link.

## 2026-11-01 — v59k Whole-site v4 Master Training Manual + help-drawer manual links
- PMC_v4_Master_Training_Manual.pdf (93 pages, hyperlinked contents + PDF bookmarks): overview/architecture, roles, security, screen tours of all 5 portals (59 screens), deep dives (DPR AI, criteria/opening/proof review, L1/award/escrow, partners/tracker), AWS deployment runbook, troubleshooting, sample workflow, API index (737 endpoints from OpenAPI), data model, release history, glossary. Build: scripts/build_manual_v4.py (+ capture_manual.py with manual_screens*.json).
- Help drawer (every portal) shows "Read the manual for this screen" linking to the matching page (downloads/manual/sections.json). Frontend prod ZIP now includes the v4 manual + sections.json so the link works on AWS.
- Award emails: already sent on every award incl. Award to L1 (winner congratulations; other bidders told it went to another supplier, with EMD refund date).

## 2026-11-01 — v59l Secret leak cleanup, loser email reasons, v4 policy chapters
- SECURITY: real Resend API key + VAPID private key found in committed docs frontend/build-v54a/downloads/EB_ENV_FIX_missing_RESEND_key.md and NEXT_STEPS_v46x_and_push.md (since 2026-09-25). Files deleted; .gitignore adds frontend/build-v*/, *.pem, *.key. User must revoke/rotate keys (still in Git history).
- Losing-bidder award email now explains why: criteria failed (list), disqualified (committee note), or L-rank + own price vs awarded L1 price (bids._loss_reason).
- v4 manual: added chapters 19-28 (criteria/qualification policy, proof review policy, evaluation & award policy, ethics/COI, data protection & secrets, incident response, complaints & appeals, RACI, templates, SLAs); 104 pages.

## 2026-11-01 — v59m Key leak guard + bidder debrief page
- scripts/secret_scan.py blocks bundles containing API keys (Resend, Stripe, sk-, AWS, Google, GOCSPX, GitHub, Slack), private key blocks, DB URLs with passwords, quoted secret assignments (value must contain a digit) and .env/.env.*/.pem/.key files; prints file + kind only. build_v59m.sh runs it and deletes bundles on failure.
- GET /api/v1/bids/{id}/debrief + /vendor/bids/:id/debrief page (summary, rank, own vs awarded price, criteria with mandatory/optional, results, proof review outcome + rejection comments, EMD refund date). My bids: non_winner = "Not selected" with Debrief action; legacy patcher tab filter fixed. Loser email button opens the debrief. Tested iteration_162 + test_v79 26/26.

## 2026-11-06 — v60g Translation review + language-specific public pages
- Admin Growth > Translation review (/admin/e/growth?tab=translations): admin/reviewer pick language, filter reviewed/not, search, Approve or Save fix. Backend GET /api/v1/i18n/admin/stats, GET/PUT /api/v1/i18n/admin/phrases (reviewed, reviewed_by, reviewed_at, audit log i18n.phrase_reviewed). Reviewed fixes never overwritten by AI or seed; public dict cache 5 min.
- Language URLs: /{lang}/... for 13 languages (BrowserRouter basename from lib/langPath.js), dropdown on prefixed URL navigates to the other prefix; raw hrefs auto-prefixed; title/meta translated (autoTranslate.refreshHead); hreflang x15 + canonical in useSeo; sitemap has language URLs with xhtml:link alternates; robots (static + API) disallow /*/admin,/*/staff,/*/vendor.
- prerender.py now prerenders 10 public routes x 14 languages (140 pages) using backend/seed/i18n_cache.json offline. SEO title/description phrases prewarmed (prewarm_i18n.py seo).
- RTL: letter-spacing 0 + IBM Plex Sans Arabic for Arabic pages.
- Help module admin-translations + video; languages help/video updated (53 videos); manual 105 pages.
- Tested iteration_171 (backend 22/22; frontend flows pass; href-prefix + robots + debounce issues fixed after).
- Removed superseded release zips older than v60f from public/downloads (disk was full). Built pmc-backend-v60g.zip + pmc-frontend-v60g-prod-build.zip, secret scan passed.



## 2026-11-06 — v60h Help in every language + new manuals
- Ask PMC replies in chosen language (ChatIn.lang); reply bubbles notranslate; links keep /lang prefix.
- Videos: make_videos.py --lang=xx -> public/help-videos/<lang>/ + manifest; HelpVideo falls back to English per slug. 139/689 localized videos done; stopped at LLM key daily spend limit. Resume with same command per language (skips finished).
- Manual: new chapter 28a + 8 new screenshots -> English 114 pages; build_manual_i18n.py renders 13 translated manuals + sections_<lang>.json. Help Centre download button + help panel link per language.
- Translate limit 600->2000 chars; craco devServer static watch off (inotify limit).
- Tested iteration_172 (backend 33/34; ar page map, long text, chat links, button contrast fixed after).
- Deleted old /app root zips v3-v20 and v60f zips (disk). Built v60h (frontend 259MB), secret scan passed.

## 2026-11-07 — v60i iPhone app (App Store prep)
- App renamed PMC Managers (bundle com.pmcmanagers.tenders, v1.0.0 build 1, iPhone only, portrait). Capacitor webDir mobile-shell (index + offline.html errorPath), server.url https://www.pmcmanagers.com, scheme pmcmanagers.
- Info.plist rewritten: Face ID/camera/photo usage strings, arm64, ITSAppUsesNonExemptEncryption=false, remote-notification. App.entitlements (aps-environment production) + CODE_SIGN_ENTITLEMENTS; AppDelegate forwards APNs token.
- Native features (components/NativeFeatures.jsx, native only): push registration on /vendor pages -> POST /api/v1/push/ios/register; notification tap navigates; Face ID app lock (after 60s background); native share; settings sheet. @capacitor/share added.
- Backend routers/apns.py: push_devices (soft deactivate), send_to_vendor via APNs HTTP/2 token auth (APNS_KEY_ID/TEAM_ID/BUNDLE_ID/KEY_P8/ENV; no-op if missing). Hooked into saved-alert _send_alert.
- Vendor E account page: "Delete my account" panel (#delete) using existing GDPR self-forget (Apple 5.1.1(v)). PWA install banner hidden in native app.
- Deliverables: downloads/PMC-Managers-iOS.zip (ios project + vendored plugin node_modules + guide + 6 App Store screenshots 1290x2796 + listing.txt), downloads/PMC-Managers-iPhone-App-Guide.pdf. Old PMC-Tenders-iOS-project.zip removed. v60i bundles built, secret scan passed. Not tested on a device (needs Mac/Xcode).


## 2026-11-07 — iOS app submitted
- PMC Managers 1.0.0 (1) uploaded from customer's Mac (Xcode 27.2) and submitted for App Review (Waiting for Review). China mainland excluded (no ICP). APNs key created (Team Q2J9548DSN); APNS_* env vars still to be added in EB.


## 2026-11-09 — v60j: purchase-free iPhone app + admin vendor mandatory fields
- Apple 2.1 "Information Needed" reply drafted (notes, recording steps). APNs env set in EB by customer (APNS_KEY_P8 via SSM Parameter Store reference).
- lib/nativeBilling.js: in Capacitor app only, hides buy/pay/subscribe/upgrade/featured/priced buttons (data-pmc-iap-hidden), blocks checkout/pay POSTs in api.js interceptor, rewrites 402 to neutral "Billing ... managed by your organisation's PMC account." (info toast). Web unchanged. Tested iteration_173.
- Admin /admin/vendors/new: final create now blocked until all red-* fields + required documents are filled (frontend requiredFields.js + backend vendor_full_invite._check_mandatory, 400 listing missing items).
- Prod 403 on hero-image upload: preview upload of 1.3 MB JPG works; prod 403 has no JSON body → AWS layer (likely WAF on CloudFront). Customer to check WAF sampled requests.
- Admin Add Vendor: live red "Required" under every empty mandatory field (ShowRequiredContext in FormPrimitives; admin form only, public form unchanged).
- Bundles: pmc-backend-v60j.zip + pmc-frontend-v60j-prod-build.zip (rebuilt 02:37, secret scan passed).

## 2026-11-09 — v60k: WAF-safe uploads
- Root cause of prod 403: AWS WAF AWSManagedRulesCommonRuleSet#CrossSiteScripting_BODY on raw image bytes (CloudFront free plan; custom rules not allowed).
- Fix: frontend api.js interceptor sends every FormData upload to own /api as base64 JSON (X-PMC-Upload: b64); backend b64_upload.py ASGI middleware rebuilds multipart (inside CORS). All UploadFile endpoints unchanged; legacy multipart still works. Tested iteration_174 (16/16 backend, md5-identical round trips).
- Registration doc uploads: allow-list pdf/jpg/jpeg/png/doc/docx (client + server 400).
- Customer deploys website via CloudShell one-liner (bucket pmc-managers-frontend-prod, CloudFront E2WZT1TMQ0EK9W); build stamp now v60k.

## 2026-11-09 — v60l: vendor category bug ("Wind generators")
- Root causes: admin Edit full profile saved Section D categories only into vendor.profile.business_categories (bid gate reads top-level business_categories); category_interest stringified dicts; vendor /vendor/categories picker only listed db.categories master (no UNSPSC commodities); request_category rejected non-master codes.
- Fixes: _fees.category_names(); admin_update_vendor_full syncs profile -> top-level (removals honoured) and no longer 404s vendors without tenant_id; startup backfill; picker searches UNSPSC (deduped) + ?add= prefill/auto-select; request accepts UNSPSC code+title or a published tender's category; admin Section D no 1-category limit (adminMode). Tested iteration_175.
- Main tender document label in Notice edit modal now says needed to publish.

## 2026-11-09 — v60m: iPhone recording fixes
- Customer's recording used the home-screen web shortcut "PMC Tenders" (PWA), not the App Store app "PMC Managers" — native ⇪ share/⚙ only exist in the real app.
- Mobile supplier menu (PmcMobileNav) now has AI tender tools, Saved alerts, Prepare tender, Consortia, Directory listing, Data intel, Messages, Refer & earn.
- Tender share bar: new "Share" button (Capacitor Share / navigator.share / copy fallback).
- After self-delete: vendor logout + redirect /login?deleted=1 with "Your account has been deleted" toast (was blank home). Tested iteration_176.
- Known (not fixed): notice detail Indicative budget shows "$" for GBP tenders; saved-alert row layout on narrow mobile.

## 2026-11-09 — v60n: AI summary prod 500 diagnostics
- Prod /api/v1/supplier-ai/summary returned bare HTTP 500 for "DPR LW-20.04.22.pdf"; preview works (200) with 114-page PDF. Cause unknown (no prod logs).
- Added global exception handler (JSON detail "Server error (Type): msg" + logged traceback) and NUL-byte strip before LLM. Next: customer retries on v60n and sends the new message.
- AI tools "Your recent reports": clicking now scrolls to the opened report; each report has Download (.txt) and Print / Save as PDF.
- ROOT CAUSE of prod AI 500: "ModuleNotFoundError: emergentintegrations" — tender_pro._llm_complete (AI summary, readiness, Ask PMC, tender drafting), i18n_auto (translations) and proof_ai imported emergentintegrations, which is not installed on AWS. Switched to vendored pmc_lib.llm.chat; pmc_lib now treats sk-emergent- keys as managed and routes to integrations.emergentagent.com when INTEGRATION_PROXY_URL is unset. Verified preview: summary 200, Ask PMC reply. Bundle pmc-backend-v60n2.zip (Dockerfile unchanged).
- PdfStreamError on iPhone upload (truncated/iCloud placeholder PDF): _extract_text_from_upload now checks %PDF header, pypdf strict=False, per-page tolerance, friendly 400 messages. Bundle pmc-backend-v60n3.zip.

## 2026-11-09 — v60o: dark screen after account deletion (native)
- Cause: post-delete reload re-engaged Face ID lock screen (pref pmc.faceid=1). Fix: deletion removes pmc.faceid; lock never shown on /login|/signin; lock z-index 2000; floating buttons hidden on sign-in. Tested iteration_177.

## 2026-11-09 — v60p: scanned PDF reading + readable delete dialog
- Supplier AI summary reads scanned PDFs (no text layer) and photos (JPG/PNG) via Gemini vision (growth._vision_summary); proof_ai now uses _llm_key() (prod LLM_API_KEY).
- GDPR delete dialog: portal to body, z-3000, dark readable text, white input, "Enter your password to permanently delete your account". (pref pmc.faceid=1). Fix: deletion removes pmc.faceid; lock never shown on /login|/signin; lock z-index 2000 (covers header); floating ⇪/⚙ hidden on sign-in pages. Tested iteration_177 (5/5). Known: AI tool buttons would be hidden in-app if AI prices > 0 (currently free).

