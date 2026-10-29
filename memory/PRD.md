# PMC Managers — PRD (reset: 16 Feb 2026)

> Oversized history relocated. This file now carries ONLY the live product
> requirements + current status. Changelog and backlog live in the sibling
> files.

## Product
PMC Managers is a React + FastAPI + MongoDB procurement/tender SaaS with
reverse auctions, bid governance, EMD escrow workflows, vendor/staff/
institution portals, AWS deployment bundles, and transactional notifications
(Stripe, Resend, DocuSign, Emergent crons).

## R9 — FULL vendor tender builder (IMPLEMENTED + tested, 29 Oct 2026)
Vendors now use the COMPLETE staff Tender Builder (`TenderBuilderPanel` in `vendorMode`)
at `/vendor/tender-builder` (`VendorTenderBuilderFull.jsx`), not the cut-down R8 form.
Status: backend 21/21 pytest green (`backend/tests/test_r9_vendor_tender_builder.py`),
reviewer + vendor UI screenshot-verified in preview. Shipped:
- **Shared access layer** `routers/_tender_access.py`: resolves a staff OR vendor
  principal (admin cookie first, then vendor_token); `write_principal` enforces CSRF for
  staff sessions + entitlement for vendors; `scope_filter`/`assert_can_read_doc`/
  `assert_can_edit_doc` give strict server-side tenant/ownership isolation (a vendor sees
  only their own drafts + APPROVED shared masters; pending/rejected masters hidden &
  blocked from public pdf/zip). The edit guard also LOCKS a tender once submitted/approved
  across EVERY write path (patch, section save, restore, ai-fill, ai-draft, attachment,
  bulk, delete, save-as-master).
- **tender_templates.py / tender_pro.py** endpoints converted from `require_role` to the
  principal model with ownership scoping; DPR analyze/async/jobs, AI Fill-All and section
  AI-draft accept vendors on their OWN draft only. AI uses **Claude Sonnet 5.5 via the
  Emergent LLM key** (`_llm_complete`).
- **Submit-for-review (no vendor publish)**: `POST /tender-templates/{tid}/submit-review`;
  active-reviewer-only queue + approve/request-changes/reject (`require_role("reviewer")`,
  admins get 403). Approve publishes a `notices` doc (origin=vendor, author=vendor company,
  `tender_template_id` linked) and preserves originator → the R8 bid conflict-guard blocks
  the author from bidding. Mandatory fields (title/description/budget) validated before publish.
- **Vendor template → shared library moderation**: `save-as-master` by a vendor stays
  `moderation_status=pending`; reviewer `Pending library` tab approves/rejects
  (`/masters/pending`, `/{tid}/master/{approve,reject}`).
- **Pricing via Fee Master** (`emd_masters`, kind='subscription') per COUNTRY+currency:
  no priced master for the vendor's country → FULL builder FREE for KYC-approved vendors;
  a real price → subscribe gate (Stripe test-mode, `vendor-tenders/subscription*` rewired
  to Fee Master). Entitlement re-checked at operation time; NO cron.
- Frontend: vendor action bar shows "Submit for PMC review" (never "Create notice"),
  entitlement banner (free/active/subscribe), review-status badge + locked controls once
  submitted/approved, unique data-testids. `AdminTenderReviewE` keyed by template id.
Deferred (non-blocking): ai-fill-all async job for very large (18-section) masters;
malformed-ObjectId 500 hardening; `tender_templates.py` module split; vendor brute-force/CORS
(pre-existing, out of R9 scope).

## R9 — original SPEC (superseded by the IMPLEMENTED section above)
User requirement (28 Jun 2026): the vendor tender builder must be the COMPLETE
staff experience, not the cut-down form shipped in R8.
Architecture (discovered — reuse existing, do NOT duplicate):
- **Reuse the real panel** `frontend/src/apps/admin-console/TenderBuilderPanel.jsx`
  (+ `tender/DprGenerateModal, TenderHeaderForm, TenderSidebar, TenderSectionCard`)
  in a NEW vendor-portal wrapper, in a "vendor mode" prop where the final action is
  **Submit for PMC review** (reviewer-only approval, already built in R8), never Publish.
- **Vendor-auth the DPR/AI engine**: `routers/tender_pro.py` endpoints are gated to
  `require_role("admin","reviewer")`. Add a vendor-aware auth path (accept
  `current_vendor`) with STRICT per-draft ownership scoping — a vendor may run DPR
  analyze / AI drafting / section save only on their OWN draft notice.
- **Subscription via the FEES MASTER (already exists)**: the fees master is
  `emd_masters` with `kind="subscription"` (see `tender_pro.py` ~L709-803). Create a
  `tender_builder` subscription entry there; `billing.py` (L332+, `fee_master_id` →
  Stripe checkout, one-off or recurring) already does the checkout. REWIRE
  `vendor_tenders._sub_config()` to read price from that fee-master entry instead of
  the stop-gap `platform_config` doc, and use billing.py's checkout. Full AI builder
  is unlocked ONLY when the vendor's subscription is active.
- **Scope limiting**: a vendor may raise tenders only in their APPROVED categories.
  Extra scope = vendor requests expansion → PMC approval (new approval flow) AND may
  require a higher subscription tier. Enforce approved-category check on create/submit.
- **Masters-driven fields**: delivery-country & currency are dropdowns limited to the
  VENDOR'S OPERATING COUNTRIES (from the vendor's registered countries ∩
  `/meta/countries` + `/masters/currencies`). Apply consistently on admin builder too.
- Keep R8 conflict guard (can't bid on own tender) + author disclosure.
Testing: end-to-end vendor flow (subscribe via fees master → DPR upload → AI draft →
submit → reviewer approve → publish → originating vendor blocked from bidding).
STATUS: fully specced + architecture discovered; implementation pending (large, to be
built + tested in a dedicated pass).

## R8 — Vendor Tender Preparation (28 Jun 2026)
Approved, KYC-verified vendors can prepare tenders with the same fields as staff,
gated by an optional paid subscription; every vendor tender needs MANDATORY PMC
review by the `reviewer` role ONLY before publishing. Backend: `routers/vendor_tenders.py`
(prefix `/api/v1/vendor-tenders`). Frontend: vendor page `/vendor/tender-builder`
(subscription gate + full-parity builder + my-tenders) and admin `/admin/e/tender-review`
(reviewer-only queue: approve→publish / request-changes / reject).
- Subscription price/period come from backend config (`platform_config` doc
  `tender_builder_subscription`; default disabled=free). Stripe reuses the repo's
  Flow-B pattern (`pmc_lib...StripeCheckout`, `STRIPE_API_KEY`), checkout+poll;
  on paid the vendor's `tender_builder_sub` is activated.
- Conflict of interest: a vendor who prepared a tender is blocked (403) from
  bidding on it (guard in `bids.py`). Author disclosed on the tender + ledger.
- Notices public list/detail now emit `bid_count` (distinct active bidders) for a
  public interest counter. NEXT (deferred): render the counter + a live countdown
  timer in the tender cards (public + portal).
- Verified: backend auth-gating via curl (401/403), frontend build + render of
  both pages. Reviewer approve path requires a reviewer-active session.

## R7 — Governance & integrity hardening (28 Jun 2026)
Answered the PMC-portal due-diligence questionnaire against the real code, then
built the governance gaps the user flagged as must-do. Admin console page:
`/admin/e/governance` (AdminGovernanceE, 6 tabs). Backend: `routers/governance_controls.py`
(prefix `/api/v1/governance-controls`). All actions audit-logged; SoD enforced.
- **AI price-leak fixed**: `bids_ai_compare._fetch_bid_scope` no longer sends bid
  price to the LLM (two-cover integrity).
- **Manual-exceptions register**: `manual_exceptions` collection + `record_exception()`
  helper (mirrors to audit ledger); GET /exceptions. Fed by KYC override, fee-waiver
  approval, buyer-type override, integrity senior-override.
- **Buyer public/private classification**: classify (admin/reviewer) → verify by a
  DIFFERENT officer (SoD 403 if same person); verified rows are locked (409 on
  reclassify); history kept.
- **Integrity committee + collusion**: raise/review/resolve with a state machine
  (resolve blocked once overridden/resolved → 409); audited+disclosed senior
  override (admin, reason ≥10 chars, no repeat override); collusion indicators
  endpoint (shared email-domain/phone/address/bank + repeat co-bidding).
- **Fee-waiver maker-checker**: request then approve by a different person (SoD 403);
  approval writes an exception.
- **Per-country legal register**: board-visible; approved_by set only when approved.
- **Incidents + public SLA**: admin logs incidents; `/public/incidents` (no auth)
  returns disclosed incidents + published SLA statement.
Verified: 19/19 pytest (incl. 2 loophole regressions) + testing_agent iteration_118
(frontend 100%). STILL A STUB / NOT REAL: KYC/AML screening — user will supply
Refinitiv World-Check One (LSEG) access to wire a real provider next.
NEXT (user-approved order): real KYC (Refinitiv) → full accounting module →
CRM (supplier + buyer + shared tasks).



## Public placeholder-data cleanup (26 Jun 2026)
Go-live prep: public-facing pages must show real live API data or honest empty/loading/not-found states —
NO fabricated tenders/awards/bids/refs/budgets/countdowns. Transaction-independent marketing copy may remain.
Verified via /app/test_reports/iteration_115.json (empty DB): Home filter-chip ghost-card bug fixed; all
public routes clean. Removed unverified "Big-4 / since 2018 / 11 jurisdictions" footer claim. Optional
remaining polish: mobile mockup empty-state labels, /tenders/all header brand alignment, footer pinning.

## Current deployable: v56u (26 Jun 2026)
Fix release: (1) contract-type/sector dropdowns no longer duplicate — shared uniqByCode() dedupes
by code across board/homepage/notice forms, plus an admin "Remove duplicates" button (TaxonomyTab)
calling POST /api/v1/masters/dedupe-taxonomy to delete duplicate sector/contract_type/category rows
(keeps earliest per code, idempotent, audit-logged). (2) Tender-board Country filter is now a
dropdown from the country master (was a 2-char text box). Verified testing_agent iter 108 (100%).
Artifacts: pmc-backend-v56u.zip, pmc-frontend-v56u-prod-build.zip, DOWNLOAD_v56u.md. USER ACTION
after deploy: Masters → Contract types → "Remove duplicates" once to clean production data.

## Prev deployable: v56t (26 Jun 2026)
Homepage hero search rebuilt on the primary taxonomy (Sector → Contract type → Category +
full country master + keyword; HeroTaxonomySearch.jsx), order-independent, deep-links to
/tenders/all. Country↔currency master: each country has an editable accepted_currencies[]
with a primary default (Masters → Country currencies); notice/bid/EMD currency pickers
default-load the country's primary while allowing any active currency (CurrencySelect.jsx,
wired into notice create/edit). Fixed hero-form hijack in PmcLinkPatcher.jsx. Artifacts:
pmc-backend-v56t.zip, pmc-frontend-v56t-prod-build.zip, DOWNLOAD_v56t.md. Preview-verified
(testing_agent iter 106 + 107, 100%). DONE: admin "Taxonomy backfill" (Admin → Taxonomy
backfill) auto-guesses + bulk-saves Sector/Contract codes onto legacy notices so public
filters return rows; bids/EMD already lock to the tender currency; v56t Word/Excel pack
regenerated with a "New capabilities" section.

## Prev deployable: v56r (24 Jun 2026)
Notice pickers: cascading Sector + Contract type selectors on Create-Notice (NoticesPanel)
and Edit-Notice (NoticeEditModal) forms, saved as sector_code/contract_type_code on the
tender (backend extra="allow"; verified end-to-end — created notice returns both). Builds on
v56q masters + v56o fixes. Artifacts: pmc-backend-v56r.zip, pmc-frontend-v56r-prod-build.zip,
DOWNLOAD_v56r.md. STILL TO WIRE: vendor tagging (registration/profile), public board filter
by sector/contract, go-live mandatory switch.
Adds Sector/Contract-Type taxonomy above UNSPSC + all v56o bug fixes.
Backend: db.sectors (25) + db.contract_types (30) own collections, seeded idempotently on
boot; full admin CRUD + `/api/v1/masters/{sectors,contract-types}[/public]`. Earlier v56p
flat-in-categories attempt auto-cleaned (categories back to 105 UNSPSC). Admin UI: Masters →
Sectors / Contract types tabs. Artifacts: pmc-backend-v56q.zip, pmc-frontend-v56q-prod-build.zip,
DOWNLOAD_v56q.md. STILL TO WIRE: cascading Sector→ContractType pickers on notice-create &
vendor registration/profile (optional now, mandatory at go-live) + public board filters.
Bug-sheet batch 1 (6 fixes) + customer contract/works taxonomy.
Artifacts (preview): `pmc-backend-v56p.zip`, `pmc-frontend-v56p-prod-build.zip`,
`DOWNLOAD_v56p.md` under `/downloads/`. Deploy: EB backend → S3 frontend root →
CloudFront invalidate `/*` → confirm footer "Frontend v56p · Backend v56p".
Backend auto-seeds the 26-item EPC/Works/PPP/Renewable/Power/Logistics taxonomy on boot.
Fixed+preview-tested: #58 catalog disable, #44 eval default rubric, #17 docusign vendor
envelopes, #23 corrigenda validate-before-write, #36 closed-tender Start bid, #72 escrow
magic-link message. STILL OPEN: #55 registration approve, #40 notice timelines,
#56 AI FILL ALL (502 large), #23b public corrigenda tab.
Public-site upgrades on top of v56m: live ledger Verify (recompute hash → intact/break),
tender deep-links (live rows + cards open the notice), real Contact enquiry with tracked
reference (ENQ-2026-#####) emailed to desk, status-filter links (Closing this week /
Awarded), and "Sign in" now opens the Option-E `/login` chooser (not legacy navy page).
Artifacts (preview): `pmc-backend-v56n.zip`, `pmc-frontend-v56n-prod-build.zip`,
`DOWNLOAD_v56n.md` under `/downloads/`. Deploy: EB backend → S3 frontend root →
CloudFront invalidate `/*` → confirm footer "Frontend v56n · Backend v56n".
Agent-tested in preview (iteration_98: backend 100%, frontend 88% → card deep-link
fixed after). NOT yet user-confirmed in production.

## EMD → Escrow flow (validated on preview, 18 Jun 2026)
Lifecycle: bid `emd_paid`→`escrow_accepted` (auto) → admin records EMD receipt
(`POST /api/v1/escrow/transactions/init`) against a joint account with DISTINCT
officers → tx at `received` → dual sign (in-app / magic-link / DocuSign) →
`Release`. DocuSign hand-off = `POST /api/v1/escrow/transactions/{tid}/docusign`
(503 if DocuSign not configured; magic-link email is the fallback). Preview E2E
confirmed: EMD USD 500,000 recorded, tx `received`, governance_ok, both officers
distinct, ready for signature hand-off.

## v56g (18 Jun 2026) — staff portal sidebar + readable + embedded DocuSign
- Staff dashboard rewritten with a left SIDEBAR + inline-colour palette (fixes
  the unreadable/faint text caused by the global `[data-ui="e"]` dark theme
  repainting `bg-slate-*`/`text-slate-*`).
- DocuSign signing is now EMBEDDED (recipient view): signers carry
  `client_user_id`; "Open in DocuSign" mints `create_recipient_view` with a
  `return_url` back to the portal (/staff, /escrow/me, /admin) so the PMC
  officer actually SIGNS and is returned to their dashboard — not the DocuSign
  email login. Legacy email-mode envelopes auto-convert via `update_recipients`.
- Signed PDF emailed to both officers + the issuing admin on completion.
- NOTE: embedded signing verified only structurally in preview (DocuSign JWT
  not configured there → 424 handled gracefully); REQUIRES production validation.

## v56f (18 Jun 2026) — PMC-officer signing surface + signed-PDF delivery
- Staff portal (`StaffDashboard.jsx`) now shows an **"Escrow documents — your
  signature"** section for the logged-in PMC officer: lists every escrow
  transaction where `escrow_account_snapshot.pmc_officer.email` == their email,
  with pending items highlighted. Actions per row: **Open in DocuSign to sign**
  (Safari-safe sync-open), **Refresh DocuSign**, **Download signed PDF**.
- New staff endpoints (`staff_auth.py`, scoped to the officer's own email →
  403 otherwise): `GET /api/v1/staff/escrow/signatures`,
  `GET /escrow/transactions/{tid}`, `GET …/docusign-url`,
  `POST …/docusign/refresh`, `GET …/signed-document`.
- On DocuSign completion, `_deliver_escrow_signed_document()` (docusign.py,
  called from `_apply_live_status` escrow_tx branch) downloads the COMBINED
  signed PDF, stores it on the transaction (`signed_document`) and EMAILS it as
  an attachment to BOTH officers (incl. the escrow institution officer, e.g.
  Sakina) — so the executed document actually reaches their inbox, not just a
  status flag. Idempotent + best-effort.
- Readability fix: staff dashboard forced to a solid light background (#eef2f7)
  with dark text; contrast strengthened on refs, chips and secondary buttons.
- Verified (iteration_93): backend 100% (listing + 403 scoping + signed-doc),
  frontend 100% (section renders, all data-testids, graceful toasts, PDF
  downloads). Still PREVIEW-only — not yet deployed/confirmed in production.

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

## Status note — v56s (25 Jun 2026): taxonomy + Go-Live batch complete (preview)
- Shipped & preview-tested (pending prod deploy + user sign-off): procurement taxonomy
  (Sector/Contract Type/UNSPSC) across vendor registration, vendor category requests, notice
  create/edit and the public tender board; admin Go-Live switch (OFF default, server-side
  enforcement when ON); public board filters + shareable deep-links; escrow incomplete-reg
  reminders + 30-day dormancy (#13); Events HTML-tag render fix (#71).
- Verified (no code change): #6 required marker (bold red REQUIRED pill), #15 stale
  registration selection cleared on tab switch.
- Deferred by user: #11, #69 help-text wording.
- Backend `test_v56s_golive_taxonomy.py` 14/14 green; earlier full regression iter 102/103 green.
- Deliverables for the client team generated + rendered-verified: `PMC_Bug_Clearance_v56s_*`
  (.docx + .xlsx) in `/app/deliverables` and `/app/frontend/public/downloads`.
- OPEN: production `contract_types` duplicate remediation — plan only
  (`memory/PROD_CONTRACT_TYPES_DEDUP_PLAN.md`), needs user authorization; production deploy of
  v56s pair + CloudFront invalidation.

## Status note — v56w (27 Jun 2026): responsive remediation batch complete (preview)
- Staff (/staff) and Escrow (/escrow/me) portals migrated to the shared Admin-E shell:
  desktop sidebar, mobile off-canvas drawer + working tap-to-close scrim, unified header,
  exactly one hamburger. Mobile title/breadcrumb context added and tab-reactive.
- Escrow transaction mobile cards now labeled (Bid, Notice, Amount, Status, Signatures),
  no blank cells; empty Notice shows "—"; Signatures reads "PMC pending · Us pending".
- SignInE collapses to a single clean column at 820px; /privacy first legal sub-nav pill
  no longer clipped under the fixed mobile topbar.
- Verified: testing_agent iteration 113 confirmed all 6 iteration-112 responsive defects +
  both polish items fixed (~98%); the two residual LOW cosmetic items fixed + screenshot-verified.
- Bundles: `pmc-backend-v56w.zip`, `pmc-frontend-v56w-prod-build.zip` + `DOWNLOAD_v56w.md`.
  Footer stamp v56w / 2026-06-27. Preview-verified; awaiting prod deploy + user confirmation.

## Status note — v56x (27 Jun 2026): Supplier portal mobile-nav parity (preview)
- Supplier portal mobile navigation unified to the shared single-hamburger off-canvas drawer
  pattern (bottom tab bar removed), matching Staff/Escrow/Admin. Desktop was already consistent.
- Vendor home Quick links given meaningful per-link icons (were all generic sparkles).
- Screenshot-verified in preview; NOT yet packaged into a build artifact or deployed.
- NOTE: All four portals (Admin, Staff, Escrow, Supplier) now share the same mobile nav model.

## Status note — v57e (26 Oct 2026): PUBLIC reverse-auction system (preview, agent-verified)
Extended the existing reverse-auction module with a full PUBLIC discovery + live
spectator experience. NOT a separate subsystem; built on existing routes/data/UI.
Shipped & agent-tested (testing_agent iteration_116: backend 19/19 pytest green,
frontend flows pass; NOT yet user-confirmed):
- **Public discovery**: `GET /api/v1/reverse-auctions/public/list?status=live|upcoming|closed|awarded`
  returns anonymised cards. Landing band + full `/auctions` page
  (`LiveAuctionsBand.jsx`) with honest empty state when no live auctions.
- **Anonymous spectator room** `/auctions/:aid/live` (`PublicAuctionRoom.jsx`):
  masked bid ladder (Bidder A/B/C), descending price chart, SHA-256 hash-chained
  audit timeline, anonymous viewer count, live countdown. Transport = SSE
  (`GET …/{aid}/stream`) with polling fallback to the public `GET …/{aid}/state`;
  stops on close, retries SSE once before polling.
- **Atomic duplicate-price protection**: Mongo unique index
  `ra_bid_auction_price_unique` on `reverse_auction_bids(auction_id, price)` —
  simultaneous equal-price bids → exactly one 200, other 409. Losing bidder gets
  in-app notification + email (`_notify_duplicate_price`).
- **HIGH race fix (v57e)**: `_place_bid_inner` leader update is now a CONDITIONAL
  atomic `update_one` guarded on `current_price >= price + decrement`; on no-match
  the reserved bid row is rolled back and the bidder gets a 409 "outbid" — prevents
  a concurrent HIGHER bid from overwriting a lower leader (verified 12 rounds).
- **Governance-gated award**: public `_public_winner` reveals the winning COMPANY
  only once the awarded bid reaches `status=awarded` (award_status
  `in_approvals` → `awarded_published`); winner=null before that. NO identity leak
  (vendor_id/email/company) in list/state/events/SSE — confirmed by recursive scan.
- **Hardening**: non-ObjectId public ids → 404 (was 500); heartbeat verifies the
  auction exists + stores datetime `last_seen` with a 120s TTL index on
  `reverse_auction_viewers`; unique `(auction_id, seq)` index on
  `reverse_auction_events` to detect hash-chain forks.
- Cron remains DISABLED (user decision) — manual close only; no timers/schedulers added.
- All TEST seed data cleaned up; public board back to honest empty state.
- **DONE (2026-06): public `/auctions` header+footer aligned** with the public-site
  chrome via new `frontend/src/apps/shared/PublicChrome.jsx` (brand, nav with active
  Auctions link, Sign in/Register, dark footer). Replaces the old generic TopBar on
  both the discovery page (`LiveAuctionsBand` page variant) and the spectator room
  (`PublicAuctionRoom`, incl. error/loading states). Flex-column layout keeps the
  footer at the bottom on short pages. testing_agent iteration_117 = 100% pass.
- **DONE (2026-06): homepage live-auctions band** — `LiveAuctionsBand` (band
  variant) renders right under the hero on `HomeE`, showing live/upcoming auction
  cards with LIVE badge, countdown, current lowest price, floor and a "Watch live"
  link, plus a "See all auctions" CTA. It now **hides entirely when there are no
  live/upcoming auctions** (and during load) so the homepage stays clean. Verified
  by seeding a temporary DEMO live auction (shown at top), screenshotting, then
  deleting it — board back to 0 auctions / honest empty state.
- OPEN / optional: (none — see v57f additions below)

### v57f — auction engagement polish (2026-06)
- **Faster dup-price reject**: `place_bid` now fires `_notify_duplicate_price`
  via `asyncio.create_task` (fire-and-forget) so the 409 returns immediately and a
  slow mail provider can't delay it. (`backend/routers/auction_live.py`)
- **Watcher share link**: public spectator room has a "Copy watch link" button
  (testid `spectator-copy-link`) that copies the room URL and flashes "✓ Link
  copied". (`frontend/src/apps/shared/PublicAuctionRoom.jsx`)
- **Closed auction recap**: `_public_card` now returns `ledger_ref` (short head
  hash of the SHA-256 event chain) for closed auctions; the `/auctions` closed
  card renders an "Auction recap" panel with final price, saving % and ledger ref
  (testids `public-auction-recap/final/saving/ledger-<id>`).
  (`backend/routers/auction_live.py`, `frontend/.../LiveAuctionsBand.jsx`)
- **Hero live ticker**: `HomeE` hero shows a "N auction(s) live now" pill (testid
  `hero-live-auction-pill`) that smooth-scrolls to the live-auctions band, only
  when at least one auction is live. (`frontend/.../HomeE.jsx`)
- All verified in preview with temporary DEMO auctions, then fully cleaned up.
  NOTE: the dup-price timing change is logic-verified (409 still raised identically);
  it was not re-load-tested for concurrency.
