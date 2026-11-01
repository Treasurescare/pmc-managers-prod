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

## R9b — 2026-10-29 (agent-tested, preview only)
- **DPR "1 DPR(s) failed" fix**: root cause = DPRs <4 MB went through the synchronous
  `/dpr/analyze-json`; real DPRs take >60s (30-page PDF = 53s) and hit the gateway timeout.
  `DprGenerateModal` now always uses `/dpr/analyze-async` + polling, tolerates transient
  poll errors, shows phase in errors, marks a failed row immediately. Scanned/image-only PDFs
  return a clear message.
- **AI Fill All background job**: `POST /tender-pro/templates/{tid}/ai-fill-all-async`,
  `GET /tender-pro/ai-fill-jobs/{id}` (collection `ai_fill_jobs`); sections saved one by one;
  stale (>5 min) jobs auto-failed; progress bar `tb-fill-progress`; editing + autosave locked while running.
- **Reviewer inline preview**: `TenderPreviewModal` (DOMPurify-sanitised) with approve/changes/reject.
- **Vendor scope rules** (`platform_config.vendor_scope_rules`, defaults: approved categories only,
  max 3 tenders awaiting review, max 5 pending category requests; 0 = no limit). Enforced on
  submit-review (also requires title/description/budget) and category requests. Editable on the
  review page (`ScopeRulesCard`); vendor sees `VendorScopeStrip`.
- **Stripe paid unlock**: verified end-to-end in test mode with a temporary KZ subscription Fee
  Master (removed afterwards). Webhook now also activates `tender_builder_sub`; checkout status
  endpoint checks ownership. No real per-country prices configured — awaiting user's price list.
- Library lists hide pending/rejected masters.
- Tests: `tests/test_r9_vendor_tender_builder.py` 21/21, `tests/test_r9b_scope_fillall_dpr_sub.py` 14/14 (run with `-n 0`).
- Open (pre-existing, not changed): vendor login has no brute-force lockout; CORS_ORIGINS='*'.

## R10 — Fee Type master + per-tender fees — 2026-10-29 (agent-tested, preview only)
- New `fee_types` collection + `/api/v1/fee-types` CRUD (router `fee_types.py`, seeded on startup, attributes only, no prices):
  timing upfront|on_completion, calc fixed|percentage|either, amount_mode single|range, category_scope all|selected,
  billing one_time|yearly, used_in_tender_builder. Seeded: subscription, premium_subscription, registration, emd,
  tender_fee, tender_management (Tender Builder, at end, selected categories), transaction, data_intel.
- Masters tabs: "Fee types" (FeeTypesPanel) + "Fee rules" (was EMD rules). Rule form adapts to the chosen type;
  multi-category checkbox picker (CategoryPicker). Rules store `categories[]`; server validates against type (`_fees.py`).
- Vendor Tender Builder: TenderFeesPanel shows per-tender fees (non-yearly, tender-builder types) for vendor country +
  category, amount from tender value; Pay now → Stripe → back with `?fee_session=&tid=` (auto-opens tender).
  Upfront unpaid → 402 on AI/DPR-with-template/section edits/PDF; any unpaid → 402 on submit. Raised value → difference due.
  Webhook credits fee payments (idempotent `credited`). Yearly access still via kind=subscription.
- Tests: tests/test_r10_fee_types.py 33/33; R9 21/21; R9b 14/14 (run -n 0, one file at a time).
- No real prices entered — user to add Fee rules per country.

## R11 — Start-fee gate + fee receipts — 2026-10-29 (agent-tested, preview only)
- If any active upfront Tender-Builder fee rule exists for the vendor's country, clicking "AI Generate from DPR" or
  "Clone as draft" first opens StartTenderGate (approved category + estimated value → quote → Stripe). Payment creates a
  `tender_credits` record; creating a draft consumes one credit (category/value/fees_paid copied onto the draft);
  DPR analysis without a draft needs a paid credit (max 3 DPR runs per credit); one unused credit at a time;
  vendor DPR batch limited to 1 file when a start fee applies. Staff never gated.
- Receipts: `fee_receipts` (PMC-RCPT-xxxxxx), created once per Stripe session for start fees and per-tender fees,
  emailed via existing Resend `send_email`, listed on /vendor/emd (VendorFeeReceipts). GET /vendor-tenders/receipts.
- Removed the two Reengus DPR templates at user's request.
- Tests: test_r11_start_gate_receipts.py 27/27, test_r10 33/33, r9 21/21, r9b 14/14 (-n 0, one file at a time).
- Known pre-existing: /vendor/emd stat cards + header chip are hard-coded mock data (not the logged-in vendor).

## R12 — Real EMD & payments page — 2026-10-29 (agent-tested, preview only)
- VendorEmdE.jsx rewritten: VendorPortalChrome (real vendor), KPIs from bidApi.mine() (Due now / Held in escrow /
  Refunds in progress, totals per currency, no conversion), live deposits table with status/currency filters,
  Pay EMD / Receipt (PDF) / Statement (PDF) via PmcLinkPatcher, tender fee receipts section. Mock markup removed.
- Fee-type wiring (for reference): code `subscription` = yearly builder access; any type with
  used_in_tender_builder + one_time = per-tender builder fee (upfront → start gate, on_completion → before submit);
  `emd` = notice EMD picker + DPR auto-EMD; other codes only usable via Masters → Charge Fee (manual) today.

## R13 — Paid additional categories — 2026-10-29 (agent-tested, preview only)
- Registration: only ONE business category allowed (Section D error toast + 400 on submit).
- Additional categories: price from the 'registration' Fee rule for the vendor's country (category-specific wins);
  first category free; no rule → free. Request stores fee_amount/fee_currency/payment_status (unpaid|not_required|paid).
- Vendor /vendor/categories: fee quote before submit, Pay now (Stripe) on pending rows, ?cat_session= return, receipt
  (fee_receipts purpose category_fee) emailed.
- Admin Vendor requests: payment badge, Approve blocked (UI + 409) while unpaid, "Payment pending — send back" →
  status payment_pending + email with prefilled Stripe link (24h) + portal link; new payment_pending tab; reject
  allowed on payment_pending. Stale/duplicate payments never reopen a request — tx flagged needs_refund instead.
- Tests: test_r12_category_fees.py 14/14; r9b 14/14; r11 27/27.

## R14 — Full payments wiring — 2026-10-29 (agent-tested, preview only)
- Fixed: category approve 500 when vendor.business_categories null (vendor updated first via $setUnion pipeline).
- Fee types: country_scope all|selected + countries; rules may use country "ALL"; `find_rule` (country beats ALL,
  category beats all-categories) used by subscription, extra category, builder fees, doc fee, hosting, data intel.
- New fee types: tender_hosting (builder, at end), tender_document_download.
- Charge Fee: lists fee types/rules, payer email mandatory, link emailed (`emailed_to`).
- EMD collector on notices (pmc|escrow|escrow_institution|tender_caller|authorised_party; default tender_caller);
  PMC Stripe EMD checkout 409 for non-PMC collectors; vendor sees pay-direct instructions.
  NOTE: legacy notices without emd_collector now default to tender_caller (PMC checkout blocked) — confirm with user.
- Category upsell: bid on non-registered category → 403 category_not_registered; notice page banner + notification
  + db.messages + email (deduped). db.messages has no UI reader yet.
- Doc download fee (once per tender): gates /notices/{ref}/pack, /uploads/public-files (notice docs), template public
  zip/pdf with notice_ref; Pay & unlock on notice page; receipts.
- Hosting fee for admin notices: "Hosting fee" button emails buyer link; publish (POST and PATCH) blocked while unpaid;
  auto-publish on payment; public /pay/complete page.
- Data intel service: vendor /vendor/data-intel requests (market insights / vendor report); admin Masters → Data intel
  quote (prefilled from data_intel rule) → pay link → deliver.
- Refund alerts + one-click Stripe refund on /admin/e/billing (needs_refund transactions).
- Cron `category-pay-remind` daily 09:00 UTC → /api/v1/cron/category-payment-reminders (WEBHOOK_CRON_SECRET).
- Tests: test_r13_payments_extra.py 17/17; r10/r11/r12 pass.

## R15 — Vendor Messages inbox — 2026-10-29 (agent-tested via curl + screenshot, preview only)
- /vendor/messages (VendorMessages.jsx, nav "Messages"): list, filters (all/unread/category/payment/service),
  expand + DOMPurify body, mark read / mark all read, deep-link "Open".
- API: GET /api/v1/vendor/messages, POST /api/v1/vendor/messages/{id}/read, POST /read-all (own vendor_ref only).
- Messages written by `post_vendor_message` for: category upsell, extra-category fee needed, payment-pending
  send-back, 3-day reminders, category approved, payment received (every fee receipt), data intel quote/delivery.


## R16 — RFQ/RFP starters + Messages unread badge — 2026-10-29 (agent-tested, preview only)
- Seeded masters (always, idempotent, `_seed_extra_masters` on startup): "Standard Request for Quotation (RFQ)"
  (8 sections) and "Standard Request for Proposal (RFP)" (10 sections). TenderTemplateIn.kind is Literal tender|rfp|rfq.
- AI drafting is kind-aware (`kind_style`/`kind_label` in tender_pro.py): section draft, Fill All (sync + background),
  DPR analysis. RFQ = short, price/spec focused; RFP = outcome, methodology, weighted evaluation.
- Cloning a master keeps the master's kind.
- GET /api/v1/vendor/messages/unread-count; supplier nav "Messages" badge (hot), hidden at 0, updates live on read.
- Tests: tests/test_r14_rfq_rfp_unread.py 12/12 (run with `-n 0`; parallel workers break its shared state).
- Backlog: RFQ/RFP drafts still show the full tender "Basic Details" grid (3 covers, Open Tender) — kind-specific header defaults.

## R17 — Fee rules auto-fill + multi-country rules — 2026-10-29 (agent-tested, preview)
- Fee types have a `categories` list (picker when Categories = Selected; cleared when scope = all).
- Fee rules: `countries[]` (one rule covers all ticked countries; stored country = code | MULTI | ALL);
  picking a fee type pre-ticks its countries/categories; ticking extra ones shows "(new)" and, with
  `extend_type`, adds them to the fee type only after the rule saves successfully. find_rule/country_q match `countries`.
- Category-addition fee = Registration fee type rule (first category free).
- Tests: tests/test_r15_fee_rule_scope.py 13/13, r12 14/14 (run -n 0).

## Current deployable: v57i (2026-10-29)
Artifacts in /frontend/public/downloads: pmc-backend-v57i.zip, pmc-frontend-v57i-prod-build.zip, DOWNLOAD_v57i.md
(build script scripts/build_v57i.sh). AWS needs an EventBridge daily POST to /api/v1/cron/category-payment-reminders.



## Stripe go-live status — 2026-10-29 (AWS prod, current deploy v57k)
- DONE: live restricted key rk_live_…9pBE in SSM /pmc/prod/STRIPE_API_KEY; STRIPE_TAX_MODE=diy in SSM;
  live webhook "PMC production webhook" → https://www.pmcmanagers.com/api/webhook/stripe (4 checkout.session.* events).
  Charge Fee now produces cs_live_ links (confirmed by user screenshot).
- v57j/v57k fixes: Quick calculator computeEmd; Charge Fee awaits send_email, returns email_sent, shows link box.
- PENDING (resume here): user to pay USD 1 test link → check Stripe Event deliveries = 200 → Admin Billing paid → refund.
- DONE (user confirmed): prod emails now sending properly.
- PENDING: confirm STRIPE_WEBHOOK_SECRET in SSM matches live destination secret; create /pmc/prod/WEBHOOK_CRON_SECRET;
  EventBridge daily POST /api/v1/cron/category-payment-reminders (Authorization: Bearer <secret>).
- Security advice given: rotate secrets exposed in EB screenshot (Mongo, JWT, admin/owner passwords, Resend, Zoom, DocuSign); DocuSign still sandbox.



## R18 — Marketing module — 2026-10-30 (agent-tested 17/17 backend + frontend, preview) — build v58a
- backend/routers/marketing.py (/api/v1/marketing): contacts (manual, CSV import w/ lawful-basis confirm, platform sync,
  delete), segments (audience/countries/categories/sources; size = consent & not unsubscribed), AI copy (Claude Sonnet 5.5),
  campaigns (draft/test/send in background, per-contact unsubscribe link, open pixel, click redirect, stats),
  public unsubscribe page, new-tender alerts (toggle, OFF by default; hooked on publish, vendor-tender approve,
  template approve, hosting-fee paid; once per notice via unique index), referrals (vendor code, /register?ref=CODE).
- Frontend: /admin/e/marketing (side nav "Marketing"), /vendor/refer ("Refer & earn"), RegistrationStart stores ref.
- Data stance: we do not supply/scrape personal email lists; user imports own/lawful lists (CSV template provided).
- Backlog: notices created already-published don't trigger alerts; contact soft-delete not implemented (hard delete on admin action).

## R19 — Website sign-up + weekly digest — 2026-10-30 (agent-tested 15/15 + 17/17, preview) — build v58b
- Homepage "Get tender alerts" box (TenderAlertsSignup.jsx) → POST /api/v1/marketing/subscribe (public, honeypot,
  5/hour per real IP, TTL hits) → double opt-in email → GET /api/v1/marketing/confirm/{token} sets consent.
- Alerts mode instant|weekly; run_weekly_digest (marketing_public.py) — last 7 days, max 15 per email, active vendors +
  consented vendor contacts; cron marketing-digest Mon 08:00 London (.emergent/crons.yml) → POST /api/v1/cron/marketing-weekly-digest.
  AWS needs EventBridge for it. Admin "Send this week's digest now" (forced, labelled manual).

## R20 — Share cards, buyer invites, Google sign-in — 2026-10-30 (agent-tested 19/19, preview) — build v58c
- marketing_share.py: GET /api/v1/share/notice/{ref}.png (Pillow, bundled fonts backend/assets/fonts) + /share/notice/{ref}
  (OG tags + redirect); NoticeShareBar on notice page. Buyer invites /api/v1/marketing/buyer-invites (sent→clicked→joined).
- google_auth.py: POST /api/v1/auth/google/exchange (Emergent-managed Google; existing vendor/admin_users only; MFA refused;
  high-risk-MFA gate); frontend /auth/google/:portal callback, "Continue with Google" on /login.
- Pending: confirm Emergent Google sign-in works on AWS www.pmcmanagers.com; if not, own Google OAuth client (+ LinkedIn) needed.

## R21 — AI assistant, LinkedIn posts queue + LinkedIn sign-in — 2026-10-30 (agent-tested 18/18, preview) — build v58d
- assistant.py: POST /api/v1/assistant/chat (session_id, multi-turn, Claude Sonnet 5.5; vendor context via vendor_token;
  40/hour per IP; vendor session can't be reused anonymously → 409). ChatWidget ("Ask PMC") global, hidden on admin/staff/escrow/auth.
- linkedin.py: sign-in /api/v1/auth/linkedin/start|callback (OIDC, existing accounts via _social_signin.sign_in_existing);
  page posting: connect (w_organization_social) stores token in mkt_settings.linkedin; mkt_social_posts queue created on publish
  (via send_tender_alert); approve → Posts API (LinkedIn-Version env, default 202610). Needs env LINKEDIN_CLIENT_ID/SECRET/ORG_ID.
- WhatsApp: not built — user chose Meta WhatsApp Cloud API; waiting for Meta Business + app credentials.

- Buyers have no separate login; they sign in via staff/admin accounts.

- Note: tests/test_marketing_v59_signup_digest.py rate-limit tests used fake X-Forwarded-For; after the real-IP fix they hit 429 when run back to back (test assumption, not a bug).


## R22 — Brand logo + social kit — 2026-10-30 — build v58e (screenshot-verified, preview)
- New logo (forest green + gold PMC monogram with checkmark). Downloads: /downloads/pmc-logo-pack.zip, /downloads/pmc-social-kit.zip
  (LinkedIn page cover 1128x191, personal cover 1584x396, Facebook cover 1640x624, WhatsApp 640, LinkedIn page logo 400).
- Site: .pmc-brand::before + mobile .pmc-mob-brand::before show src/pmc-logo-mark.png beside every wordmark; favicon/PWA public/pmc-logo.png replaced.
- Emails: emails._wrap header shows {FRONTEND_URL}/pmc-logo-mark.png (FRONTEND_URL must be https://www.pmcmanagers.com in prod).
- Share cards: marketing_share._render_card pastes backend/assets/pmc-logo-mark.png top-right.

## R23 — Footer social links, branded PDFs, launch posts — 2026-10-30 — build v58f (self-checked: screenshot + rendered PDFs)
- components/PmcSocialLinks.jsx (LinkedIn + Facebook icons, URLs exactly as user gave) added to footers of all 10 notice-board-e pages.
  LinkedIn URL given is a single post (feed/update/...), not a profile — swap when user sends profile/page URL.
- backend/pdf_brand.py: brand_html() inserts logo header after <body> (weasyprint) + logo_flowable() (reportlab).
  Applied to: tender/RFQ/RFP PDFs (tender_templates), award letters (awards), BOQs, EMD receipt + statement (payments),
  bid acknowledgement (docusign), corrigendum PDF, escrow statement (escrow_v52f), escrow EMD receipt (escrow_payment_entries).
  Fee receipts are email-only (logo via emails._wrap). Internal reports/flowcharts not branded.
- downloads/pmc-launch-posts.md: 3 LinkedIn/Facebook launch posts.


## R24 — Admin-editable footer links + branded fee receipt PDFs — 2026-10-30 — build v58g (agent-tested iteration_132: 19/19 backend + UI)
- routers/site_settings.py: GET /api/v1/site/social (public, defaults = user's URLs), PUT /api/v1/marketing/site-social (admin+CSRF, https only, empty hides).
  Admin UI: Marketing → "Website links" tab (WebsiteLinksTab.jsx). Footer PmcSocialLinks reads API.
- Fee receipt PDF: render_receipt_pdf (logo, PAID, lines, total); GET /api/v1/vendor-tenders/receipts/{no}.pdf (own only);
  PDF button in vendor /vendor/emd receipts table; issue_receipt (_fees.py) now attaches the PDF to the receipt email.


## R25 — WhatsApp Cloud API wiring + Instagram/WhatsApp footer links — 2026-10-30 — build v58h (agent-tested iteration_133: 26/26 + 19/19, UI)
- site_settings: instagram (https URL) + whatsapp (digits) keys; footer WhatsApp → https://wa.me/<digits>.
- routers/whatsapp.py (env: WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, WA_APP_SECRET, WA_VERIFY_TOKEN, optional WA_GRAPH_VERSION default v24.0, WA_WABA_ID).
  Webhook GET/POST /api/v1/whatsapp/webhook (verify token + X-Hub-Signature-256), inbound → wa_threads/wa_messages (unique partial wamid index),
  STOP → vendor opt-out, AI auto-reply via assistant (session wa:<id>, 20/h). Templates: pmc_new_tender(4 vars), pmc_payment_reminder(3),
  pmc_payment_receipt(DOCUMENT header + 3) ; hooks in send_tender_alert, category reminders cron, issue_receipt (7-day public token PDF link).
  Admin: Marketing → WhatsApp tab (status, toggles, test hello_world, inbox + 24h-window reply). Vendor opt-in card on /vendor/messages (CSRF).

## R26 — Sealed bids: encryption + committee-only opening — 2026-10-31 — build v58j (agent-tested iteration_134 29/29, iteration_135 43/43 + UI)
- Audit finding: staff (admin/reviewer/accounting/committee etc.) could see technical+commercial docs and price any time; one person could "open". Fixed.
- backend/bid_seal.py: Fernet key derived from env BID_SEAL_KEY (20+ chars; MUST be in AWS SSM /pmc/prod/BID_SEAL_KEY; losing it = sealed bids unreadable).
  New bids (seal_v=1, non-auction): price_amount/technical_notes/commercial_notes encrypted in `sealed`; bid-docs/ uploads encrypted (uploads.sealed, owner_vendor_id).
  Vendor sees own plaintext; staff see name/time/status/EMD only (envelope_state sealed|technical_open|commercial_open). bid.viewed audited.
- routers/bid_opening.py: GET /api/v1/bid-opening/{ref}; POST .../approve {stage}. ALL committee members (chair+member_ids of open committee) must approve,
  after submission deadline and bid_opening_date. Technical opening unseals only EMD-confirmed bids (status escrow_accepted+). Commercial requires
  technical opened + every tech-unsealed bid cleared/rejected + ≥1 cleared; unseals price for cleared bids.
- Gates: technical-clear/decision(admin flag, certifier, legal)=412 until technical open; accounting/committee until commercial; financial-open 412 for sealed.
  Files: /uploads/files + bundle enforce envelope state; create/PATCH require sealed owned bid-docs keys.
- UI: AdminBidDetailPage sealed banner + BidOpeningPanel; /admin/e/bidding "Bid opening" rail panel; Flag hidden for sealed bids.
- Legacy bids (no seal_v) and auction bids unchanged.


## R27 — Signed bid-opening record PDF — 2026-10-31 — build v58k (agent-tested iteration_136: 22/22 + 43/43 sealed suites, UI)
- Approve now needs signer_name (typed e-signature, stripped ≥3) + consent; stores signature {name, ip (x-forwarded-for), user_agent, statement}.
- GET /api/v1/bid-opening/{ref}/record.pdf (after technical opening): landscape PDF with signatures per stage, bids table (deposit/tech/commercial,
  price only when commercially opened), audit-ledger stamp (record code, SHA-256, ledger seq+hash) + QR → public GET /api/v1/bid-opening/verify/{code}
  (recomputes record hash + ledger event hash). db.opening_records (unique code). audit_log now returns {seq, current_hash}.

## Agent onboarding — PLAN PROPOSED 2026-10-31 (awaiting approval; see finish summary). User choices: AI assistant + human agents + both;
agents may fill in for supplier with consent pack (documents, safety, privacy, NDA/indemnity protecting PMC & agent); agent self-onboarding by
email invite with escrow-style form (banking, master country→state→city→zip, country banks editable, KYC/company docs); commission wallet:
onboarding fixed fee + deal fee (fixed or % of PMC business earned); admin pays via Stripe, payouts to agents on schedule or on request.


## R28 — Agent onboarding Phase 1 + opening record email — 2026-10-31 — build v58l (agent-tested iteration_137; agents suite 22/22, sealed 66/66)
- Payouts: user will pay agents manually from own account — NO payment gateway for commissions (Phase 4 = wallet ledger + "mark paid").
- routers/agents.py: admin invite (POST /api/v1/admin/agents/invite, resend, list, get, decision approve|clarify|reject|suspend with note),
  agent join /api/v1/agents/join/{token} (set password → agent_token cookie + CSRF), login (5 fails/15 min by email → 429), logout, me,
  PATCH me/profile (draft/needs_clarification only), agreement (version 2026-10-v1, 6 consents + typed signature + IP), submit (validates fields,
  bank, KYC docs by entity type, agreement) → emails admins. Agreement text is a DRAFT template — owner's lawyer should review.
- Frontend: /agent/join/:token, /agent/login, /agent/me (Profile via EscrowCoreForm `individual` prop, Banking via EscrowBankingStep, Documents,
  Agreement); admin /admin/e/agents ("Onboarding agents" in side nav). agent-docs uploads owner-checked (owner_agent_id).
- bid_opening: when last member approves a stage, background task issues the signed record and emails PDF to every committee member.

## R29 — Agent → "Partner": login, self-registration, registration fee — 2026-10-31 — build v58m (agent-tested iteration_138; suites 38/38 + sealed 66/66)
- Main sign-in has 5th role "Partner" (signin-role-partner → /partner/me). Routes /partner/register|join/:token|login|me (old /agent/* kept);
  admin nav "Partners" /admin/e/partners. Footer "Become a PMC partner" link (PmcSocialLinks).
- POST /api/v1/agents/register (generic reply, 5/h per ingress IP = rightmost XFF). Login lockout per email.
- Fee type partner_registration (fixed, country rules; one rule covers a group of countries). Admin: "Waive registration fee" tick → Approve;
  else "Send payment request" → Stripe checkout (purpose partner_fee) → status payment_pending; webhook/refresh → apply_partner_payment →
  approved + partner_code PT-NNNN + receipt PDF email. Waive+approve also allowed from payment_pending.
- NEXT (approved by user): vendor onboarding by partner — invite with partner code, vendor verifies email + consent first, partner fills
  6 sections (agent_token on registration draft, edits marked), vendor reviews & submits with final declaration, 30-day claim lock,
  duplicate checks, revoke/report links, commission only on approval/payment. Mobile OTP waits for WhatsApp/SMS provider.

- NEXT: Phase 2 (agent fills supplier registration + supplier consent pack), Phase 3 (AI guide + human hand-off), Phase 4 (commission rules + wallet, manual payouts).

- PENDING: user to supply Meta credentials + get the 3 templates approved; set webhook in Meta.

- LinkedIn "Feature not available — not enough connections": LinkedIn account-age/connections restriction on new profiles (user-side).


## R30 — Partner-led supplier onboarding + Commission wallet — 2026-10-31 — build v58n (agent-tested iteration_139: 32/33 → all fixed; v66 suite 16/16 standalone)
- routers/partner_suppliers.py: approved partner invites supplier (company, email, mobile) → registration draft with partner_id/code, 30-day claim,
  duplicate checks (vendor email / company name / own invite / other partner claim / self-started). Unconsented expired/declined/revoked claims
  released to a new partner. Consent page /supplier-invite/:token (6 consents, typed name, IP) = email verification; decline → withdrawn; 2nd reply 409.
- Partner fills via /register/resume?token=<partner_edit_token>&from=partner (valid only with that partner's cookie). decl_*, signature_*,
  document_slots stripped from partner PATCH; every edit logged. Section E locked for partner; partner cannot submit. Send-for-review emails
  supplier. Supplier banner lists partner-filled fields + "Remove partner access".
- Commission: default rule (currency, onboarding fixed, deal fixed or %) + per-partner override; onboarding auto-accrues on approval (access granted);
  admin adds deal commissions; mark paid (reference, emails partner) / void, race-safe; partner wallet + Request payout. NO payout gateway.
- Sign-in: Partner role → "Register as a partner" → /partner/register; Google button hidden for partner.
- NEXT: supplier mobile OTP (needs SMS/WhatsApp provider); admin reassign for disputed claims; WhatsApp/LinkedIn/Stripe live checks still pending.


## R31 — Reassign supplier, partner leaderboard, supplier self-fill, partner code through lifecycle — 2026-10-31 — build v58o (agent-tested iteration_140; v67+v68 suites 44/44 after fixes)
- Supplier invite choices: let partner fill / "I'll fill it myself" (self_fill: name + data-privacy tick, partner stays linked) / decline.
  POST /api/v1/registrations/{rid}/partner-access/mode?token= switches self ↔ partner (partner needs typed name). Commission counts for both.
- Partner code stamped on vendor doc (approval), bids, contracts (from bid), payment_transactions (emd, category, tender fees, billing).
  Shown: admin vendor KPI, vendor account page, admin bid detail, contract detail, billing transactions. Partner tokens excluded from vendor.profile.
- Admin reassign POST /api/v1/admin/partner-suppliers/{rid}/reassign {partner_id, note}: draft → supplier re-consents for new partner;
  submitted → self_fill; approved (re-org) → vendor doc updated; partner_history kept on registration + vendor; old commission stays.
  Blocked for declined/withdrawn/rejected and approved-with-revoked-access.
- Leaderboard (partner tab + admin card): approved this month (credited to approving partner) then invites (credited to inviter);
  admin toggle show names (default codes only).


## R32 — Login return-path fix, legacy logins retired, partner password reset, partner statements + badges — 2026-10-31 — build v58p (agent-tested iteration_141; v69 14/14)
- /login honours ?next= (preselects role from path incl. /partner, shows notice, returns there after sign-in) and ?role=. /admin/login,
  /vendor/login, /staff/login, /escrow/login (without token/claim/reset) redirect to /login?role=…. Admin partner-review email explains sign-in.
- Forgot/reset password supports Partner portal (db.agents, bumps token_generation); reset returns to /login?role=<portal>.
- routers/partner_statements.py: statement PDF (suppliers, invites, commission earned, payouts, still due, badges) — partner
  /api/v1/agents/me/statement.pdf?month=, admin /api/v1/admin/agents/{aid}/statement.pdf, admin "Email statements now",
  cron 0 7 1 * * POST /api/v1/cron/partner-monthly-statements (db.partner_statements; retries rows whose email failed).
  NOTE: crons.yml runs only on Emergent hosting — on AWS EB schedule the endpoint via EventBridge/cron with Bearer WEBHOOK_CRON_SECRET.
- Badges per month: top_partner, most_invites, rising_star (first approval). Partner portal Leaderboard tab; homepage "Partners of the month"
  section (last month, else this month so far; codes unless admin shows names; hidden when empty).


## R33 — Partner profile cards + AWS cron script — 2026-10-31 — build v58q (agent-tested iteration_142; v70 16/16, v69 14/14)
- Partner opt-in homepage card: photo (jpg/png/webp ≤2MB, magic-byte checked, db.partner_photos) + bio ≤280; shown with name in
  "Partners of the month" for badge winners; admin Hide/Show from homepage. Endpoints /api/v1/agents/me/public-profile|public-photo,
  /api/v1/public/partner-photo/{code}, /api/v1/admin/agents/{aid}/public-profile/hide.
- scripts/aws_eventbridge_crons.sh (also /downloads/): EventBridge connection (Bearer WEBHOOK_CRON_SECRET from SSM /pmc/prod/WEBHOOK_CRON_SECRET)
  + API destinations + rules: partner statements (1st 07:00 UTC), marketing digest (Mon 08:00 UTC), category payment reminders (daily 09:00 UTC).
- Known LOW: on first ~250ms after page load the /login role choice / join password fields can reset (app bootstrap remount) — pre-existing.


## R34 — Email error visibility, sign-in fixes, partner referral links — 2026-10-31 — build v58r (agent-tested iteration_143; v71 14/14, v67 33/33)
- emails.send_email records the provider's reason (emails.last_error); admin partner invite/resend toasts show it.
- Forgot password: Administrator radio had value "staff" (both highlighted) → fixed. /login keeps chosen role in ?role=; fields grid
  minmax(0,1fr) so Partner/Escrow boxes align (also on mobile). Register start: empty-email toast.
- Partner referral link /register?partner=PT-XXXX (stored in localStorage; banner on start page) → registration tagged partner_access self_fill,
  partner_source link, invited_by_partner_id. GET /api/v1/public/partner/{code}. Partner portal "Your personal sign-up link" (copy / WhatsApp).
- Known: inputs typed in the first ~1s on preview can be wiped (seen in preview dev server; not reproduced as code cause) — verify on production.


## R35 — Email health check — 2026-10-31 — build v58s (self-tested: curl + admin UI screenshot)
- routers/email_health.py: GET /api/v1/admin/email/health (key set, key accepted, sender, Resend domain status; send-only keys handled),
  POST /api/v1/admin/email/test {to} → real send, returns provider reason on failure. UI card under Admin → Marketing → Website links.


## R36 — Meta data-deletion page, demo showcase data, committee opening in staff portal — 2026-10-31 — build v58u (iteration_144 walkthrough → fixes; self-verified)
- /data-deletion page (Meta app settings requirement). Video pack PDF: /downloads/pmc-video-pack.pdf (scripts/build_video_pack.py).
- scripts/demo_showcase.py seed|clean (PREVIEW ONLY; demo_showcase=True, @demo.pmcmanagers.com, password in test_credentials.md):
  partner PT-DEMO + wallet, 3 suppliers, consent-pending invite, 3 open tenders, DEMO-TND-OPEN with 2 sealed bids + committee, escrow institution/account/2 EMD txns.
- FIX (real product gap): committee members had no UI to approve bid opening → Staff portal "Bid opening" tab (committee_member role).
- Vendor My bids KPIs use bid currency; partner statement month defaults to current month; supplier row separator fix.

## R37 — Video shots v2 (cleaned + missing) — 2026-11-01
- scripts/demo_showcase_extra.py (run after demo_showcase.py seed): partner join/submitted demo agents, partner-filled supplier draft,
  DEMO-TND-AWD opened by both committee members (tech+commercial) and awarded with award docs.
- scripts/capture_video_shots_v2.py → /downloads/pmc-video-shots-v2.zip (screens masked: non-demo emails → officer@demo…, preview host →
  www.pmcmanagers.com, Stripe test warnings and 'sakina' rows hidden). Not captured: escrow institution dashboard (needs escrow login),
  DocuSign two-officer signing screen (no demo signing envelope).

## R38 — Partner sign-up country + clear submit checklist — 2026-11-01 (agent-tested iteration_145, 8/8 backend + E2E)
- /partner/register asks Country (stored on agent, pre-fills Profile). API field optional for older callers.
- Documents step marks required docs (* + Required). Agreement step lists missing items with Go-to buttons; Submit disabled until complete; submit saves profile first.
- Known (pre-existing, LOW): fresh sessions may auto-reload once after load (version guard), wiping typed text.

## R39 — Partner login message + first-visit reload fix — 2026-11-01 (self-tested: curl + Playwright)
- Partner login verified working from main /login (register→join→login 200). Wrong password now shows a clear partner-specific message (autofill / Supplier role / Forgot password hints).
- SwUpdateBanner: no longer reloads on first service-worker install (only on real updates) — typed text no longer wiped on first visit.


## R40 — Show-password eye toggle + release bundle v58v — 2026-11-01 (self-tested: Playwright)
- components/PasswordInput.jsx (eye/eye-off, data-testid `<input-testid>-toggle`) used by all 18 screens with password boxes.
- Bundles: /downloads/pmc-backend-v58v.zip, /downloads/pmc-frontend-v58v-prod-build.zip (scripts/build_v58v.sh). Not yet deployed to AWS.

## R41 — Public links always pmcmanagers.com — 2026-11-01 (self-tested: Playwright)
- frontend/.env REACT_APP_PUBLIC_SITE_URL=https://www.pmcmanagers.com; lib/site.js PUBLIC_SITE used for partner sign-up link, auction invite/live links, meeting links, escrow signing link.
- Payment return URLs still use the current site (needed so checkout returns to where the user is).
- Bundles: pmc-backend-v58w.zip, pmc-frontend-v58w-prod-build.zip (scripts/build_v58w.sh).
- NEXT (approved): Tender Criteria Builder Stage 1 for every tender — buyer criteria (measure, rule, unit/currency/period, proof, must-pass/scored, consortium applies-to), AI pre-fill from tender doc where possible else blank, supplier answers sealed in bid; then auto-qualification at opening; then consortium.

## R42 — Tender Criteria Builder Stage 1 + own Google OAuth + partner CSRF + phone dropdown — 2026-11-01 (agent-tested iteration_146/147)
- backend/routers/tender_criteria.py: criteria per notice (tender_criteria on notices; measure, gte/lte/eq + value + unit, period, proof, must_pass/scored, auto/evaluator scoring, consortium_rule lead/combined/each, prefill_field), templates, AI read from tender text (Claude via tender_pro._llm_complete), vendor prefill, clean_answers().
- Publish needs >=1 must-pass criterion (POST /publish and PATCH is_published); create-with-publish removed (draft first). Criteria locked once live.
- Bids: criteria_answers sealed in criteria_answers_json (SEALED_FIELDS_TECH), proofs as documents with criterion_id. Drafts keep criteria_answers.
- UI: NoticesPanel "Criteria" button → notice/CriteriaEditorModal.jsx; vendor BidSubmit → BidCriteriaSection.jsx.
- Google sign-in: routers/google_auth.py own OAuth code flow (/config, /start, /exchange; oauth_states). Needs GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET (not yet provided) — button hidden until set. Redirect URI: <site>/auth/google/callback.
- Partner CSRF: session-bound HMAC for agent:<id> (security._agent_sub); agent login/join/me return + cache csrf_token.
- PhonePrefixInput closes on outside click / Escape.
- Bundles: pmc-backend-v58x.zip, pmc-frontend-v58x-prod-build.zip.
- Not gated yet: hosting-fee auto-publish, vendor-tender approve, template publish paths. NEXT: Stage 2 auto-qualification at opening, then consortium.

## R43 — Criteria on every publish path + AI document check + Stage 2 auto-qualification — 2026-11-01 (agent-tested iteration_148/149/150)
- Publish gate on all paths: hosting-fee paid publishes only if must-pass criteria exist (else stays draft for admin); vendor-tender submit + admin approve need must-pass; template submit-review needs must-pass; template approve creates live notice only with criteria, else draft.
- Supplier criteria: /tender-criteria/{ref}/mine (GET/PUT/ai-suggest) for vendor tenders; /tender-criteria/template/{tid}/mine for Tender Builder (read for owner/admin anytime, edit while draft). UI: CriteriaEditorModal mode=vendor|template|admin; buttons in VendorTenderBuilderE + TenderBuilderPanel (tb-criteria).
- AI check (admin/reviewer): POST /tender-criteria/{ref}/ai-check compares tender document with entered criteria → mismatches/missing stored as criteria_ai_check, shown in modal; cleared on criteria save. AI never edits criteria.
- Stage 2: at technical opening, sealed answers decrypted and evaluate() gives pass/fail + reasons per must-pass, auto points for scored, pending for evaluator items → bid.qualification; qualified bids auto technical_cleared. Commercial opening only for qualified; blockers count open doubts only. Committee: GET qualification, raise doubt (logged reason, per criterion), decide (uphold/disqualify), evaluator score. Opening record has "Qualification (system check)" column. UI: bidding/QualificationPanel.jsx in BidOpeningPanel.
- Open: hosting-fee confirmation email wording when tender stays draft not adjusted; AI title dedupe is fuzzy (contains match) only.
- NEXT: consortium bidding on top of criteria; Google OAuth keys still needed.

## R44 — Partner draft fix + Consortium bidding + Bidder result notices — 2026-11-01 (agent-tested iteration_151/152)
- Partners: resend works for invited (new link) and draft/needs_clarification (finish-profile reminder); re-inviting an existing invited/draft email re-sends instead of "exists"; admin can edit partner details (PATCH /api/v1/admin/agents/{id}/profile). UI in AdminAgentsE (Edit details, Send reminder).
- Consortium (routers/consortia.py, db.consortia, db.platform_settings{_id:"consortium"}): admin default max members (default 5) + per-tender override (consortium_allowed / consortium_max_members saved with criteria). Lead forms team of registered, KYC-passed suppliers; invite/accept/decline/leave/remove; shares must total 100; escrow shared|separate; deposit lead_pays|each_pays_share; agreement = uploaded signed file OR every member signs standard agreement. Bid with consortium_id stores snapshot; members can't bid alone; bid withdraw returns consortium to forming.
- Criteria rules for consortium: lead / combined (sum, any-yes) / each (every member, failing names in reason). Per-member answers in bid form.
- Result notices: preliminary after technical opening, final before price opening; email + vendor bell + My bids "Criteria results"; own results + qualified count only; per-recipient email status stored.
- UI: vendor /vendor/consortia, BidConsortiumBox + ConsortiumCard on bid page, CriteriaResultNotices.
- Not built: actual escrow payment splitting after award (terms stored only).

## R45 — Consortium escrow split + result-notice delivery admin + bundle v58y — 2026-11-01 (agent-tested iteration_153)
- routers/consortium_split.py: on dual-signed escrow release of a consortium bid, tx.consortium_split recorded (contractor: by shares, remainder to lead; refund: lead_pays → 100% lead, each_pays_share → by shares; forfeit none; route text shared vs separate escrow); members emailed; preview GET before release; Mark paid per line with reference; list /api/v1/escrow/consortium-splits. UI ConsortiumSplitBox in escrow transactions.
- Result notices admin: GET /tender-criteria/{ref}/result-notices, POST .../resend (admin; returns ok:false + error instead of 5xx). UI ResultNoticesPanel in BidOpeningPanel.
- Bundles: /downloads/pmc-backend-v58y.zip, /downloads/pmc-frontend-v58y-prod-build.zip (scripts/build_v58y.sh).

## R46 — Consortium payment instructions with dual officer signatures + bundle v58z — 2026-11-01 (agent-tested iteration_154/155)
- User chose manual bank transfers, but tighter (no automatic payouts). Each split line = payment instruction (<bid_ref>-P<n>) with member bank snapshot (vendors/registrations bank_* fields). Both escrow officers (PMC + institution, per tx account snapshot) must sign (staff endpoint or magic-link portal /escrow/officer/:token) → approved; then admin/accounting records payment with reference + uploaded slip (vendor-docs key, unowned, unsealed). Atomic per-line updates (no lost signatures); bank-account change after signing blocks payment.
- Bundles: /downloads/pmc-backend-v58z.zip, /downloads/pmc-frontend-v58z-prod-build.zip (scripts/build_v58z.sh).

## R47 — Member payout view + consortium payments CSV + life-cycle guide + bundle v59a — 2026-11-01 (self-tested via API + screenshots)
- GET /api/v1/escrow/consortium-payouts/mine (vendor: own lines only, bank last-4, officer sides/dates, paid ref). UI: Consortia → "My consortium payments" (MyConsortiumPayouts.jsx).
- GET /api/v1/escrow/consortium-splits.csv (admin/accounting/auditor; audit-logged). Button "Consortium payments · CSV" on admin escrow ledger.
- scripts/capture_consortium_guide.py run|shot1|clean — seeds DEMO-CONSORTIUM-2026 (tenant PMC-KZ-01), drives full life cycle with real APIs, screenshots 11 steps, builds /downloads/pmc-consortium-guide.pdf + pmc-consortium-guide-screens.zip; demo data cleaned afterwards.
- Bundles: /downloads/pmc-backend-v59a.zip, /downloads/pmc-frontend-v59a-prod-build.zip.






