# PMC Managers v2 — PRD (last touched 15 Oct 2026)
## v53l — Signatory-required badge + one-click Backfill (16 Oct 2026)

- **Signatory-required health check per row:** AccountRow in
  EscrowAccountsSection.jsx compares current signers to the pool and
  shows red SIGNATORY REQUIRED badge + ✗ marks + breakdown when the
  institution name doesn't match any approved master, the PMC officer
  email isn't a flagged staff, or the escrow officer email isn't a
  signatory of the matched institution.
- **Backend backfill:** `POST /api/v1/escrow/accounts/{aid}/backfill-signers`
  (admin). Matches institution to master (case+whitespace insensitive),
  refreshes PMC/escrow officer rows from the pool, or swaps escrow
  officer to first institution signatory. Returns 409 with closest
  legal_name suggestions when institution unmatched. Audit event
  `escrow.account.backfill_signers`.
- **Frontend:** red Backfill button appears only on flagged rows, shows
  diagnostics toast with what was refreshed/swapped/left as-is.
- Known production login crash is NOT in this bundle — deployer could
  not RCA (AWS-hosted; v3 deployment not found). See DOWNLOAD_v53l.md
  for 2-minute self-diagnosis via F12 Network tab.
- Bundles: pmc-backend-v53l.zip + pmc-frontend-v53l-prod-build.zip.


## v53k — Dropdown-driven joint escrow signatories (16 Oct 2026)

- **Blocker fixed:** EMD-bearing bids were stuck at `emd_paid` because
  joint escrow accounts stored signatories as free text, not linked to
  any real PMC staff or institution signatory. Nobody could actually act
  on the escrow-accept step.
- **Backend:** `is_escrow_signatory` added to `StaffCreateIn` /
  `StaffUpdateIn` (persisted on `admin_users`). New admin endpoint
  `GET /api/v1/escrow/signatory-pool` returns `pmc_officers` (active
  staff with the flag) + `institutions` (approved rows with signatories).
- **Frontend:** Joint-account create and edit use dropdowns sourced from
  the pool for institution, PMC officer, and escrow-institution officer.
  Masters → Staff shows an "Escrow signatory" checkbox in create + edit,
  plus an `escrow-signer` badge on the roster.
- **Operator steps post-deploy:** flag at least one PMC staff as escrow
  signatory and ensure at least one escrow institution is approved; then
  joint-account creation routes correctly and `emd_paid → escrow_accepted`
  advances.
- Bundles: pmc-backend-v53k.zip + pmc-frontend-v53k-prod-build.zip.


## v53j — Resend/decline/awarded panel + weekly digest cron (16 Oct 2026)

- **Resend invite (admin, one-click):** new POST
  `/{aid}/invite/{token}/resend` reuses the stored token + default
  template and emails a "Reminder — …" nudge via Resend. Admin UI shows
  Resend button inline per pending invite row with resent_count tracking.
- **Decline-with-reason (vendor):** new POST `/invite/decline/{token}`.
  AuctionRoom shows "Decline with reason" button beside Join when the
  vendor is an invitee who hasn't joined; textarea → persists
  `status: declined`, `decline_reason`, `declined_at` and fires admin
  notification. Admin panel shows declined badge + reasons summary.
- **Awarded reverse auctions panel:** new GET `/awarded/list` + new page
  AdminAwardedAuctionsE at `/admin/e/awarded-auctions` (sidebar entry
  added). Columns: title/notice, winner, starting → final, saving %
  (emerald when ≥10%), current pipeline stage, awarded date.
- **Weekly opportunity digest cron:** second entry in
  `.emergent/crons.yml` (`0 9 * * 1`), hits
  `/api/v1/cron/vendor-opportunity-digest`. New router
  `routers/cron_vendor_digest.py` (bearer-auth, idempotent via
  `cron_runs`, ACKs 200 + enqueues `_do_digest` via asyncio.create_task).
  Groups still-open invites per vendor and emails one digest per week.
- **state-mine (auction_live.py):** now also returns `me.invite_token`,
  `me.invite_status`, `me.decline_reason` so the vendor room can wire
  the decline action to the correct token.
- Preview smoke: cron 401 w/o bearer, 200 w/ bearer; awarded/resend/
  decline endpoints 401 unauthenticated. Code-level verified.
- Bundles: pmc-backend-v53j.zip + pmc-frontend-v53j-prod-build.zip.


## v53i — Invited-but-didn't-register fan-out + distinct outcome (16 Oct 2026)

- **User report:** awarded auction (winner managerspmc@gmail.com) → the
  other invitee info@emeraldcorporates.com got no email at close, and the
  auction was not referenced on their dashboard with "invited but did not
  participate" context.
- **Root cause #1 (silent email gap):** `close_reverse_auction` fanned out
  only to `reverse_auction_participants` (vendors who registered). Invitees
  who never clicked the invite link were skipped entirely.
- **Root cause #2 (misleading UI):** `/mine` already returns invited
  auctions, but `_stamp_outcome` only had `won`/`lost` — invitees who
  never bid got `outcome: "lost"` and the UI said "your bid was not the
  lowest", which is wrong.
- **Backend (auction_live.py):**
  - `_stamp_outcome` now async; new third outcome `not_participated` for
    invited vendors with no participant row.
  - `close_reverse_auction` → after mailing losers, loops
    `reverse_auction_invitations` and mails every non-participant invitee
    ("you were invited but did not register, auction closed, awarded to
    another bidder").
  - `award_reverse_auction` → same fan-out at award time so the user's
    existing Modular OT auction (closed before v53i) still mails
    info@emeraldcorporates.com + any registered losers on the next
    Award Winner click.
- **Frontend (VendorAuctionsE.jsx):** new grey "invited — did not
  participate — awarded to another bidder" badge row for
  `outcome === "not_participated"`.
- Bundles: pmc-backend-v53i.zip + pmc-frontend-v53i-prod-build.zip.


## v53h — My-bids deep-link honesty + winner-email backfill (16 Oct 2026)

- **Root cause of "bid not in My bids":** TWO auctions exist on
  PMC-NOT-2026-0020 — "OT Auction Wave40 Test" (winner TEST_Dec) was the
  one awarded (BID-AUC-A03BF7); the user's "Modular OT Reverse Round 1"
  (winner Managers PMC) was never awarded (awarded_bid_id null) → no bid
  exists → My bids correctly showed only the old bid. Fix path for user:
  Award winner on the Modular OT row.
- **Backend (auction_live.py):** state-mine now exposes
  `me.awarded_bid_id` / `me.awarded_bid_ref` to the winning vendor only;
  award endpoint backfills missing `winner.vendor_email` from the
  participant record (pre-v53b closes stored none).
- **Frontend (AuctionRoom.jsx):** "What happens next" step 4 is
  conditional — pre-award: "Once PMC confirms the award, the new bid will
  appear under My bids"; post-award: shows the actual BID-AUC ref and
  links to My bids.
- **E2E verified:** pre-v53b-style closed auction → award → email
  backfilled, bid at escrow_accepted (v53g zero-EMD auto-clear), winner's
  state-mine shows awarded_bid_ref. Cleaned.
- Bundles: pmc-backend-v53h.zip + pmc-frontend-v53h-prod-build.zip.


## v53g — Zero-EMD auto-clear for sealed bids + L1 live-statuses fix (16 Oct 2026)

- **bids.py create_bid:** zero-EMD sealed bids now created directly at
  `escrow_accepted` with system workflow_history + `escrow_auto_cleared`,
  and the tender desk is notified (notify_bid_transition). EMD-bearing
  bids unchanged (emd_pending). Same rule as v53f auction awards — the
  user's call: no EMD ⇒ no escrow stop, any bid source.
- **comparison.py L1 bug fixed:** live_statuses excluded every mid-pipeline
  governance status (emd_paid, escrow_accepted, admin_flagged,
  certifier_cleared, legal_cleared, accounting_cleared) — such bids were
  mislabelled "withdrawn/rejected" in L1 results. All alive statuses now
  included. (This was a pre-existing blind spot, made critical by v53f/g.)
- **VendorMyBidsE:** mid-pipeline statuses labelled "In PMC review" and
  counted as Active.
- **E2E verified (preview, real vendor submit):** zero-EMD notice →
  escrow_accepted + system history + admin notification; EMD notice →
  emd_pending, untouched. Data cleaned.
- **Legacy rows:** pre-v53g zero-EMD bids at submitted/emd_pending remain
  movable via the v52cs escrow-accept path; one-time sweep available on
  request.
- Bundles: pmc-backend-v53g.zip + pmc-frontend-v53g-prod-build.zip.


## v53f — Zero-EMD escrow auto-clear (16 Oct 2026)

- **User insight:** no EMD ⇒ no money held ⇒ no escrow sign-off should be
  required. Money layer (institution dual sign-off on releases) already
  only engaged on real EMD transactions; the pipeline layer was the gap —
  zero-EMD auction-awarded bids parked at the manual escrow step.
- **Backend (auction_live.py award):** bids with no EMD due are created
  directly at `escrow_accepted` with two system workflow_history entries +
  `escrow_auto_cleared: true`; next-step notification goes to admin instead
  of escrow agent. EMD-bearing bids unchanged (full manual escrow step).
- **Frontend (AdminAuctionsE):** award toast/tooltip reflect actual landing
  stage.
- **E2E verified:** award → bid at escrow_accepted with system history,
  idempotent re-award, data cleaned.
- **Prod note:** pre-fix bid BID-AUC-A03BF7 still at emd_paid — one-time
  manual accept as escrow@ staff login, or re-award a fresh auction.
- Bundles: pmc-backend-v53f.zip + pmc-frontend-v53f-prod-build.zip.


## v53e — Auction-room back button + awarded-bid discoverability (16 Oct 2026)

- **Vendor AuctionRoom:** v53c's back link was too subtle (11px text) —
  now a prominent bordered "← Back to reverse auctions" button.
- **AdminAuctionsE:** awarded badge now reads "Awarded · in pipeline —
  Track in Bidding Ops →" with a deep link to /admin/e/bidding. Explains
  the confusion: auction-awarded bids sit at `emd_paid` in Bidding Ops and
  only appear in the Awards panel after the full pipeline completes.
  Verified on prod: BID-AUC-A03BF7 (TEST_Dec, USD 925,000,
  PMC-NOT-2026-0020) present at emd_paid.
- **Prod bundle check:** confirmed prod is already serving the v53c/d
  frontend (main.392550cb.js contains ra-back, trophy, award strings).
- Bundle: pmc-frontend-v53e-prod-build.zip (frontend-only).


## v53d — Phone-submit bug fix + Award button in the REAL admin panel (16 Oct 2026)

- **Phone-change greyed button ROOT CAUSE:** `validatePhoneForCountry`
  returns `null` on success; disabled check `phoneError !== ""` treats
  `null` as error → button never enables. Fixed by storing `""` on success
  (`VendorAccountE.jsx` onChange). Verified: 10 digits → enabled; 6 digits
  → disabled with precise error. This also explains "no email": the request
  never left the browser, so prod DB correctly has zero mobile requests.
- **Admin auctions panel fix:** v53b's Award button was added to
  `admin-console/LiveAuctionsPanel.jsx` — DEAD CODE (legacy /admin route).
  The live surface is `admin-console-e/AdminAuctionsE.jsx`
  (`/admin/e/auctions`). Added there: winner line (company, price, −savings%),
  "Award winner" button (closed + winner + not awarded), "Awarded · in
  pipeline" badge, and "Closed with no winning bid" note. Screenshot-verified:
  closed row shows "Won by Bidder-42 · USD 872,500 (−12.8%)" + AWARD WINNER.
- Bundle: pmc-frontend-v53d-prod-build.zip (frontend-only; needs v53b
  backend on EB for /award).


## v53c — Vendor auction UX + prod email root cause found (16 Oct 2026)

- **VendorAuctionsE.jsx:** trophy badge on the list row itself — "You won"
  (closed, outcome=won) / "Contract awarded" (awarded_bid_id set), lucide
  Trophy icon, no need to open the room.
- **AuctionRoom.jsx (vendor room):** "← Back to reverse auctions" link +
  closed-state "What happens next" flow (winner: award email → EMD/escrow/
  legal/accounting → DocuSign PO → My bids; loser: no-action + EMD release
  note).
- **PROD EMAIL RCA (corrected after deeper probes):** version-marker probe
  (`reverse-auctions?created_by_email=zzz` → total 0 vs 9 unfiltered)
  proves prod backend IS current (v52w+); Resend verified working (prod
  test-send ok:true). Prod audit shows only address-change requests (Oct
  7/12) — NO mobile request ever reached the DB, so the vendor's Submit
  never completed (validation/frontend), not an email failure. Asked user
  for the exact toast seen on Submit. (CloudFront rewrites 404s to the SPA
  page, which made route-probe HTML responses misleading.)
- Preview verified: list rows + lost note render, room back-link present,
  no console errors. Trophy/won path API-verified in v53b E2E.
- Bundle: pmc-frontend-v53c-prod-build.zip (frontend-only; backend v53b
  carries the email fix).


## v53b — Reverse-auction award hand-off (16 Oct 2026)

- **Gap closed:** auction close was previously silent and terminal — no
  emails, no bid record, no award path; winners couldn't tell they won.
- **Backend (auction_live.py):** close now fans out emails (admin summary +
  next step, winner "you won" + pipeline explainer, losers not-selected —
  winner identity stays masked). New idempotent `POST /{aid}/award` creates
  a `BID-AUC-XXXXXX` bid at `emd_paid` (source=reverse_auction, linked to
  notice_ref) and fires the standard `notify_bid_transition` to the escrow
  agent — **full governance pipeline kept per user decision** (escrow →
  certifier → legal → accounting → award docs). `_stamp_outcome()` adds
  outcome=won/lost + winning_price + awarded_bid_id to vendor `/mine`.
- **Frontend:** LiveAuctionsPanel closed rows get "Award winner" button →
  "Awarded · in pipeline" badge; VendorAuctionsE shows won/lost outcome
  cards with My bids link; PublicAuctionRoom gets a "← Back to notices"
  link (was a dead-end).
- **E2E verified (preview):** full lifecycle create→register→start→bid→
  close→award→re-award (idempotent)→vendor outcome=won. Test data cleaned.
- **Also answered:** prod email config is FINE — prod test-send returned
  ok:true via Resend; the user's missing profile-change mail is a
  delivery/spam or old-backend question, pending their inbox check.
- **Bundles:** pmc-backend-v53b.zip + pmc-frontend-v53b-prod-build.zip.


## v53a — Vendor address form: masters cascade (16 Oct 2026)

- **VendorAccountE.jsx** Registered-address change form rebuilt:
  Country (250-country master) → State/County (states master, free-text
  fallback when country has none) → City (type-to-search 150k cities
  master, state-filtered) → Address line 1 (required) → Address line 2
  (optional) → ZIP. `address_parts` now carries address1/address2/
  state_code; composed one-line value unchanged in format.
- Masters cascade curl-verified (KZ: 20 states, cities by state, q=alm →
  Almaty). Screenshot-verified E2E in preview (vendor login → account →
  address form: KZ → Abai → city type-ahead, Submit enables). Fixed a
  crash where the Submit-button disabled check still referenced the
  removed `street` key (line 514). Frontend build clean.
  Bundle: pmc-frontend-v53a-prod-build.zip.
- **Vendor profile-change emails:** preview verified WORKING (mobile
  change request → 2× Resend 200). Production non-delivery = missing
  RESEND_API_KEY in EB env / SSM /pmc/prod (recurrence of the documented
  EB_ENV_FIX issue). User to add key + redeploy.


## v52z — Create Notice 422 fix + Mongo storage audit (16 Oct 2026)

- **Bug:** Tender Builder → Create Notice / Generate reference → HTTP 422
  "String should have at most 3 characters". Root cause: AI/DPR fill can
  store country as full NAME ("India"); `tender-pro/next-reference` and
  `save-as-master` enforce `country` max_length=3 (ISO-2). Reproduced:
  `next-reference?country=INDIA` → 422; `country=IN` → 200.
- **Fix (frontend-only, `TenderBuilderPanel.jsx`):** `toIso2()` helper maps
  full names → ISO-2 via the 250-country master; applied at `genRef`,
  `saveAsMaster`, and the Create Notice prefill (`delivery_country`).
  Backend stays strict — correct contract.
- **Mongo storage audit (preview DB, 75.3 MB / 84 collections):**
  `masters_unspsc` 40 MB + `masters_cities` 25.4 MB (required reference
  data, user said keep), `uploads` 7.1 MB inline base64 (growth risk, user
  said leave for now), `audit_events` 1.1 MB, notifications 0.3 MB, all
  business data < 1 MB combined. User to pull PROD Atlas sizes themselves
  (step-by-step guide in DOWNLOAD_v52z.md appendix) and report back.
- **Bundle:** pmc-frontend-v52z-prod-build.zip only (no backend change).


## v52y — Corrigenda ↔ Tender Maker date parity + v52x cron REMOVED (16 Oct 2026)

- **Removed v52x submission-close cron entirely** (per user: no
  Emergent-platform dependencies). Deleted
  `routers/cron_submission_close.py`, its server.py registration, and the
  `.emergent/crons.yml` entry. Escrow-expiry cron untouched. Verified:
  endpoint 404; escrow endpoint still 401.
- **Corrigenda now exposes all 10 tender-maker Critical Dates** (7 new:
  Publish Date, Doc DL Start/End, Clarif Start, Sub Start, Bid Opening,
  Bid Award + 3 pre-existing with Tender-Maker labels) so admins can
  restart a closed tender's full timeline from the Corrigenda form.
- **Backend `_AMENDABLE_FIELDS`** extended with the 7 new keys, flat on
  the notice doc. New `_validate_tender_chain(notice, amendments,
  new_submission_deadline)` runs the full `routers/date_rules.py` chain
  (mirrors frontend `tenderDateChainViolations`) over the EFFECTIVE
  post-amendment state on publish, with corrigendum-specific aliasing:
  `sub_end↔submission_deadline`, `clarif_end↔clarification_deadline`,
  `pre_bid_date↔pre_bid_meeting_date`. Future-only checks skipped for
  publish/sub_end (edits live notice); new-deadline past guard retained.
- **Frontend `CorrigendaPanel`** `NOTICE_FIELDS` rebuilt with
  Tender-Maker labels + `chainKey` for each date; hand-rolled validation
  replaced with `tenderDateChainViolations({ requireToday: false })`.
- **Verified E2E (preview, admin login via curl with cookie jar):**
  out-of-order (doc_dl_start > doc_dl_end) → 400 with precise message;
  in-order 10-date restart → 200, corrigendum #2 applied=10, every date
  on notice updated, `amendment_base` captured 10 originals for rollback.
- **Bundles:** pmc-backend-v52y.zip + pmc-frontend-v52y-prod-build.zip.


## v52x — Submission-close notification cron (16 Oct 2026)

- **Gap closed:** deadline expiry was previously silent — nobody was told a
  tender's submission window had closed.
- **New:** `routers/cron_submission_close.py` →
  `POST /api/v1/cron/submission-close-sweep` (bearer auth via
  WEBHOOK_CRON_SECRET, ack-then-background, idempotent via cron_runs +
  per-notice `submission_close_notified_at` flag). Sweeps notices whose
  deadline passed in the last 24h.
- **Fan-out:** admins + committee get per-tender summary (bid counts, EMD
  paid/pending, tech-cleared, per-bid table, next-step checklist); each
  bidder gets their current pipeline stage + full 5-step chain (EMD →
  technical → legal/accounting → committee → award), with action-needed
  warning when EMD unpaid; escrow agents get ONE daily summary of all
  pending EMDs across closed tenders.
- **Schedule:** `.emergent/crons.yml` daily 09:00 Europe/London.
  PRODUCTION NOTE: crons.yml only runs on the Emergent platform — on AWS EB
  the user must wire an external scheduler (EventBridge / cron-job.org) to
  POST the endpoint with the bearer secret (same pattern as escrow cron).
- **Verified in preview:** run 1 → tenders:1, vendor_emails:2, 3 admin + 6
  committee notifications, 1 escrow summary; run 2 → tenders:0 (flag skip);
  same run_id → duplicate:true. Test data cleaned.
- **Bundle:** pmc-backend-v52x.zip (backend-only release; frontend unchanged
  from v52w).


## v52w — Server-side Created-by/From/To rollout to remaining 4 panels (15 Oct 2026)

- **Backend (new params `created_by_email`/`created_from`/`created_to`):**
  `GET /api/v1/reverse-auctions` (auction_live.py) and
  `GET /api/v1/docusign/envelopes` (docusign.py) now regex-match the
  `created_by` field and range-filter ISO-string `created_at`, same pattern
  as bids.py/packages.py/notices.py from v52v. DocuSign `limit` still works
  alongside filters. Evaluation bids + Awards ride on `GET /api/v1/bids`
  which already had the params — no backend change.
- **Frontend:** new `creatorDateParams()` helper in
  `CreatorDateFilterBar.jsx` (omits empty filters). LiveAuctionsPanel,
  DocuSignPanel, EvaluationPanel, AwardsPanel now send the params on every
  filter change; client-side `matchCreatorDate` kept as instant fallback
  (user chose both). `docusignApi.listEnvelopes` signature changed from
  `(limit)` to a params object. Datalist creator sources fixed to read
  `created_by` (auctions/envelopes don't have `created_by_email`).
- **Verified (preview curl, admin login):** auctions empty→7, no-match
  creator→0, 2026 range→7, 2027 range→0; envelopes empty→4, no-match→0,
  range+limit→4, future range→0. Frontend prod build compiles clean.
- **Bundles:** pmc-backend-v52w.zip (20.9MB), pmc-frontend-v52w-prod-build.zip
  (3.9MB), DOWNLOAD_v52w.md — all verified HTTP 200 under /downloads/.


## v52t — Tender date-chain validation (15 Oct 2026)

- **Corrigendum path added (frontend + backend):** `CorrigendaPanel.publish`
  now blocks past new-deadlines / past deadline amendments and pre-bid or
  clarifications-close values landing after the effective submission
  deadline (live toast hints); backend `corrigenda.py` publish enforces the
  same rules (verified: pre-bid after deadline → 400
  "Submission deadline must be on or after Pre-bid meeting date";
  valid clarification-close amendment publishes and withdraws cleanly).
- **Filters verified:** Audit ledger From/To pick up native min/max guards
  (screenshot-verified: setting To immediately caps From).

- **Chain enforced** (both sides, shared rule sets):
  frontend `src/lib/dateRules.js` ↔ backend `routers/date_rules.py`.
  Submission end ≥ today · Publish ≥ today · Pre-bid ≥ Publish ·
  Doc-dl start ≥ Pre-bid · Doc-dl end ≥ Doc-dl start · Clarif start ≥
  Doc-dl end · Clarif end > Clarif start · Sub start ≥ Clarif end ·
  Sub end ≥ Sub start · **Bid Award Date** (new header field) ≥ Sub end.
- **Live hints:** TenderHeaderForm shows a red "Date order problems" box
  that recomputes on every keystroke (screenshot-verified).
- **Block at create/publish:** TenderBuilderPanel refuses "Create notice"
  while violations exist; `notices.py` create rejects past deadlines and
  pre-bid-after-deadline (400 with clear message); `update_notice` PATCH
  enforces ordering only (legacy past dates allowed, per user choice);
  corrigenda publish rejects past new deadlines and meeting/clarification
  dates that land after the effective deadline.
- **Every start/end filter pair guarded** with native `min`/`max` (+toast):
  Audit ledger, Notices list, Escrow institutions (added now);
  BOQ & contracts, Profile change requests, Category requests, and the
  shared `MoneyFilterBar` already enforced it.
- Verified E2E in preview: past deadline → 400, pre-bid after deadline →
  400, valid chain → created, corrigendum past deadline → 400.

## v52s — Production verification of corrigenda fixes (15 Oct 2026)

- **Public notice Corrigenda tab** on `PMC-NOT-2026-0093` now renders both
  corrigenda with full Field/Before/After/Reason tables (screenshot-verified
  on production). Empty-state regression ("No corrigenda published") was a
  pre-deploy build, resolved by the v52p backend deploy.
- **Download diff PDF** returns 200 + valid PDF on production for both
  Biogas corrigenda (route `GET /api/v1/notices/{ref}/corrigenda/{cid}/pdf`,
  public, regenerates on demand via `build_corrigendum_pdf`). Earlier 404
  was the pre-v52p production backend missing the route.
- **Withdraw visibility:** verified in preview E2E — withdraw flips
  `is_active=False` server-side and the corrigendum immediately leaves both
  the admin ACTIVE list and the public page (both lists filter on
  `is_active`). Admin panel additionally does an optimistic local flip.

## v52r — Corrigendum form dedupe + production Stripe webhook live (15 Oct 2026)

- **Corrigendum form dedupe:** removed the top-level "Title" and "Overall
  change description" inputs from the New Corrigendum form — they duplicated
  the Title / Description rows in the field-amendment table. Title and
  summary are now derived automatically at publish time
  (`Corrigendum N — <notice title>` + joined per-field reasons; deadline-only
  default text when no field amendments are given). Admin edits the tender's
  title/description directly in the table when those need changing.
  Verified E2E in preview (auto title/summary accepted by backend validation,
  amendment applied to notice, rollback on withdraw).
- **Production Stripe webhook live:** `STRIPE_WEBHOOK_SECRET` loaded via AWS
  SSM Parameter Store (`/pmc/prod/…`); attached
  `ssm:GetParametersByPath` + `kms:Decrypt` inline policy to
  `aws-elasticbeanstalk-ec2-role`; v52p deployed to EB; signed
  `checkout.session.completed` trigger verified end-to-end. Biogas tender
  `PMC-NOT-2026-0093` confirmed showing amended budget/EMD/deadline after
  corrigenda re-publish under the v52q sync fix.

## v52q — Corrigendum amendments sync to the tender notice (15 Oct 2026)

- **Bug:** publishing a corrigendum with field amendments (budget, EMD,
  dates) stored the diff on the corrigendum row but never applied it to the
  parent notice — only `new_submission_deadline` flowed through. The tender
  notice view kept showing stale values (user's Biogas tender).
- **Fix (`routers/corrigenda.py`):** `_apply_corrigendum_amendments` now
  $sets every whitelisted amendment (`title/description/category/
  document_type/delivery_country/submission_deadline/budget_*/
  tender_fee/form_of_contract/emd_fixed_amount/emd_percentage/
  pre_bid_meeting_date/clarification_deadline`) onto the notice, stashing
  pre-amendment values under `amendment_base`. Dotted paths whose parent is
  null (e.g. `emd_config: null`) are materialised as full objects — Mongo
  rejects `$set emd_config.fixed_amount` on a null parent (WriteError 28).
- **Withdraw rollback:** `_rollback_corrigendum_amendments` replays the
  remaining ACTIVE corrigenda (latest wins per field) and restores the
  stashed base when none remain.
- **Verified E2E (PMC-NOT-2026-0102):** publish → budget 50000→555000,
  emd_config {fixed_amount:2500}, deadline updated; withdraw all → restored
  to base. An orphan corrigendum left by an interim 500 was cleaned up.
- **Migration note:** corrigenda published BEFORE this fix never synced.
  User action for the Biogas tender: withdraw Corrigendum 1 and re-publish
  it with the same edits — the new flow applies them to the notice.

## v52p — Bid lockout + categories chip + resync pending + hover fixes (15 Oct 2026)

- **Vendor bid lockout (P0 ask):** `vendor-portal/BidSubmit.jsx` now
  short-circuits to a view-only **"Bidding is closed" / "Bidding hasn't
  opened yet"** screen whenever the current time is outside the admin-set
  `[submission_start, submission_deadline]` window. The old behaviour kept
  rendering the form with just a disabled submit button, confusing vendors
  who thought they could still edit a closed bid. If PMC later extends the
  deadline (or opens a tender) and the current time re-enters the window,
  the form re-appears automatically on next load — no code change needed.
  Backend `routers/bids.py:create_bid` already enforces this with HTTP 400
  on late submits; this is a UX reinforcement.
- **Tender Maker categories (P1 ask):**
  * New `tender/CategoryMultiPicker.jsx` — chip-based picker fed live from
    `/api/v1/masters/categories/public` with multi-select, type-to-add,
    per-chip remove, and star-to-promote to **primary**.
  * `TenderHeaderForm.jsx` swaps the Product Category text input for the
    chip picker.
  * `DprGenerateModal.jsx` surfaces AI-extracted PDF categories as chips in
    the DPR preview card so admins see exactly what the AI picked before
    clicking Create (amber hint when the AI couldn't extract any).
  * Primary chip still writes back to the existing `product_category`
    string (keeps notice create / matching / filters working); a new
    `product_categories` list is stored alongside for the full tagging.
- **Admin "Resync pending payments" (P2 ask → done):**
  * Backend `POST /api/v1/billing/resync-pending?limit=N` in `routers/billing.py`.
    Polls Stripe for every stuck row (`payment_status` ∉ paid/refunded),
    calls the webhook's own idempotent `_mark_paid`, writes a
    `billing.resync_pending` audit event, and returns
    `{scanned, reconciled, still_pending, failed[]}`.
  * Frontend green **Resync pending** button on
    `BillingTransactionsPanel.jsx` with confirm prompt + inline report.
  * Verified E2E in preview (scanned 25, reconciled 0, 20 still pending,
    5 known-stale `cs_test_` ids reported in `failed`).
- **Hover readability (P1 ask):** `index.css` adds matching-weight hover
  rules so `hover:text-white`, `hover:bg-brand-navy`,
  `hover:bg-brand-navy-deep`, `hover:bg-brand-navy-soft` can beat the
  Option-E palette overrides. Fixes:
  * Masters → Staff Master → row **Clone** button (was invisible on
    hover).
  * Masters → Escrow EMD → **Sign · release-to-vendor / forfeit /
    release-to-contractor** and **Release** button.
  * Admin → Billing → **Refresh** / **Resync pending**.
- **Stripe production webhook (P2 ask, no code change):** existing handler
  already enforces `STRIPE_WEBHOOK_SECRET` and returns 503 when missing
  (SEC-001). Operational remediation steps written into
  `public/downloads/DOWNLOAD_v52p.md`:
  1. Stripe Dashboard → Developers → Webhooks → prod endpoint
     (`.../api/webhook/stripe`).
  2. Enable `checkout.session.completed/.async_payment_succeeded/
     .async_payment_failed/.expired` and `charge.refunded`.
  3. Reveal signing secret, set `STRIPE_WEBHOOK_SECRET` on prod backend,
     redeploy.
  4. Confirm Recent deliveries return 200 (not 503).
  5. Admin → Billing → **Resync pending** to reconcile the backlog.

## v52o — Vendor invite: country master dropdown + visible email delivery (15 Oct 2026)

- **Country field:** `VendorsPanel.jsx` quick-invite country was a free-text input; now a `<select>` fed from `mastersGeoApi.countries()` (250-row master, ISO-2 codes stored — consistent with the full registration form and KYC routing).
- **Email delivery visibility:** `vendor_invites.invite_vendor` fired `asyncio.create_task(send_email(...))` — fire-and-forget, so the UI toasted "Invited" even when Resend failed. The send is now awaited; the API returns `email_sent`; the UI shows a warning toast on failure. `email_sent` is also recorded in the `vendor.invite` audit event.
- **Verified:** invite round-trip returns `email_sent: true` with Resend HTTP 200 in logs; dropdown renders 250 options and stores the ISO code (screenshot iteration_83).
- **Note:** `/api/v1/vendors/invite` is mounted twice (vendor_invites router at server.py lines 178 & 217; first match wins — behavior unchanged, cosmetic duplication only).

## v52n — Audit rechain speed + reverse-auction invite delivery (15 Oct 2026)

- **Audit repair timeout (reported "timeout of 20000ms exceeded"):** `rechain_audit()` was issuing one `update_one` per event (~4300 docs). Rewritten with 500-doc `bulk_write` batches; prod-size ledger now rechains in < 1 s. Frontend `repairAudit` call also gets a 120 s per-request timeout as safety net.
- **Reverse-auction invites "shown as sent but not received":** two independent bugs.
  1. Stored default template had no `{{invite_url}}` placeholder → recipients got a mail with no join link. Backend now appends a "Join the auction" button + fallback URL whenever the body lacks the placeholder, and a one-time DB backfill patched the stored default template (1 row).
  2. Burst invites > 10 recipients hit Resend's 10 req/s rate limit; later rows silently 429'd. Added `asyncio.sleep(0.12)` between sends. Verified: 10-row burst → `auto_sent: 10`, 0 × 429 in logs.

## v52m — Audit ledger: race fix + repair + real filters (15 Oct 2026)

- **Root cause of "chain broken":** `audit_log` allocated the seq and read the last hash in two non-atomic steps — concurrent writers (login bursts) chained off the same parent (preview: seq 1503/1504 share `previous_hash`, 0.6 ms apart; prod broke at 2037 the same way). Not tampering.
- **Fixes:**
  - `audit.py`: process-level `asyncio.Lock` wraps seq → read-last → insert; writes are serialized (single-instance deployment).
  - New `rechain_audit()` + `POST /api/v1/audit-events/rechain` (admin, CSRF): recomputes previous/current hash links for the whole ledger, payloads untouched, appends an `audit.chain_repaired` marker event.
  - `GET /api/v1/audit-events` now supports server-side `event_type` / `actor` (case-insensitive substring, regex-escaped), `from_date` / `to_date` (inclusive), `target_type`, limit ≤ 500. Previously the UI fetched the last 100 and filtered client-side — older matches were invisible.
  - UI (`AuditPanel.jsx`): filters refetch server-side (350 ms debounce); failed verify now explains the legacy race and offers a **Repair chain** button that rechains and re-verifies.
- **Verified:** chain broken at 1504 → rechain (2431 events, 932 links rewritten) → verify OK; 30 parallel logins → chain still OK (2462 events); filters: staff.login 163/163 match, actor substring, from-date, and type+date combo all correct.

## v52l — Owner pause banners + Suggested Banks light pin (15 Oct 2026)

- **Owner visibility:** `EscrowAccountDashboardBody` overview and `EscrowInstitutionProfile` both render an amber "Changes pending PMC review — institution paused (not live)" banner while status is `changes_requested`; invite section shows lock copy and the form stays disabled until the queue clears.
- **Palette:** `admin-bank-master-page` (Suggested banks curation) pinned to the light palette like the Escrow Institutions page (bg/text/inputs/hover).
- **Verified:** ACME flipped to `changes_requested` via a real change request; overview banner + profile banner + locked invite copy all render (screenshots iteration_80_*); Suggested Banks page computed colors stay light/readable.

## v52k — Pause-on-change + readable diffs + multi-invite (15 Oct 2026)

- **Status gate (user decision):** approved institution + any pending change request ⇒ status `changes_requested` ("not live"); auto-restores to `approved` when the queue empties (approve/reject/cancel). `previous_status` tracked; `Status` Literal + admin filter + chart sources updated; signatory invites blocked while paused (403).
- **Admin list** now returns `pending_changes` per institution; pipeline rows show an orange "N changes pending" badge; status filter gained "Changes pending (awaiting approval)".
- **Readable review:** Current/Proposed diff boxes render plain values / document cards (filename · KB · View) / list items instead of JSON; inline-styled to dodge the global `[data-ui="e"]` slate→dark remap; whole page palette pinned light in `index.css` (bg + text + inputs + hover) — fixes the dark-on-hover / dark box issue.
- **Invite form:** multi-row with "+ Add another teammate" + per-row remove; country dial dropdown (30 countries from `lib/phoneCountries.js`) with per-country digit validation; backend enforces `^\+\d{1,4}\s?\d{5,15}$` (422 otherwise).
- **Verified:** full status round-trip (create→paused, approve-1-of-2→still paused, cancel-last→approved, reject→approved); filter+count 200; bad phone 422 / good phone 200 / paused 403; UI add/remove rows + validation toast + readable admin diff (screenshots iter 79).

## v52j — Signatory claim auto-login (15 Oct 2026)

- **Reported:** magic-link claim showed BOTH a green "Password set" toast and a red "HTTP 401 Invalid email or password" toast. Backend logs showed `/claim` → 200, then an auto-login `POST /escrow-signatories/auth/login` → 401. Preview reproduction with the same code path returned 200/200 — the production 401 was most likely browser password-autofill cross-wiring or a stale CloudFront-cached frontend touching the two-call sequence.
- **Fix:** `POST /escrow-signatories/claim` now sets the `escrow_sig_token` + `csrf_token` cookies and returns the bearer token + csrf in the body. Frontend no longer makes a second `/auth/login` call — one toast, one navigation. Standalone sign-in still works for returning users.
- **Verified:** claim response carries `token`, `csrf_token`, drops both session cookies; `/auth/me` 200 immediately; a fresh-session login with the same email+password still returns 200 after the claim.

## v52i — Escrow password reset + legacy account recovery (15 Oct 2026)

- **Root cause of "reset not working":** escrow *account* reset emails link to `/escrow/login?reset=1&token=…`, but that page only posted to the **signatory** reset endpoint (`escrow_sig_password_resets`); account tokens live on `escrow_accounts.reset_token` → every account reset failed with "invalid link".
- **Root cause of "invalid credentials on approved institution":** institutions registered under the old magic-link flow have **no `escrow_accounts` row at all**, so login 401s and forgot-password silently no-opped — owners were permanently locked out.
- **Fixes:**
  - `POST /escrow-accounts/auth/forgot` now **auto-provisions a verified account** linked to the institution when the email matches a `primary_contact_email` on file (legacy claim). Reset link is emailed only to the address on record — mailbox possession = proof of ownership. Audited as `escrow_account.legacy_claim`.
  - `POST /escrow-accounts/auth/reset` now also flips `status` → `verified` on success.
  - `/escrow/login` reset mode tries the **account** endpoint first, falls back to the signatory endpoint on 400/404; forgot mode fires **both** endpoints (both enumeration-safe).
  - Unified `/forgot-password` page gained an **Escrow Institution** radio that fires both escrow endpoints.
- **Verified end-to-end:** seeded a legacy approved institution with no account → forgot → account auto-created + linked → reset → login 200 with the new password → token single-use (reuse 404) → unknown email still silently 200. Existing verified account forgot/reset/login regression passed. UI: Escrow radio present on `/forgot-password`, sent panel renders.

## v52h — Deployable bundles ready (15 Oct 2026)

- Backend: `/downloads/pmc-backend-v52h.zip` · 20 MB · EB-ready (Dockerfile + .ebextensions at root, no docker-compose, **no .env in the archive**).
- Frontend: `/downloads/pmc-frontend-v52h-prod-build.zip` · 3.8 MB CRA build (14 MB unzipped, `downloads/` pruned).
- Release notes: `/downloads/DOWNLOAD_v52h.md`.
- Contains every v52g / v52g+ / v52h fix: upload crash, CSRF cookie partitioned, download gate for escrow sessions, file view inside iframe (blob fetch), institution profile change-request workflow, admin filters, sign-out to unified `/login`.
- Sessions created before this deploy must sign out and back in once to receive the new `csrf_token` cookie.

## v52h — Document download gate + sign-out routing (15 Oct 2026)

- **Bug 1 — institution users couldn't view uploaded files:** `uploads.py::_require_any_signed_in` only accepted admin Bearer or vendor cookie, so escrow account / signatory sessions got 401 on `/api/v1/uploads/files/{key}`. Now accepts `escrow_account_token` and `escrow_sig_token` cookies too (lazy imports, anonymous still 401).
- **Bug 2 — sign-out landed on `/escrow/login`:** `EscrowAccountHeader` sign-out now routes to the unified `/login` page.
- **UX:** Institution profile documents now show a **View** link next to Replace (when a file exists); admin change-request panel shows **View proposed file** for document replacements.
- **Verification:** escrow cookie GET → 200, anonymous → 401, admin bearer + admin cookie (new-tab case) → 200. Browser: View button visible, in-page fetch 200, sign-out lands on `/login` with "Signed out" toast.



- **Reported issue:** submitting a profile change request from `/escrow/me` 403'd with `CSRF token missing or invalid` in the preview iframe.
- **Root cause (two layers):**
  1. Escrow login handlers never cached the server-issued CSRF token into `sessionStorage` (admin/vendor logins already did via `cacheCsrf()`), so iframe sessions that lose the JS-readable cookie had no header fallback.
  2. Deeper cause confirmed via response headers: the platform proxy rewrites auth cookies (`escrow_account_token`, `vendor_token`, `access_token`, `escrow_sig_token`) to `SameSite=None; Partitioned`, but the app's own `csrf_token` cookie stayed `SameSite=Lax`, which cross-site iframes drop on POST. `require_csrf` requires header AND cookie, so the header fallback alone still 403'd.
- **Fix:**
  - `security.py`: new `set_csrf_cookie()` helper appends a raw `Set-Cookie: csrf_token=...; Secure; SameSite=None; Partitioned` (Starlette 0.37 lacks the `partitioned` kwarg).
  - All five auth routers (`admin_auth`, `staff_auth`, `vendor_auth`, `escrow_accounts`, `escrow_signatories`) now use it at login.
  - Frontend: exported `cacheCsrf` from `lib/api.js` and called it after every escrow login path (`EscrowSignatoryLogin` default/claim/reset-login + unified `/login` Escrow Institution tab).
- **Verification:** curl confirms `Set-Cookie: csrf_token=...; Secure; SameSite=None; Partitioned`. True cross-site iframe repro (localhost page embedding the preview URL): login → profile → submit change request passes with `document.cookie` containing `csrf_token`, no 403, pending entry visible. **Note:** existing sessions must sign out and back in once to receive the new cookie.



- **P0 bug fixed:** institution document upload was failing with `uploadsApi.uploadFile is not a function`. Added a `uploadsApi.uploadFile(file, { scope })` helper in `frontend/src/lib/api.js` that chains presign + direct and returns `{key, filename, content_type, size_bytes, uploaded_at}`. Wizard DocSlot now calls it with scope `escrow-docs`.
- **New change-request workflow (user-chosen scope: all five sections, every stage, unlimited field-level, admin review in the existing panel):**
  - Backend: new router `routers/escrow_profile_changes.py` mounted in `server.py`.
    - `POST /api/v1/escrow-accounts/me/change-requests` — owner creates a pending request (section + field_path + current_value + proposed_value + optional reason).
    - `GET /api/v1/escrow-accounts/me/change-requests` — owner lists their requests.
    - `DELETE /api/v1/escrow-accounts/me/change-requests/{id}` — cancel own pending.
    - `GET /api/v1/escrow-institutions/{iid}/change-requests` — admin list per institution.
    - `POST /api/v1/escrow-institutions/change-requests/{id}/approve` — applies via `$set` and notifies owner.
    - `POST /api/v1/escrow-institutions/change-requests/{id}/reject` — notes required; notifies owner.
    - Allowed targets: whitelisted core fields; whole-array replacement for `signatories` / `banking`; whole-dict or `documents.<slot>` for documents. Admin keys (status/account_id/magic_token/etc.) are rejected 422.
  - Frontend: new `EscrowInstitutionProfile.jsx` replaces the simple ProfileView — full read-only sections, per-field "Request change" buttons, pending list with cancel, document replace that uploads then stages a `documents.<slot>` change request. Admin console gets `ChangeRequestsPanel` inside the detail panel with current-vs-proposed diff and approve/reject buttons.
- **Verification:**
  - Backend round-trip (presign+direct upload, create request, admin approve, applied field, invalid field → 422) all passed via live curl.
  - Preview UI: owner profile tab renders full details and the pending list; new change request submits and reflects immediately.



- **User-reported issue:** login appeared to crash/stick from the main sign-in portal. The supplied recording showed the unified `/login` page with the **Escrow Institution** role selected.
- **Root cause:** `SignInE.jsx` still sent Escrow Institution logins only to the legacy `/api/v1/escrow-signatories/auth/login` endpoint. v52d account-first credentials live in `/api/v1/escrow-accounts/auth/login`, so a valid verified escrow account was rejected as "not an escrow signatory" and remained on `/login`.
- **Fix:** the unified Escrow tab now tries account-first login, preserves the 403 unverified-account message, and falls back to legacy signatory login only on 401/404.
- **Verification:** pre-fix browser repro failed on `/login`; post-fix the same verified account reaches `/escrow/me`. Unified Supplier login also still reaches `/vendor`. Backend vendor and escrow login endpoints returned 200 with the known test accounts.
- **Preview data caveat:** `info@emeraldcorporates.com` has no vendor account, escrow account, or signatory account in the preview database; it only appears on a submitted legacy escrow institution with no account link. Production must be validated after the frontend bundle is deployed.


## v52d — Account-first escrow institution registration (15 Feb 2026)

**User brief:** "first we ask for email, legal entity name and phone — once we verify that we proceed for the other five sections. The email directs them to a login page. He can login but has to proceed to complete the remaining. He also gets notified either through app or his web login." Plus a dashboard header redesign: avatar top-right with Change profile / Change password / Sign out, bell left of the avatar, Sign out → master login page.

**User choices (via ask_human):** Full build (gate + login + account-saved wizard + notifications). Verify-link email (vendor pattern). Primary contact only gets a login. Force everyone to the new flow (legacy POST /escrow-institutions/register → 410).

### Backend (new router + hooks)
- **New router `routers/escrow_accounts.py`** — cookie-based auth (HttpOnly `escrow_account_token` + double-submit CSRF), JWT `type=escrow_account_access`, `token_generation` rotation on password change.
- **New collection `escrow_accounts`** `{email, legal_name, primary_contact_phone, password_hash, status (unverified|verified), verify_token, verify_token_expires_at, token_generation, institution_id, avatar_data_url, created_at}`. Unique by email.
- **New collection `escrow_notifications`** `{account_id, kind, title, body, link, read_at, created_at}`.
- **Endpoints:**
  - `POST /api/v1/escrow-accounts/register` — captures email+legal_name+phone+password → status=unverified → Resend verify email.
  - `GET /api/v1/escrow-accounts/verify/{token}` — one-click verify, auto-creates draft institution owned by the account.
  - `POST /auth/login` — refuses with 403 while unverified; 401 on bad creds.
  - `POST /auth/logout`, `GET /auth/me` (includes institution snapshot + unread_notifications count), `POST /auth/change-password`, `POST /auth/forgot`, `POST /auth/reset`, `POST /auth/resend-verify`.
  - `PATCH /me/profile` — updates legal_name/phone/avatar, mirrors to owned institution.
  - `GET /me/notifications`, `POST /me/notifications/{id}/read`, `POST /me/notifications/mark-all-read`.
  - `notify_account()` helper used by the admin decision endpoint and submit flow — writes in-app row AND fires email.
- **Legacy guard:** old `POST /api/v1/escrow-institutions/register` → **HTTP 410 Gone** pointing to `/escrow/register` so no orphan drafts are created.
- **Session gate on institution writes:** `escrow_institutions.py` now has `_institution_for_write(iid, request, token)` — cookie-first, magic-token fallback. PATCH/submit/dashboard all route through it so admin-invited magic links keep working during the transition.
- **Status-change hook:** admin decide (approve / reject / needs_clarification) and submit now call `notify_account(...)` so the account owner's bell + inbox update immediately.
- **New owner-scoped read:** `GET /api/v1/escrow-institutions/{iid}/admin-view-public` — session-only, 1:1 with the owning account; used by the wizard to preload drafts.

### Frontend
- **`/escrow/register`** — new single-screen gate (email, legal entity name, phone with ISD, password, confirm) → "Check your inbox" state → resend button. Legacy wizard moved to `/escrow/register-legacy` so admin-invited drafts still work.
- **`/escrow/verify/:token`** — one-click verification landing with success/failure states and a Sign-in CTA.
- **`/escrow/login`** — tries `escrow_accounts` login first, falls back to `escrow_signatories` (so pre-approval signatories still sign in). After login routes to `/escrow/me`.
- **`/escrow/me`** — fetches `auth/me`; if institution status in {draft, needs_clarification} renders the new **account-authed wizard** (session cookie, no magic-token URL), otherwise renders the dashboard body.
- **New shared header `EscrowAccountHeader`** — brand lockup left; bell (left of avatar) with unread badge + dropdown + mark-all-read; avatar circle with menu: Change profile, Change password, Sign out → `/escrow/login`. Keyboard-dismiss + outside-click close.
- **Change profile modal** — legal name + phone, saves via `PATCH /me/profile`.
- **Change password modal** — current + new + confirm; backend rotates `token_generation`.

### Tests
- `backend/tests/test_v52d_escrow_accounts.py` — 8 tests, all green:
  - Register creates unverified; login blocked until verified.
  - Verify creates draft institution; subsequent login returns institution snapshot.
  - Duplicate register for unverified reuses the row + re-sends verify.
  - Session cookie authorises PATCH / submit on owned institution.
  - PATCH on foreign institution → 404.
  - Change-password rotates session (new password works).
  - Legacy POST /escrow-institutions/register → 410.
  - Submit notifies the account (kind=submitted).
- Backend end-to-end verified live via curl: register → verify → login → PATCH → submit → notification visible on `GET /me/notifications`.
- Frontend testing_agent iteration 66 covers: gate form validation, inbox-sent screen, unverified login blocked, verify link success/failure, signed-in wizard render, header bell + avatar menu, profile modal save, sign-out, notification bell workflow.

**Pre-seeded demo account** (preview only, see `/app/memory/test_credentials.md`): `escrowdemo@pmcmanagers.com` / `Escrow@12345` — status=verified, institution=draft so the wizard renders immediately.

### v52d post-review patches (15 Feb 2026, from testing_agent iter 66, 67, 68)
- **Unverified-login message surfaced** — `EscrowSignatoryLogin.submitLogin` used to swallow the account endpoint's 403 "unverified" by falling through to the signatory login (which then returned a generic 401). Fallthrough now triggers ONLY on 401/404; 403-unverified calls `toast.error("Sign in failed", {description: detail.message, duration:10000, closeButton:true})` directly so the title reads exactly "Sign in failed".
- **Toast container no longer intercepts header clicks** — root cause was two-fold: (a) a duplicate `<Toaster/>` was mounted in both `src/index.js` AND `src/App.js` so every toast rendered twice, and (b) the top-right toast rect overlapped the header avatar/bell for its ~6s lifetime. Fixes: removed the `index.js` Toaster (App.js is the sole mount, inside providers/error boundary), and added `offset={{ top: 72, right: 16 }}` to the App.js Toaster so toasts open BELOW the header. Live-verified: toast rect top=72, avatar rect bottom=48 — no overlap.
- **Build cache gotcha logged** — the first retest round reported edits "missing on disk". Root cause: webpack dev-server served a stale cached bundle after a .css append + rapid file edits. Fix: `sudo supervisorctl restart frontend` after structural changes (index.js mount changes especially); hot-reload alone wasn't enough.

### v52d — Final retest (iter 69) outcome
- **100% pass**, retest_needed=false. Live-DOM evidence: toaster_count=1, toast rect top=72 (sits below the ~60px header, no overlap), avatar normal page.click opens the menu while the "Signed in" toast is visible, 403-unverified toast title is exactly "Sign in failed" with the "Please verify your email…" description, avatar menu order is Change profile → Change password → Sign out, sign-out returns to `/escrow/login`, bell dropdown empty state renders correctly.


## v52e — Escrow full-flow completion (15 Feb 2026)

User brief: "can we complete this full flow of escrow and then continue with deployment". Three items from the v52d backlog, shipped together:

### 1. Admin pipeline — "Account" column + Notify-owner action
- **Backend `GET /api/v1/escrow-institutions`** now hydrates every item with `owner_account: {email, status, legal_name}` by looking up `account_id → escrow_accounts`. Legacy magic-link rows (no `account_id`) return the row without the owner key.
- **New `POST /api/v1/escrow-institutions/{iid}/notify-owner`** (admin/reviewer). Body: `{title, body, send_email}`. Writes an in-app notification (kind=`admin_message`) via `notify_account()` and optionally fires the email. Returns 400 for legacy drafts without an owner account.
- **Admin UI `AdminEscrowInstitutionsE.jsx`** — list rows now show `owner · <email> (<status>)` under the primary contact line. Detail panel gets a "Notify owner" button next to Approve/Clarify/Reject (hidden for legacy drafts).

### 2. Dashboard data wiring — real pending signatures + transactions
- **New `GET /api/v1/escrow-accounts/me/dashboard`** (session-authed). Resolves the signed-in account → institution → signatory emails → joint `escrow_accounts` the institution's officers operate → every `escrow_transactions` row on those accounts. Returns separate buckets `pending_signatures` (status in {received, awaiting_signatures} and institution has NOT signed) + `transactions` (all 200 most recent) + `joint_accounts` with balances.
- **`EscrowAccountDashboardBody.jsx`** rewritten to consume this payload: KPI tiles are now real counts, click-through routes to the matching tab. New responsive tables render pending transactions and joint-account cards; empty states tailored per institution status (submitted = "with review team", approved + 0 accounts = "waiting for PMC to open the first joint account").
- Sidebar tab labels get live badges when counts > 0.

### 3. Bank admin UI — review-and-merge for user_suggested banks
- **Backend admin endpoints under `/api/v1/masters/banks-admin/`:**
  - `GET /suggested` — lists `source=user_suggested` rows (oldest first).
  - `POST /{id}/approve` — promote to `source=curated`, optional swift_prefix / currencies / aliases enrichment; stamps `curated_by/curated_at`.
  - `POST /{id}/merge` — moves the suggestion's name into the target's aliases, deletes the source, writes an audit row to `masters_banks_merge_log`. Rejects cross-country merges with 422.
  - `DELETE /{id}` — hard-reject a user_suggested row (spam / wrong country); audited.
- **New admin page `AdminBankMasterE.jsx`** at `/admin/e/suggested-banks` (new sidebar entry "Suggested banks" under Masters). Left-column list of pending suggestions, right-column detail with editable swift_prefix / currencies / aliases, Approve / Reject buttons, and a same-country merge-target list with per-row "Merge into" buttons.
- `GET /api/v1/masters/banks` now returns the row's `_id` so the admin UI can key its rows (public /banks list was previously `_id`-stripped).

### Tests
- `backend/tests/test_v52e.py` — 6/6 green:
  - admin list enriches with owner_account ✓
  - notify-owner lands in bell + legacy draft returns 400 ✓
  - /me/dashboard returns all buckets with correct zero counts ✓
  - bank suggest → approve → curated + merge → aliased on target + reject → gone ✓
  - cross-country merge rejected 422 ✓

Backlog remaining: deployment of rev10 bundle (v52d + v52e combined).

### Deployment artifacts shipped (same session)
- `/app/frontend/public/downloads/pmc-backend-v52e.zip` — EB bundle (Dockerfile at ZIP root)
- `/app/frontend/public/downloads/pmc-frontend-v52e-prod-build.zip` — S3/CloudFront static assets
- `/app/frontend/public/downloads/DOWNLOAD_v52e.md` — release notes + deploy checklist + rollback


## v52f — Charts, signatory invites, PDF statements (15 Feb 2026)

### Features
- **Dashboard chart** — `/escrow/me` Overview tab now has a 12-month volume line + currency pie with an account picker (`EscrowDashboardChart.jsx`). Admin version with a multi-select institution filter on the admin pipeline page (`AdminEscrowChart.jsx`).
- **Signatory invites unlock post-approval** — new form on the Profile tab (disabled until status=approved); submit calls `POST /api/v1/escrow-accounts/me/signatories/invite` which appends to the institution's `signatories[]` and fires the password-claim email. 409 on duplicate email.
- **PDF statements** — Download / Download+email-me buttons on each joint account; backend `GET /me/joint-accounts/{aid}/statement.pdf?email_me=1` renders a reportlab PDF (branded header, transaction table, totals, footer) and optionally emails as attachment.

### Backend
- New router `routers/escrow_v52f.py` mounted as `/api/v1/escrow-accounts/me/*` (chart, signatories/invite, joint-accounts/*/statement.pdf) + admin router `/api/v1/escrow/admin/chart`.
- Shared `_month_series()` aggregator (buckets `escrow_transactions` by YYYY-MM × currency over configurable 3-24 month window).
- `_resolve_joint_account_ids(iid)` reused across chart and statement scopes.

### Tests
- `backend/tests/test_v52f.py` — 8 tests covering chart shape + clamp, invite 403 pre-approval, 200 + 409 post-approval, statement foreign-reject + PDF magic bytes, admin chart all + filtered.
- Cumulative suite (rev9 + v52d + v52e + v52f) — green.

### Deployment artifacts
- `/app/frontend/public/downloads/pmc-backend-v52f.zip`
- `/app/frontend/public/downloads/pmc-frontend-v52f-prod-build.zip`
- `/app/frontend/public/downloads/DOWNLOAD_v52f.md`

**Production migration note:** anyone mid-registration on the old magic-link flow needs to visit `/escrow/register` and start fresh (user explicitly chose "force everyone"). Admin-invited drafts (via `POST /admin-invite`) still resume through `/escrow/resume/:token` + legacy wizard — only the self-serve `/escrow/register` entry point moved.


## v52cz rev9 — Notice-routing 422 fix + dup escrow cleanup + bank "+" self-serve + signatories UI (14 Feb 2026)

- **P0 — HTTP 422 on Notice ↔ Escrow account routing (admin Escrow institutions page):** `PATCH /api/v1/notices/{ref}` reused the full `NoticeIn` model, so the routing picker PATCHing just `{escrow_account_id}` tripped 4× "Field required". New `NoticePatchIn` (all fields Optional, same validators) + `model_dump(exclude_unset=True)` → true partial update. Bonus fix: a PATCH that omits `is_published` no longer silently unpublishes.
- **P1 — duplicate open escrow transactions:** one-shot `scripts/cleanup_duplicate_escrow_tx.py` (dry-run by default, `--apply` keeps newest open row per bid and cancels extras with audit trail) AND a reusable "Cancel extras" button per duplicated bid in the EMD duplicates banner (`escrow-tx-dupe-cancel-<bid_ref>`, reuses the per-row cancel endpoint). Preview DB had 0 dupes (production-only data) — button ships for prod use.
- **Banks master:** root cause of "Revolut/Wise missing" — server.py only upserted `masters_banks` when the collection was EMPTY, so production's older roster never received rev7/rev8 additions. Bootstrap now upserts the full 146-row roster on every boot (idempotent). Preview verified: GB list has Revolut, Wise, Monzo, Starling.
- **"+ Add bank" self-serve:** banking-step autocomplete shows `+ Add "<typed>"` when no exact match → new PUBLIC `POST /api/v1/masters/banks` upserts tagged `source: user_suggested`, list refreshes, bank stays selected. Re-entry guard prevents double-toast. Tested by testing agent (iter 65).
- **Signatories step UI:** row grid `md:grid-cols-4 → md:grid-cols-2` (phone prefix input overflowed the card); `PhonePrefixInput` local input gets `min-w-0` for <400px viewports. Verified by testing agent: no overflow at 1280px.
- Tests: `tests/test_v52cz_rev9.py` 5/5 green (partial PATCH keeps title, sent-field validation still 422s, GB neobanks present, suggest-bank upsert idempotent + 422 on bad input). Testing agent iteration 65: 3/4 flows green, 1 N/A, both minor nits fixed (double-toast guard, mobile min-w-0). Bulk-apply toast not captured in agent's 5s window but per-row flow confirmed — same code path.
- **Prod deploy note:** backend redeploy auto-heals the bank roster on boot (no script run needed); the 409 screenshot was correct behaviour (one-open-tx-per-bid guard) — use the new Cancel extras button or the script to clear `BID-2026-TEST2` / `PMC-BID-2026-00048` extras.


## v52cz rev7 — ISD phone picker + Dup email guard + Bank roster expansion + In-page doc viewer (14 Feb 2026)

- New `PhonePrefixInput`: dial-code dropdown pre-selected from Core country (overrideable per field) + digits-only local input with ITU E.164 length validation. Used on Core Mobile/Office tel AND per-signatory Phone.
- `/register` 409s with structured detail when the primary email already belongs to any escrow institution (any status).
- `masters_banks` doubled (73 → 146) across 20+ countries incl. major neobanks (Monzo, Starling, Revolut, Wise, N26, Chime, SoFi, Mercury, Varo, Ally, Paytm/Jio/Airtel Payments…). Free-text fallback for unlisted banks retained.
- Document View now opens an in-page modal (iframe + Download + Close) instead of a bare browser tab.
- 11 targeted backend tests green (rev7+rev6). Release `pmc-*-v52cz-rev7*.zip` + `DOWNLOAD_v52cz_rev7.md`. Prod with existing rev6 masters_banks needs one idempotent run of `python scripts/seed_banks.py`.

## v52cz rev6 — Escrow Save-as-draft + Back + Bank picker + Doc-view fix (14 Feb 2026)

- Save-as-draft + Previous buttons on EVERY step; backend model relaxed (all optional on PATCH, submit still enforces mandatory set).
- Core: dual phones (mobile + office tel) ISD-prefixed via PhoneInput.
- Banking rewritten: Bank country typeahead → Bank autocomplete from new `masters_banks` (73 banks × 17 countries) → auto-fills SWIFT prefix + currency; cascading State/City from geography master; IBAN/SWIFT/IFSC/UK sort/US ABA live-regex validated; correspondent bank + correspondent SWIFT.
- Documents: new magic-token endpoint `/api/v1/escrow-institutions/{iid}/documents/{slot}/file?token=`; frontend View button uses it so anonymous (magic-link) registrants can view uploaded files — no more "Sign in to download tender documents".
- Bootstrap auto-seeds `masters_banks` on first boot; no SSH needed on prod.
- 14/14 targeted tests green. Release `pmc-*-v52cz-rev6*.zip` + `DOWNLOAD_v52cz_rev6.md`. Supersedes rev5.

## v52cz rev5 — Searchable geo pickers + blank-signatory 422 + prod geography auto-seed (14 Feb 2026)

- Country & State on escrow Core are typeable/searchable comboboxes; City is a 152k-row typeahead.
- Blank scaffold signatory/bank rows no longer 422 (`EmailStr` → Optional + `_clean_payload`); frontend strips them too.
- Prod "No states" root cause: bootstrap seeded geography only when countries was empty — prod had duplicated countries but zero states/cities. Bootstrap now checks all three collections + auto-seeds `masters_country_formats`. One backend restart repairs prod data.
- 9/9 targeted tests; preview E2E verified. Release: `pmc-*-v52cz-rev5*.zip` (supersedes rev4).

## v52cz rev4 — Escrow Core form validated against country masters (14 Feb 2026)

- `/escrow/register` Step 1 rewritten: country dropdown with flag + dial code, structured address (country→state→city→zip→addr1/2) backed by masters_countries/states/cities, REQUIRED pills on mandatory fields, country-aware reg-no / tax-id / VAT labels + examples + regex validation via new /masters/country-formats endpoint.
- 17 countries seeded with real local formats (CIN, PAN, GSTIN, BIN, UEN, Companies House, CNPJ, EIN…). Unknown countries fall back to free-text safely.
- 14/14 targeted backend tests green; preview UI verified end-to-end.
- Release: `pmc-*-v52cz-rev4*.zip` + `DOWNLOAD_v52cz_rev4.md`. Supersedes rev3. **Prod deploy must run `scripts/seed_country_formats.py` once.**

## v52cz rev3 — Documents tab data-driven + Download all above list (14 Feb 2026)

- E-theme notice detail Documents tab was hard-coded demo markup (5 fake rows, dead buttons); now rebuilt from live notice data — real rows, real count, working per-file public downloads, plus "↓ Download all (N)" above the list (pack zip, all real docs).
- Notice document uploads now tagged `scope: notice-attachments`; public-files endpoint accepts legacy `notice-docs/<ref>/` keys when parent notice is published.
- 16/16 backend regression; preview E2E verified (5-doc pack zip round-trip).
- Release: `pmc-*-v52cz-rev3*.zip` + `DOWNLOAD_v52cz_rev3.md`. Supersedes rev2. Awaiting user deploy.

## v52cz rev2 — Blank form regen + Bundle picker + Reg-doc CORS (14 Feb 2026)

- "Download Blank Form" now ALWAYS auto-generated from the live registration schema (sections A→E via RegistrationUpdateIn + DOC_SLOTS). Canonical filename `PMC-Vendor-Registration-Form.pdf`. Admin uploads to `vendor_templates` no longer surface to vendors → stray resume DOCX leak permanently prevented.
- Bundle picker on /vendor/bid/new: per-doc checkboxes (default checked), `N of M selected` counter, All/None shortcuts, `Download selected (N)` with disabled-at-0.
- Reg Doc View fixed: DocSlot (and NoticeDetail, NoticeDetailE, CorrigendaPanel, api.js template URLs) now use RELATIVE `/api/v1/...` paths so production bundles stop baking the preview host into cross-origin download URLs.
- Testing agent iter 64: 9/9 backend + 100% frontend. Preview-only — production bundles NOT built yet (awaiting user signoff).

## v52cz — Vendor download defects fixed (14 Feb 2026)

- NEW `POST /api/v1/uploads/bundle` — ZIPs any set of upload keys for signed-in admin OR vendor; README.txt manifest lists missing keys.
- Vendor bid submission now shows one `Download all (N)` button above uploaded docs (dynamic for any count).
- `Download pack` fixed on production: `NoticeDetailE` now uses relative `/api/v1/...` paths so axios baseURL resolves same-origin on prod (the old `${REACT_APP_BACKEND_URL}` prefix baked the preview host into prod bundles → CORS blocked).
- Empty-state Download pack now shows "No documents available for this tender" toast.
- Testing agent iter 62: 7/7 backend, 3/3 frontend. Not deployed to prod yet (user requested review first).



## v52cy rev6 — Bid "View" in-page modal (13 Oct 2026)

Popup-based viewing kept failing (async window.open blocked; blob:
navigation ignored; Safari quirks) even with rev5 deployed to prod.
openInNewTab now renders an in-page modal (embed for PDF/image/text,
direct download for Office/DWG). No popups. Verified on preview. Bundle
serves main.d0061103.js — frontend zip at the usual v52cy link.

## v52cy rev4/5 — Bid "View" after upload (13 Oct 2026)

`uploadsApi.openInNewTab` had two stacked bugs: async `window.open` (popup
blocked) and `popup.location.href = blobUrl` (silently ignored by Chromium).
Now opens a same-origin about:blank placeholder synchronously and writes an
`<embed src=blobUrl>` into it; office/DWG files download instead. Verified
e2e on preview (popup title + embed present). Frontend zip rebuilt.

## v52cy rev3 — Bid Submit copy matches expanded file types

Bid Submit tiles/messages said "PDFs are required" while v52cy allowed
PDF/DOC/XLS/PPT/JPG/DWG. Relabelled to "Technical/Commercial document" and
caption now lists allowed formats. Verified in built bundle. Frontend zip
rebuilt; backend unchanged.

## v52cy — seven-issue vendor-flow + bid-upload hardening (13 Oct 2026)

- Bid uploads restricted to pdf/doc(x)/xls(x)/ppt(x)/jpg/png/dwg (client enforced + caption).
- New public `GET /api/v1/notices/{ref}/pack` zips notice documents, no auth; NoticeDetailE Download pack now anonymous-safe.
- `registrationApi.update()` client-side whitelist strips extras → kills 422 "Extra inputs are not permitted".
- Prominent **REQUIRED** pills in `Field` + REQUIRED/OPTIONAL pills in `DocSlot`.
- New `NumericInput` keeps commas while typing (parses on blur) → fixes "comma blocked" complaint.
- Download blank form (already OK on preview) and all previous v52cu/v52cx backend changes bundled.
- Bundles: `pmc-frontend-v52cy-prod-build.zip` + `pmc-backend-v52cy.zip`. Supersedes v52cu/v52cv/v52cw/v52cx.

## v52cx — approval matrix edit/delete + escrow institution invite (13 Oct 2026)

- Backend: `DELETE /api/v1/masters/approval-matrices/{id}` (409 when a notice still uses it); admin-only `POST /api/v1/escrow-institutions/admin-invite` creates/reuses a draft record and emails the institution a magic-link resume URL — admin never enters third-party KYC.
- Frontend: `+ Invite institution` CTA + drawer on `AdminEscrowInstitutionsE.jsx` (email required, optional name/contact/message, corporate|personal radio); Edit + Delete per saved approval-matrix row with "editing" chip and Update/Cancel-edit affordance.
- Verified on preview: full matrix CRUD, invite dedupe (reused=true on 2nd call), email dispatch via existing Resend wrapper.

## v52cw — Download pack 401 fix (13 Oct 2026)

v52cv's pack button used native navigation, which drops the httpOnly auth
cookie on protected `/api/v1/uploads/files/*` URLs →
`{"detail":"Sign in to download tender documents"}`. Now fetches an
authenticated blob via the axios `api` instance (same pattern as
`downloadAuthedFile`) and saves with the server filename. Preview e2e
verified (admin → notice detail → download fires). Bundle:
`pmc-frontend-v52cw-prod-build.zip` — supersedes v52cv. Backend stays v52cu.

## v52cv — production E-theme fixes (13 Oct 2026)

Frontend-only hotfix bundle `pmc-frontend-v52cv-prod-build.zip`: (1) Tender
Builder page mounts the real AdminAvatarMenu (avatar/sign-out were dead
static placeholders); (2) EMD cell added to home cards + tenders list rows
(`emdText()` in pmcELiveData.js, "No EMD" for zero-EMD); (3) Notice detail
"Download pack" resolves a real URL — composed tender ZIP via
`/api/v1/tender-templates/{id}/public/zip?notice_ref=…` or primary document,
with a toast fallback when nothing is published. ZIP endpoint curl-verified
200. Backend stays at v52cu.

## v52cu — publish → landing page instantly (13 Oct 2026)

Public `GET /api/v1/notices` and `GET /api/v1/meta/public/stats` now return
`Cache-Control: no-store` so a notice appears on the landing page the moment
the admin hits Publish. curl-verified on preview; 7/7 notice tests pass.
Open follow-ups (offered, not requested): raise home-page limit=30 cap (a),
backfill null `published_at` so sort order is deterministic (b).

## v52cs — zero-EMD bids no longer stuck at "Supplier · Pay EMD" (13 Oct 2026)

Production incident: bid PMC-BID-2026-00047 — vendor finished all 5 wizard
steps (notice had EMD = 0), backend stored status="submitted", but the
admin Bidding-ops pipeline rendered it as "Step 1/6 · Supplier · Pay EMD ·
Waiting" forever and the escrow-agent transition could never fire (it
required prev_status="emd_paid", impossible when EMD is 0).

Fixes:
- `routers/bids.py::decide_bid` — escrow_agent accept now allowed from
  "submitted"/"emd_pending" when `emd_due_amount <= 0`. Guard preserved
  for EMD-due bids (tested: still 400).
- `pmcELiveData.js` Bidding-ops bucketing — zero-EMD submitted bids bucket
  to PMC side at Escrow stage ("Confirm receipt", Step 2/6) instead of
  supplier/"Pay EMD"; rows carry `data-emd` for the flow filter.
- `pmcELiveData.js` dashboard — zero-EMD bids no longer counted as
  "awaiting EMD"; pill reads "No EMD · awaiting escrow".
- `AdminBiddingOpsE.jsx` — detail panel `supplier` flag and the EMD/Escrow
  flow-step filter now respect zero-EMD bids.
- Regression: `tests/test_v52cs_zero_emd_pipeline.py` (2 cases, live API +
  direct Mongo fixture insert/cleanup).

Existing stuck bids (e.g. PMC-BID-2026-00047) self-heal on next page load
— no data migration needed; the escrow agent simply accepts to advance.

---


## v52cq deployment confirmed green on AWS Elastic Beanstalk (13 Oct 2026)

User confirmed: **"working now"** on AWS Elastic Beanstalk Docker AL2023 (`pmc-backend-prod`).
- Container listening on port 80 natively.
- Masters auto-seeding in background without blocking ELB health probes.
- Parameter Store and EB environment properties authenticated and working.
- Tender Builder → Notice creation bridge + bidder preview + master geography/UNSPSC live.

---


## v52cq rev 8 — REAL root cause found in EB logs (13 Oct 2026)

User's log paste revealed two definitive issues:

1. `/var/log/docker-events.log` showed EB AL2023 Docker platform executing
   healthchecks against a compose project:
   `com.docker.compose.project.config_files=/var/app/current/docker-compose.yml`
   → **EB was using MY docker-compose.yml**, which mapped host `8080:80`.
   Host port 80 had no listener → every ALB health check failed regardless
   of gunicorn state. My earlier note "EB ignores docker-compose.yml" was
   wrong for AL2023 (it runs Docker Compose natively). **Deleted
   docker-compose.yml** so EB generates its own single-container definition
   from the Dockerfile's `EXPOSE 80`.
2. Healthcheck `exec_die ... exitCode=127` → `curl` missing in the
   previously-running image (predates the Dockerfile). New image installs
   curl; HEALTHCHECK retained.
3. The 10:08 `ADMIN_PASSWORD` FATAL timestamps predate the user's 10:57 env
   apply — stale loop, not current state. Required prod keys are now just
   ADMIN_PASSWORD + OWNER_PASSWORD (staff fall back with a log line).

Bundle rebuilt (rev 8): no docker-compose.yml, Dockerfile unchanged from
the documented spec. pytest 15/15 green, /health 200 locally.



## v52cq rev 6 — SSM Parameter Store support (13 Oct 2026)

User's EB env-properties screenshot showed 4,286/4,096 bytes: big secrets
(DOCUSIGN_PRIVATE_KEY_B64 ~1.6 KB, VAPID keys, ZOOM ×3, Stripe ×2,
MONGO_URL, JWT_SECRET, PMC_SEED_PASSWORDS blob) cannot fit the plaintext
cap. Added `_load_ssm_parameters()` at the top of config.py: when
`PMC_SSM_PREFIX` is set (e.g. `/pmc/prod`), all parameters under that path
are fetched (WithDecryption, recursive) and injected into os.environ —
existing EB env vars take priority. boto3 already in requirements.
Verified via stubbed-boto3 unit test (injection + no-override + blob
parsing through SSM). Requires an inline IAM policy granting
ssm:GetParameter(s)(ByPath) on the prefix to the EB EC2 role
(aws-elasticbeanstalk-ec2-role). Full step-by-step in DOWNLOAD_v52cq.md.


## v52cq rev 5 — consolidated PMC_SEED_PASSWORDS for EB byte cap (13 Oct 2026)

User hit EB's 4,096-byte plaintext environment-properties limit when
adding the 7 seed-password keys. Fix: `config.py::_seed_password` now
falls back to a single consolidated `PMC_SEED_PASSWORDS` env var
(`KEY=value;KEY=value;…`) before the SEC-004 fatal. Individual keys still
win if both are set. Existing passwords are never overwritten (seed is
skip-if-exists — verified in server.py `_seed_admin`/`_seed_staff`), so
all current tester logins keep working.

Verified: full-blob test resolves owner + all 5 staff passwords; pytest
15/15 green; /health 200. Bundle rebuilt (rev 5) at the same URL.


## v52cq rev 4 — EB root cause CONFIRMED via logs (13 Oct 2026)

User pasted eb-engine.log: `[PMC-STARTUP-FATAL] Required environment
variable 'ADMIN_PASSWORD' is missing or empty` → gunicorn workers exit 1
in a loop → ALB 5xx. This is SEC-004 (v52cj) working as intended: the app
refuses to boot with built-in default passwords in any non-LOCAL_DEV env.

Resolution is EB-side config, NOT code: set ADMIN_PASSWORD, OWNER_PASSWORD
and STAFF_PW_{ESCROW,CERTIFIER,LEGAL,ACCOUNTS,COMMITTEE} under EB →
Configuration → Software → Environment properties, then Apply.

Changes made:
- server.py boot env dump now also reports ADMIN_PASSWORD / OWNER_PASSWORD /
  STAFF_PW_* key names (never values).
- DOWNLOAD_v52cq.md env checklist updated with the confirmed root cause
  and full required-keys table.
- DO NOT weaken config.py::_seed_password — the hardening was an explicit
  user-requested security fix.



## v52cq rev 4 — diagnostic + crash-fast (13 Oct 2026)

Rev 3 fixed the port 80 bind, but EB still showed "50.0 % 5xx" — exact-50 %
is the fingerprint of a mixed fleet (one new instance + one stale).

Rev 4 adds:
- Dockerfile: `--preload` + exec form (no sh wrapper), explicit access/error
  log flags + `--capture-output` so gunicorn stderr reaches EB container
  logs. Healthcheck 20s interval / 45s start-period.
- `.ebextensions/02-log-env-keys.config` sets `PMC_LOG_ENV_KEYS_ON_BOOT=1`.
- `server.py` _bootstrap_masters now dumps SET + MISSING env var NAMES
  (not values) at container boot so EB logs reveal config gaps.
- Release notes DOWNLOAD_v52cq.md rewritten with a step-by-step Rebuild +
  log-fetching plan.

Local verification unchanged: /health 200 in <2s, pytest 15/15 green.



## v52cq rev 3 — AL2023 Docker port 80 bind (13 Oct 2026)

User's second deploy went through (image built + container ran) but ELB
healthchecks failed, pushing env health → Severe. Root cause: AL2023
Docker platform does NOT run a host-side nginx reverse proxy (that was
an AL2 feature). The container must bind directly to the port the ELB
forwards traffic to.

Fix:
- Dockerfile — gunicorn now binds `0.0.0.0:80`, `EXPOSE 80`, healthcheck
  hits `http://localhost:80/health`.
- `.ebextensions/01-healthcheck.config` — ALB target group /health on
  port 80 with 15s interval, 2 healthy / 5 unhealthy thresholds.
- docker-compose.yml — local dev maps host 8080 → container 80.

Rev-3 bundle rebuilt and published at the same URL. Rev-3 release notes
rewritten with ELB health troubleshooting walkthrough.



## v52cq rev 2 — Docker deploy issues fixed (13 Oct 2026)

User's first deploy to AWS EB Docker-on-AL2023 failed with "Command failed
on all instances". Three root causes identified from the EB events panel
and the live backend inspection:

1. Shipped `Dockerrun.aws.json` had `"Image": {"Name": "local"}` which is
   not a valid pullable image name. For a Dockerfile build on EB, no
   Dockerrun is needed — removed it entirely.
2. Dockerfile HEALTHCHECK pointed at `/api/v1/health` (404). The real
   lightweight probe is `/health` (registered first in server.py). Fixed.
3. Startup event blocked for 2–3 minutes seeding 158k UNSPSC + 150k city
   rows synchronously → ALB target healthchecks timed out → rollback.
   Converted to `asyncio.create_task` background job that runs the sync
   PyMongo seed functions in a thread executor. FastAPI now answers HTTP
   in <2s regardless of seed progress; seed is still idempotent.
4. Added `.ebextensions/01-healthcheck.config` setting EB ALB health
   path to `/health` with 200 matcher.

Verified locally: `/health` 200 in <2s after restart, `/api/v1/masters/countries`
200 immediately. Pytest 15/15 still green.

Rev-2 bundle rebuilt as `pmc-backend-v52cq.zip` and release notes rewritten
with Docker-on-AL2023 troubleshooting guide.



## v52cq — Docker packaging added (13 Oct 2026)

User's AWS Elastic Beanstalk runs **Docker platform on Amazon Linux 2023**
and failed to deploy the previous v52cq zip with "Command failed on all
instances" + "Incorrect application version found". Root cause: zip was
missing Dockerfile / Dockerrun.aws.json / .dockerignore.

Added to `/app/backend/`:
- `Dockerfile` — python:3.11-slim, installs all native deps (weasyprint,
  pymongo, cryptography, etc.), runs `gunicorn -k uvicorn.workers.UvicornWorker
  server:app --bind 0.0.0.0:8001 --workers ${WEB_CONCURRENCY:-2}`. All env
  vars pulled from EB configuration (no baked-in .env).
- `.dockerignore` — keeps .env, .git, node_modules, tests, downloads, zip
  artifacts out of the image.
- `Dockerrun.aws.json` (AWSEBDockerrunVersion 1) — tells EB the container
  port is 8001 mapped to instance port 80.
- `docker-compose.yml` — optional local-dev convenience; EB ignores it.

Backend bundle rebuilt as `pmc-backend-v52cq.zip` (Docker files now
included); pytest 15/15 still green.



## v52cq — "Preview as bidder" for drafts + release bundles (13 Oct 2026)

- Admin → Notices: draft rows get a new amber **"Preview as bidder ↗"**
  button opening `/notices/{ref}?preview=1` which fetches via
  `GET /api/v1/notices/{ref}/admin` and renders a "DRAFT PREVIEW" banner.
  Published rows keep the original "Preview ↗" behaviour.
- Backend: no new endpoints — reuses the existing `/notices/{ref}/admin`.
- Downloadable release bundles produced:
  - `/downloads/pmc-backend-v52cq.zip` (~20 MB)
  - `/downloads/pmc-frontend-v52cq-prod-build.zip` (~3 MB)
  - `/downloads/DOWNLOAD_v52cq.md` (release notes + AWS deploy steps)



## v52cp iteration-60 verdict (13 Oct 2026)
- Testing agent iteration 60: **15/15 backend pytest** + **100% frontend acceptance**.
- Verified end-to-end via live preview:
  - (a) Empty-section tender save no longer 422s — toast "Saved" on real draft.
  - (b) Create-Notice from Tender Builder lands at top of viewport (scrollIntoView),
    deadline left blank, country / budget / currency / EMD all prefilled,
    primary document explicitly labelled OPTIONAL.
  - (c) Public /tenders/all register table renders EMD line under Est. Value
    for every notice with emd_config set.
- One minor backend adjustment by the testing agent: `_out()` in notices.py
  now always emits `emd_amount` key (nullable) for stable public shape.



## v52cp pytest status (13 Oct 2026)
- Backend regressions: 15/15 passing — 11 masters (v52cn) + 4 notice/tender bridge (v52cp).
- Live curl confirmed: /api/v1/notices returns `delivery_country` for every row and `emd_amount`+`emd_currency` for every row with an EMD config.
- Testing agent iteration dispatched for full UI validation.



## v52cp — Notice ↔ Tender Builder bridge fixes + public card polish (13 Oct 2026)

User reported from live use:
- "Sometimes 422 when saving a tender" — root cause: `SectionBlock` required
  non-empty `code` + `title`; adding a blank section before filling it in
  tripped Pydantic validation on the whole-template PATCH.
- Create-Notice from Tender Builder scrolled past the list, didn't carry
  country, forced an INR currency, forced a primary document upload, and
  hid the files already uploaded inside Tender Builder.
- Public landing (`/tenders/live`) card didn't surface EMD or country.

Fixes:
- **Backend `tender_templates.py`** — `SectionBlock.code` and `.title` now
  `Optional[str] = ""`; `TenderTemplateIn.name` defaults to "Untitled draft"
  instead of enforcing `min_length=2`. Auto-save no longer 422s.
- **TenderBuilderPanel `createNoticeFromDraft`**:
  - adds `delivery_country` from `header.country` / `doc.country`
  - drops `submission_deadline` from the prefill (user picks at publish)
  - uses the tender's `budget_currency` instead of hardcoded INR
  - packages every section attachment as `_tender_docs` so the Notice form
    can show them
- **NoticesPanel**:
  - new amber "Documents from the linked tender" panel at the top with
    per-section file list + View buttons + a shortcut back to Tender Builder
    for add / modify / delete
  - form `scrollIntoView` on prefill — no scrolling past the list anymore
  - primary document now **optional** (user can attach later via Edit)
- **Public `/tenders` list** — legacy card now shows EMD, EMD currency and
  country alongside Budget / Deadline / Category; register-table variant
  shows a small EMD line under the Est. Value cell.
- **Regression** — `backend/tests/test_v52cp_notices.py` (4 cases):
  blank section accepted, short placeholder name accepted, public notices
  expose `emd_amount` + `emd_currency` + `delivery_country`, notice create
  without primary doc succeeds.

---


## v52co — Section D UX fixes + Investor coverage overlay (13 Oct 2026)

User reported from screen recording:
- Section D "Business Categories" picker only showed a curated ~87-row list
  (per-country) — vendors from Bangladesh / Bosnia couldn't find biogas /
  solar / etc that Section C surfaces fine.
- "Kazakhstan Licenses Held" checklist block rendered for EVERY vendor
  regardless of country, which the user correctly flagged as wrong.

Fixes:
- **New `UnspscMultiPicker`** replaces the curated-categories picker in
  Section D. Debounced live search against `/api/v1/masters/unspsc/public/search`
  (full 158k codeset, same backend as Section C's Primary UNSPSC picker,
  including biogas/solar/CBG/STP synonym expansion). Picks accumulate as
  removable chips; stores `[{code, title}]` on the registration.
- **Backend model** — `Registration.business_categories` relaxed from
  `List[str]` to `List[Any]` so new `{code, title}` dicts coexist with
  legacy string entries. Picker normalises both on read.
- **KZ Licenses Held block gated** — now only renders when `reg.country === "KZ"`
  OR an operating region's `country_code === "KZ"`. For a Bangladesh vendor
  the block disappears entirely; country-specific uploads come from the
  dynamic `CountryLicenseSlots` instead.
- **Investor Showcase — Masters → Geography coverage overlay**: GeographyTab
  now fetches `listCountryLicenses()` and tags every country in the all-
  countries list with a green "N lic" chip + subtle emerald row background.
  Stats row grew to 4 tiles including "With licenses configured" so admins
  can see production-ready jurisdictions at a glance.

### Verified live
- `pytest tests/test_v52cn_masters.py` — still 11/11.
- Admin → New Vendor Section A country dropdown — 250 options confirmed earlier.
- Masters tabs still present; GeographyTab stats row now shows "licenses
  configured" counter.

---


## v52cn — Masters wired into vendor creation + admin CRUD (13 Oct 2026)

User Q: "if I add a company or a vendor, do I get the full list including UNSPSC
codes as dropdown and all countries / city / state / zip wired?"

Shipped on top of v52cm:
- **AdminVendorCreate / AdminVendorEdit** now fetch the full 250-country master
  (`mastersGeoApi.countries()`) so Section A's country `<select data-testid="f-country">`
  carries every ISO country instead of the 30-country CIS shortlist. Verified
  live: 250 options with India present. Legacy `/api/v1/meta/countries` kept
  only as a defensive fallback.
- **UnspscPicker** backing API switched to `/api/v1/masters/unspsc/public/search`
  so every usage site (vendor registration Section C, admin Product Catalog,
  admin BOQ Templates) now searches the full 158k UNSPSC codeset. Fallback to
  the legacy `/api/v1/taxonomy/search` kept if masters is empty.
- **Country-license upload prompts** — new `CountryLicenseSlots` block mounted
  in Section D below the KZ licenses. Pulls `/api/v1/masters/country-licenses/{cc}`
  for every country the vendor touches (`reg.country` + each office's
  `country_code`), rendering one `DocSlotsBlock` per country with slot keys
  shaped `country_license_{CC}_{code}` (e.g. `country_license_IN_gst`). Reuses
  the existing `DocSlot` upload pipeline, so authenticated blob
  view/download/delete all keep working.
- **Backend** — `routers/registrations.py :: upload_registration_doc` extended
  to accept any slot whose key starts with `country_license_`; genuinely unknown
  slots still 400 with `Unknown slot`. Covered by pytest.
- **Admin → Masters** got two new tabs:
  - **Country licenses** (`CountryLicensesTab`) — list seeded jurisdictions,
    inline add/edit/remove license rows (code / display name / mandatory flag),
    plus "Add country" picker backed by the 250-country master.
  - **Geography** (`GeographyTab`) — read-only paginated viewer with cascading
    country → state → city filters so admins can confirm coverage before
    rolling the portal out to a new jurisdiction.
- **Pytest regressions** — `backend/tests/test_v52cn_masters.py`, 11/11 passing
  against the live preview URL. Covers countries/states/cities masters, UNSPSC
  full-codeset + biogas synonym expansion + numeric prefix, country-licenses
  public GET + admin-only PUT, and the dynamic `country_license_*` slot
  whitelist (plus a regression for bogus slot rejection).
- **Testing agent** — iteration 58 confirmed every feature; the only HIGH
  issue it raised was f-country still being 30 options (caused by my first-
  pass `.then` chain swallowing the master response). Fixed and verified
  programmatically (`page.evaluate` → `count=250, has_IN=true`).

### Verified live
- `GET /api/v1/masters/countries` → 250 countries with `postal_code_regex`.
- `GET /api/v1/masters/unspsc/public/search?q=biogas` → methane / digester /
  anaerobic entries via synonym expansion.
- `GET /api/v1/masters/country-licenses/IN` → gst, pan, msme, esi, pf, shop_est.
- Admin → New Vendor → Section A `f-country` dropdown has 250 options.
- Section D RegionOfficeEditor cascades + CountryLicenseSlots renders per
  attached country.
- Admin Masters tabs `masters-tab-country_licenses` and `masters-tab-geography`
  mount, list seeded data, and update after Save.

---


## v52cm — Masters data pull: UNSPSC + geography + country licenses (12 Oct 2026)

User Qs (a) + (b): categories master was missing solar/biogas; operating regions
needed cascading country → state → city → zip dropdowns with license masters.

- **UNSPSC v26.0801 (158,464 rows)** imported from codebysaadbouh/unspsc-fr GitHub
  release into `masters_unspsc`. 4 levels, EN+FR titles, indexes on code/segment/
  level + text index on titles. `GET /api/v1/masters/unspsc/{search,public/search}`.
  Verified live: solar → 20 hits incl. 26131507 Solar power plants.
- **Geography** imported from dr5hn countries-states-cities-database:
  `masters_countries` 250 · `masters_states` 5,328 · `masters_cities` 152,021.
  Countries ship `postal_code_regex` so ZIP stays validated text (no 10M-row dropdown).
  `GET /api/v1/masters/{countries,states,cities}`.
- **masters_country_licenses** seeded for IN, KZ, AE, US, GB, SG (hand curated,
  admin editable via `PUT /api/v1/masters/country-licenses/{cc}`). Public GET for
  the registration portal.
- **Section D RegionOfficeEditor** rewired to cascading dropdowns: country →
  state → city search-as-you-type → zip regex-validated. Legacy string entries
  compatibility preserved.
- **Startup auto-seed** (`server.py::_bootstrap_masters`) runs the three seeds
  only when the collection is empty; production first boot ~90 s, subsequent
  boots unaffected. Data files baked into backend archive at `backend/data/`
  (unspsc 112 MB + csc 53 MB).

### Bundles
`pmc-backend-v52cm.zip` (~170 MB — includes master data), `pmc-frontend-v52cm-prod-build.zip`,
`DOWNLOAD_v52cm.md`.

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cl — Golden active sidebar tab (12 Oct 2026)

User: "left side bar when I chose a particular tab I need it to be the golden colour".
`pmc-theme-e.css`: active item (`.pmc-side__item--active` + `[aria-current="page"]`)
now uses a bright gold gradient (#e3b93b→#c9a227) with bold dark text, gold inner
edge bar and a soft gold glow ring — replacing the muted tan (#d9bd72) pill.
Verified live on Billing + Evaluation pages.

### Bundles
`pmc-frontend-v52cl-prod-build.zip`, `DOWNLOAD_v52cl.md`. Backend unchanged (v52ck).

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52ck — Stripe webhook health indicator on Billing (12 Oct 2026)

SEC-001 follow-up (user approved): admin can now see webhook health at a glance.

- `billing.py`: `GET /api/v1/billing/webhook-health` (admin-only) returns
  `{secret_configured, last_event_at, last_session_id, last_payment_status,
  events_24h}`. Both webhook handlers (`payments.py`, `billing.py`) record every
  signature-verified event into `db.webhook_events`.
- `BillingTransactionsPanel.jsx`: health card above the table — red when secret
  missing, amber when configured-but-no-events, green with last-event timestamp
  + 24h count. `api.js` gains `feeBillingApi.webhookHealth()`.
- Verified live: card renders red variant on preview (secret unset by design);
  endpoint 401 for anonymous.

### Bundles
`pmc-backend-v52ck.zip` (includes v52cj), `pmc-frontend-v52ck-prod-build.zip`
(includes v52ci), `DOWNLOAD_v52ck.md`.

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cj — Security Hardening Pack (SEC-001 → SEC-004) (12 Oct 2026)

Backend-only build that closes all four findings from the security audit.

- **SEC-001** `config.py` + `routers/payments.py` + `routers/billing.py` — both
  `/api/webhook/stripe` handlers now return 503 when `STRIPE_WEBHOOK_SECRET` is
  missing and pass `webhook_secret=` into `StripeCheckout.handle_webhook` so
  `stripe.Webhook.construct_event` verifies the signature. Verified live: forged
  POST → 503.
- **SEC-002** `routers/registrations.py::create_draft` — if an existing record
  is found for the submitted email, the response is a generic ack with no
  token/id/url; the resume link is emailed to the record's own address only.
  Verified live: second-call response has only `{ok, message}` keys.
- **SEC-003** `models/registration.py::RegistrationUpdateIn` → `extra="forbid"`;
  PATCH endpoint strips an expanded protected-field allowlist.
  Verified live: PATCH with unknown key → 422.
- **SEC-004** `config.py::_seed_password` — fallback literals only served when
  `LOCAL_DEV=1` is explicitly set. All other envs call `_require_env`, which
  fails hard at boot. Preview `.env` has `LOCAL_DEV=1` added so dev work
  continues; boot log emits CRITICAL per account on fallback.

### Open operational task
Android upload keystore `frontend/android/app/pmc-upload-key.keystore` is still
in git history. Needs `git filter-repo` + Play Store upload-key rotation —
destructive, awaiting user go-ahead.

### Bundles
`pmc-backend-v52cj.zip`, `DOWNLOAD_v52cj.md`. Frontend unchanged (stay on v52ci).

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52ci — Structured Operation Regions / Offices (12 Oct 2026)

User Q (h): regions needed per-office structured entry — name, address, country,
ZIP, city, state. Shipped as its own build.

- **Backend**: `models/registration.py` `operating_regions: List[str] → List[Any]`
  so the PATCH endpoint accepts both legacy strings and new office objects.
  `routers/vendors.py` KPI endpoint passes the field through unchanged.
- **Frontend new component** `RegionOfficeEditor.jsx` — per-office card with the
  six fields, country dropdown fed by `publicApi.countries()`, add/remove with
  required-field validation. Backwards-compat: legacy string entries show as a
  dismissible amber banner.
- **SectionD.jsx**: replaces the free-text input with `<RegionOfficeEditor />`.
- **VendorsPanel.jsx** (admin KPI): structured rows render as a card
  (name bold + address · city · state · zip · country), legacy strings keep the
  single-line form.

### Bundles
`pmc-frontend-v52ci-prod-build.zip`, `pmc-backend-v52ci.zip`, `DOWNLOAD_v52ci.md`.

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52ch — Sticky 3-col Registrations/Vendors + status pill (12 Oct 2026)

- **(g) Sticky 3-column layout** (first wave): `RegistrationsPanel.jsx` and
  `VendorsPanel.jsx` wrap both grid columns with
  `lg:sticky lg:top-6 lg:self-start lg:max-h-[calc(100vh-140px)] lg:overflow-y-auto`
  so each pane scrolls independently; clicking a row shows the detail right
  next to it instead of forcing the whole page to scroll.
  Still pending: Corrigenda, DocuSign, Billing, Audit if you want them next.
- **Enhancement — status pill**: `NoticesPanel.jsx` picker rows now show a
  `★ Master` (amber) or `✏ Draft` (navy soft) chip beside the EMD chip
  (`notice-tpl-status-<id>`).

### Bundles
`pmc-frontend-v52ch-prod-build.zip`, `DOWNLOAD_v52ch.md`. Backend unchanged.

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cg — Tender Builder country list cleanup (12 Oct 2026)

User Q (a): "in the tender maker country list can u show the country code and the country
name in the same list. also, there are a few companies where codes are full company names."

- `TenderBuilderPanel.jsx` — `masterCountries` now stores `{code, name}` from
  `publicApi.countries()` (filtered to `code <= 3` chars). `countries` memo merges
  with template-stored codes ONLY when `/^[A-Z0-9]{2,3}$/` matches — strips corrupt
  "full company name leaked into country" values.
- `TenderFilterBar.jsx` — option label is `${code} — ${name}` when name exists,
  else just `code`. Backwards compatible with string[] input.
- Verified live: all 30 countries render as "AE — United Arab Emirates" through
  "UZ — Uzbekistan", no 60+-char garbage entries.

### Bundles
`pmc-frontend-v52cg-prod-build.zip`, `DOWNLOAD_v52cg.md`. Backend unchanged (stay on v52cf).

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cf — Tender Builder follow-up quick-wins + picker badges (12 Oct 2026)

5 user-reported items closed in one batch; 3 more clarified for a later pass:

- **(b) Tender Builder "Your drafts"**: `tender_templates.py::list_templates`
  resolves admin ids → emails in one batched lookup; sidebar row shows
  "Created DD/MM/YYYY · by email" via new `tb-draft-meta-<id>` testid.
- **(c) Audit Ledger pager hidden**: `AuditPanel.jsx` — table moved into its own
  `overflow-x-auto` div so `{controls}` (page numbers) renders unclipped below.
- **(d) BOQ "View" no visible feedback**: `BOQTemplatesTab.jsx` — on every open
  the viewer flashes a 1.2 s amber `ring-4` + bold banner (`boq-viewer-flash`).
- **(f) Sidebar active state invisible**: `AdminSideNavE.jsx` auto-detects active
  from `window.location.pathname` (prop stays an override); `pmc-theme-e.css`
  swaps the subtle brass stripe for a solid `--brass-on-chrome` pill with bold
  on-brass text so every admin page highlights the right item.
- **(enhancement) EMD badge in Notices tender picker**: `NoticesPanel.jsx` adds
  an amber "EMD ₹ 50,000 · 2%" chip under each row (`notice-tpl-emd-<id>`).

Deferred with reason: **(g) sticky 3-column layouts** and **(h) structured
Operation Regions** are standalone tasks. Clarifications still owed by user:
**(a) country list — which page?**, **(e) exact escrow error**, **(i) which
registration + slot renders HTML on view**.

### Bundles
`pmc-frontend-v52cf-prod-build.zip`, `pmc-backend-v52cf.zip`, `DOWNLOAD_v52cf.md`.
Backend ships because `/api/v1/tender-templates` list now resolves emails.

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52ce — Tender picker EMD auto-fill (12 Oct 2026)

Follow-up to v52cd: `pickTemplate` in `NoticesPanel.jsx` now also pre-fills
`emd_config.fixed_amount` (`header.emd_amount`) and `emd_config.percentage`
(`header.emd_percentage`) when the picked tender carries them. All pre-filled
values stay editable. Verified live: EMD 50,000 → manual 75,000 retained.

### Bundles
`pmc-frontend-v52ce-prod-build.zip`, `DOWNLOAD_v52ce.md` (supersedes v52cd).
Backend unchanged (stay on v52bz).

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cd — Notices: searchable Tender Template picker with auto-fill (12 Oct 2026)

User request: the "Tender template (Tender Builder)" select in Notices → Create notice
needed full search (name / tender no / created date / tender value) and picking a tender
should auto-populate title, description and budget.

- `NoticesPanel.jsx`: plain `<select>` replaced with a search picker
  (`notice-tender-template` input + dropdown). Filters on name,
  `header.tender_reference_number`, created date (dd/mm/yyyy + ISO), and
  `header.tender_value` (comma-insensitive). Rows show ref · created · ₹ value ·
  section count. `pickTemplate` pre-fills title (`work_title`), description
  (`work_description`), budget (`tender_value`) and sets `tender_template_id`;
  `✕ clear` unlinks. No-match hint lists the searchable dimensions.

### Bundles
`pmc-frontend-v52cd-prod-build.zip`, `DOWNLOAD_v52cd.md`. Backend unchanged (stay on v52bz).

---


# PMC Managers v2 — PRD (last touched 12 Oct 2026)

## v52cc — Tender Builder clarity pack: fresh date schedule + order validation · docs-section relabel · Draft→Notice bridge (12 Oct 2026)

User Q&A on Tender Builder (answers given: docs section is a schedule/index not an
uploader; nothing is mandatory in Tender Builder itself; no Publish exists there by
design; Critical Dates were cloned verbatim from masters with no logic; Tender Builder
drafts live in tender-templates, never in Notices → Drafts). Approved fixes shipped:

- **Critical Dates**: `cloneMaster` stamps a fresh schedule anchored to today
  (publish=now, doc sale +0/+7d, clarification +0/+10d, submission +1/+21d,
  opening +22d). `save()` blocks out-of-order dates via `dateOrderError()` with a
  plain-English toast. Verified live: block fired on sub_end < sub_start.
- **Tender Documents**: group relabelled "…— schedule (bidders' checklist)" +
  hint banner (`th-docs-hint`) pointing to the real upload paths and the Save rule.
- **Mandatory markers**: Title / Work Description / Tender Value / Product Category /
  Bid Submission End Date now starred in `TenderHeaderForm`.
- **Draft → Notice bridge**: `tb-create-notice` button validates the starred fields
  (gate toast names what's missing), then sessionStorage-prefills
  NoticesPanel (`pmc.noticePrefill`) and navigates to `/admin/e/notices`. Verified:
  notice form opens with title, budget, deadline, INR currency + EMD prefilled.
  (Category stays a manual dropdown pick — master-backed select can't hold free text.)

### Bundles
`pmc-frontend-v52cc-prod-build.zip`, `DOWNLOAD_v52cc.md`. Backend unchanged (stay on v52bz).

---


# PMC Managers v2 — PRD (last touched 11 Oct 2026)

## Mobile v1.0.1 — Google Play bundle refreshed with v52cb web app (11 Oct 2026)

- Synced the v52cb production web build into `android/app/src/main/assets/public/`
  (manual asset sync — container Node is v20, Capacitor 8 CLI needs >=22; no plugin
  changes so asset-only sync is equivalent).
- `android/app/build.gradle`: versionCode 1→2, versionName 1.0.0→1.0.1 (Play
  requires incremented versionCode for updates). Signing config unchanged.
- Packaged `pmc-mobile-android-v1.0.1.tar.gz` (+ `DOWNLOAD_mobile_v1.0.1.md`) for
  local `.aab` build on the user's dev machine — no Android SDK in this container.

---


# PMC Managers v2 — PRD (last touched 11 Oct 2026)

## v52cb — Registrations card layout · Admin "Back to Registrations" · Evaluation tender picker (11 Oct 2026)

Three user-reported bugs closed in one frontend-only pass:

- **Registrations card misalignment** — "Edit sections (opens vendor view in new tab)"
  link visually attached to the *next* vendor because the row divider was on the inner
  button. `RegistrationsPanel.jsx` moves `border-b` to the row wrapper so each vendor
  card is one contiguous block. New testid `reg-card-<id>`.
- **Lost context after Edit sections** — the admin-opened new tab had no way back to
  Registrations (TopBar "Back" chip walked history and landed on the public homepage).
  `RegistrationResume.jsx` now renders "← BACK TO REGISTRATIONS" when `from=admin`;
  click triggers `window.close()` then falls back to `/admin/e/registrations`.
  New testid `reg-resume-back-admin`.
- **Evaluation tender lookup broken** — the Tender notice ref field was free-text,
  so typing "18" didn't surface `PMC-NOT-2026-0018`. `EvaluationPanel.jsx` now
  loads every notice via `adminApi.listAllNotices` and renders a real picker that
  filters live on ref AND title substring. Verified: typing "18" surfaces both
  `PMC-NOT-2026-0018` and `PMC-NOT-2026-0004` (title contains 18); picking locks
  the full ref. New testids `eval-notice-picker`, `eval-notice-opt-<ref>`,
  `eval-notice-nomatch`.

### Bundles
`pmc-frontend-v52cb-prod-build.zip`, `DOWNLOAD_v52cb.md`. Backend unchanged (stay on v52bz).

---


# PMC Managers v2 — PRD (last touched 11 Oct 2026)

## v52ca — Corrigenda second-search UX fix + withdraw dialog regression pass (11 Oct 2026)

User report: "two search bars … the second one is not working" (Admin → Corrigenda, lower
`corr-search-within` filter; symptom: nothing changes when typing).

**Investigation verdict:** the filter logic was functionally correct on current preview
(reproduced: no-match → 0 rows, number/title queries filtered correctly). It *looked* dead
because (a) the default-picked notice (a test draft) has zero corrigenda, so any query
changes nothing visible, and (b) the input gave zero feedback — no counter, no no-match
message, no explanation.

**Fixes (`CorrigendaPanel.jsx`):**
- Live feedback line under the second search: `N of M corrigenda match "q"` or amber
  no-match guidance (`corr-search-feedback`); zero-corrigenda hint when the picked notice
  has none (`corr-search-empty-hint`).
- `corrSearch` now resets when the notice picker changes (stale query can't hide rows).
- Withdraw dialog regression-tested end-to-end (v52bz's late patch had never been retested):
  opens, min-8-char validation, confirm withdraws, ACTIVE 3→2 / WITHDRAWN 1→2, reason shown.

### Bundles
`pmc-frontend-v52ca-prod-build.zip`, `DOWNLOAD_v52ca.md`. Backend unchanged (stay on v52bz).

---


# PMC Managers v2 — PRD (last touched 11 Oct 2026)

## v52bz — Evaluation rubric persistence · Scoring=0 auto-COI · Package redirect fix · shadcn Withdraw Dialog (11 Oct 2026)

Round-6 P1/P2 continuation after v52by:

- **#43 Rubric persistence**: `EvaluationPanel` now calls `evalApi.getRubric(noticeRef)` on notice pick and hydrates the editor from the persisted doc. Weights survive refresh.
- **#44 Scoring = 0**: root cause was the 400 "declare COI first" block. `submitTechScore` now catches it, auto-declares `no_conflict`, retries the save. Clear toast surface.
- **#32 Work Packages redirect**: PmcLinkPatcher's intercept pattern tightened to exclude `|package` so the New Package button is no longer hijacked.
- **Withdraw Dialog**: `CorrigendaPanel` swaps `window.prompt()` for shadcn `Dialog + textarea` with character counter and testids `corr-withdraw-dialog`, `corr-withdraw-reason-input`, `corr-withdraw-confirm`. Unblocks QA automation.
- **Dead code**: `LiveAuctionsPanel.jsx` annotated as legacy; `AdminAuctionsE.jsx` is the canonical live surface. File kept for the AdminDashboard tab route; deferred deletion to avoid regressions.

### Bundles
`pmc-backend-v52bz.zip`, `pmc-frontend-v52bz-prod-build.zip`, `DOWNLOAD_v52bz.md`.

---


## v52by — Reverse Auction create/start · BOQ Excel+PDF export · Corrigendum withdraw refresh (11 Oct 2026)

### Mid-release correction baked in
After the first cut, the testing agent surfaced that the **actually-mounted** admin
Reverse Auctions panel is `admin-console-e/AdminAuctionsE.jsx`, not the sibling
`LiveAuctionsPanel.jsx` that was edited first. The real root cause of #64 was in
`AdminAuctionsE.create()`: it POSTed a `bid_decrement` field, but the backend's
`ReverseAuctionIn` model expects `min_decrement` — producing the silent "field
required" 422 the user saw. Fixed in the right file + optimistic prepend applied
there too + Start button shows live `participant_count/2` + no longer hard-disables.

Round-6 P0/P1/P2 continuation after v52bx:

### Round-6 #64/#59/#60 — Reverse Auction
- `backend/routers/auction_live.py`: `ReverseAuctionIn.floor_price` defaults
  to 0.0, `min_decrement` to 1.0 (removes silent "field required" 422).
- `frontend/.../LiveAuctionsPanel.jsx`: `create()` coerces every numeric to
  Number(), inline toasts validate ranges, new draft is optimistically
  prepended to `items`. Start button is no longer client-disabled — the
  backend already returns a clear 400 naming the gate.

### Round-6 #48/#57 — BOQ export
- `backend/routers/boqs.py`: new `GET /boq/templates/{id}/export.xlsx`
  (openpyxl) and `.pdf` (WeasyPrint). Audit-logged.
- `frontend/src/lib/api.js`: `boqApi.exportXlsx/exportPdf` use
  `downloadAuthedFile` blob pattern.
- `BOQTemplatesTab.jsx`: two new buttons per row (`boq-export-xlsx-<id>`,
  `boq-export-pdf-<id>`).

### Round-6 #49 — Corrigendum withdraw refresh
`CorrigendaPanel.withdraw()` now does an optimistic local state flip
(`is_active: false`) before the refetch, so the withdrawn row leaves the
active table instantly — fixes "withdrawn corrigenda still show as
active" without touching the backend.

### Bundles
`pmc-backend-v52by.zip`, `pmc-frontend-v52by-prod-build.zip`,
`DOWNLOAD_v52by.md`.

### Still queued (Round-6 remainders)
#32 Work Packages redirect · #41 Escrow error (need repro) · #43 Rubric
save · #44 Scoring=0 · #46 UX corrigenda search (closed in v52bx) · #58
Product disable (need repro) · Vendor chrome wrap on
`/vendor/categories` and `/vendor/services`.

---


## v52bx — Round-6 session security + vendor reverse-auction visibility (11 Oct 2026)

Round-6 Report scope fixes landed in v52bx:
- **#34 Session cross-contamination** — admin/staff/vendor login endpoints
  now delete the OTHER role's cookie on successful login
  (`backend/routers/{admin_auth,staff_auth,vendor_auth}.py`). Two accounts
  on the same browser can no longer mix permissions.
- **#46 Corrigenda search bars** — distinct aria-label + testids
  (`corr-search-notice` for the global notice picker,
  `corr-search-within` for the active-notice filter).
- **User follow-up (reverse auction invites)** — new endpoint
  `GET /api/v1/reverse-auctions/mine` (vendor-auth, bid-notice OR
  explicit invite rows), new vendor page `/vendor/auctions`
  (`VendorAuctionsE.jsx`), new KPI tile `vhome-kpi-auctions` on
  `VendorHomeE.jsx`.
- **VendorCategories back button** — navigates to `/vendor` via
  `useNavigate` (replaces fragile `window.history.back()`).

### Explicitly out-of-scope for v52bx (queued next)
#43 rubric save · #44 scoring=0 · #48/#57 BOQ export · #49 corrigendum
withdraw refresh · #58 product disable · #59/#60/#64 reverse auction
create/start · #41 escrow error · vendor chrome wrap on
`/vendor/categories` and `/vendor/services`.

### Bundles
`pmc-backend-v52bx.zip`, `pmc-frontend-v52bx-prod-build.zip`,
`DOWNLOAD_v52bx.md`, plus `BUG_TRACKER_R6.md` (consolidated Round-6
tracker).

---


## v52bw — DocuSign vendor sync (both gates removed) · Resend graceful v2 · Escrow CSS · BOQ View/Contract reveal · Tender search promoted (11 Oct 2026)

### 1. DocuSign vendor sync — the "two conditions"
Previously the vendor's bid stayed on "submitted / pending" after admin
signed because `_apply_live_status` required BOTH (a) a webhook/poll to
detect the change AND (b) `bid_id` to already be present on the envelope
row. Fixes:
- Fallback resolution: `award_ref → awards.bid_id` then `bid_ref → bids._id`.
- New `POST /api/v1/docusign/envelopes/{id}/refresh` so admin console can
  force a status pull right after signing/dispatching (frontend
  `docusignApi.refresh`).

### 2. DocuSign resend — UNKNOWN_ENVELOPE_RECIPIENT
Previous catch only handled ENVELOPE_DOES_NOT_EXIST. User screenshot
showed UNKNOWN_ENVELOPE_RECIPIENT 400 surfacing a raw trace. Now caught
too → HTTP 410 + orphan flag.

### 3. Escrow / EMD signer-row CSS
Added `min-w-0 break-all` to the grid cells so long emails wrap inside
their column instead of overlapping the next one.

### 4. BOQ View scroll-into-view + Close
`BOQTemplatesTab` adds `viewerRef` + `useEffect(scrollIntoView)` and a
Close button (`boq-viewer-close`).

### 5. BOQ Contract reveal after create
`createContract` now awaits create → toast with contract_ref → awaits
reload → scrolls the new row into view.

### 6. Tender Builder search promoted
Second matching-drafts banner (`tb-search-results-main`) at the top of
the main pane when any filter is active.

### Bundles
- `pmc-backend-v52bw.zip`, `pmc-frontend-v52bw-prod-build.zip`, `DOWNLOAD_v52bw.md`.

---


## v52bv — Services back button · "Service quotes" KPI tile · PmcMobileNav 401-redirect fix (11 Oct 2026)

User requests: Services page missing a back button; service quote requests
should surface as a separate counter on the vendor landing page.

### 1. Back button on /vendor/services
`VendorPurchase.jsx` rewritten: back button (`data-testid="services-back-btn"`)
above the grid. Signed-in vendors → "Back to supplier portal" (/vendor);
anonymous visitors → "Back to home" (/). Vendor detection probe uses
`_skipAuthRedirect: true` so anonymous users are never bounced to /login.

### 2. "Service quotes" KPI tile on vendor home
- Backend: new vendor-scoped `GET /api/v1/engagements/mine` (registered
  ABOVE `/{eid}` to avoid FastAPI route shadowing — same class as the
  /bids/mine bug).
- Frontend: `VendorHomeE.jsx` fetches `engagementsApi.mine()` and renders a
  5th KPI tile (`data-testid="vhome-kpi-services"`, briefcase icon) counting
  engagements in `quote_requested / quoted / invoiced`; links to
  /vendor/services.

### 3. Global bug found & fixed during verification
`PmcMobileNav.jsx` (mounted on every page) called `vendorApi.me()` without
`_skipAuthRedirect`, so its 401 tripped the global axios interceptor and
force-redirected ANY unauthenticated visitor on /vendor/* (including the
public /vendor/services page) to /login. Fixed by using the flagged probe.

### Testing
- iteration_52.json: backend 5/5, authed frontend 5/5; unauth leg failed →
  PmcMobileNav root cause found & fixed.
- Retest: unauth /vendor/services renders grid + "Back to home" → `/` ✓
  (self-tested via screenshot; testing-agent retest running).

### Bundles
- `pmc-backend-v52bv.zip`, `pmc-frontend-v52bv-prod-build.zip`, `DOWNLOAD_v52bv.md`.

---


# PMC Managers v2 — PRD (last touched 11 Oct 2026)

## v52bu — Vendor Signatures live sync · EMD receipt PDF · Vendor sidebar Categories/Services (11 Oct 2026)

User follow-up features after v52bt. All 3 verified fixed (test_reports/iteration_51.json, backend 5/5 pytest, frontend 4/4 live).

### 1. Vendor Signatures Sync
`VendorSignaturesE.jsx` statusPill now maps DocuSign `signed` (partial — admin
signed, vendor pending) to a yellow "Admin signed · your turn" pill with a
working **Review & sign** CTA. Page now polls envelopes every 20 s and on
window-focus, so the badge appears live after admin dispatch.

### 2. EMD Payment History (per-bid receipt PDF)
- Backend: new `GET /api/v1/payments/emd/bid/{bid_id}/receipt.pdf`
  (vendor-auth, Weasyprint). Returns a 1-page A4 receipt with vendor, bid,
  notice, amount, payment reference and date. 401 unauth / 404 if no paid tx.
- Frontend: `useVendorEmdLive` rewrites the right-most cell of every paid
  deposit row into **"Receipt (PDF)"** (`data-testid=vemd-receipt-<bid_ref>`),
  authenticated blob download via `paymentApi.receiptPdf`. Click handler in
  `PmcLinkPatcher.jsx` reads `data-vemd-receipt-bid`.

### 3. Vendor sidebar Categories & Services
`VendorEmdE.jsx` and `VendorAlertsE.jsx` had hard-coded `<nav class="pmc-lnav">`
menus missing **Categories** (`i-tag`) and **Services** (`i-briefcase`).
Those links are now inserted after Company & KYC, matching the shared
`VendorPortalChrome` layout — sidebar identical on every vendor page.

### Bundles
- `pmc-backend-v52bu.zip`, `pmc-frontend-v52bu-prod-build.zip`, `DOWNLOAD_v52bu.md`.

### Known gap (out-of-scope improvement for next pass)
`/vendor/categories` and `/vendor/services` pages don't themselves render
`VendorPortalChrome`'s left nav — they use a different legacy chrome. Not in
scope for v52bu (user asked only about VendorEmdE / Vendors page).

---


## v52bt — Admin sidebar unified · Vendor EMD filters & Pay · DocuSign resend graceful · Edit-signers contrast (11 Oct 2026)

Reported bugs batch after v52bs. All 7 verified fixed (test_reports/iteration_50.json, 100% pass).

### 1. Admin sidebar inconsistency (highest impact)
Six pages (`AdminDashboardE`, `AdminProgrammeE`, `AdminTenderBuilderE`,
`AdminBiddingOpsE`, `AdminVendorKycE`, `AdminEvaluationListE`) had hard-coded
inline sidebar HTML with the old short item list. Clicking any item on those
pages → the next page used `AdminEShell` which had the full 27-item list,
making the sidebar appear to "grow" on second navigation (user: "Market
section only shows 4 items … Masters and others below do not open on the
first attempt").
**Fix:** new shared `apps/admin-console-e/AdminSideNavE.jsx` (single source of
truth). `AdminEShell` + the six pages now all render it. Verified 27 nav
links on 9 admin pages.

### 2. EMD & Payment (vendor `/vendor/emd`)
- "All statuses" / "All currencies" dropdowns were dead JSX selects with one
  option each → **populated from rendered rows** with real distinct values
  (`vemd-status-filter`, `vemd-currency-filter`), with live row filtering
  via `data-vemd-status / data-vemd-currency` on each row.
- Top "Pay EMD" button → `useVendorEmdLive` now stamps `data-bid-ref` +
  `data-bid-id` on hydrated rows so `PmcLinkPatcher.handlePayEmd` resolves
  the exact bid. Verified: button opens a real `checkout.stripe.com` session.

### 3. Admin Escrow / EMD "Edit signers" opacity
`EscrowAccountsSection.jsx` button was ghost-outline → now solid
`bg-brand-navy text-white` primary; computed opacity 1.

### 4. DocuSign resend graceful (user screenshot — ENVELOPE_DOES_NOT_EXIST 404)
`routers/docusign.py :resend_envelope` now catches upstream
`ENVELOPE_DOES_NOT_EXIST` (and "no rights to it"), marks the local row
`status: "orphaned"` with `orphaned_at` + `orphan_reason`, and returns
**HTTP 410** with detail "different DocuSign sandbox — use Reassign".
No more raw stack traces in the admin toast.

### 5. DocuSign vendor status sync
`_apply_live_status` now mirrors **every** envelope transition
(sent / delivered / signed / completed — not only completion) onto
`db.bids` (`docusign_status`, `<sub_kind>_docusign_status`,
`docusign_updated_at`) and `db.awards`. Vendor UI no longer stays on
"submitted / pending" after admin signs.

### 6. Work packages sample CSV
Verified: `pkg-import-sample` button uses `downloadAuthedFile` →
`pmc-work-packages-sample.csv`, header
`title,category,phase,value,currency,float_target_date,status`.

### Testing
- Backend pytest: 6/6 pass (`backend/tests/test_v52bt.py` + xml).
- Frontend E2E: 7/7 feature checks pass.
- Report: `test_reports/iteration_50.json`.

### Bundles
- `pmc-backend-v52bt.zip` (EB-ready: Dockerfile + Dockerrun.aws.json +
  `.platform/` + `backend/` at archive root).
- `pmc-frontend-v52bt-prod-build.zip` (S3 + CloudFront invalidate `/*`).
- `DOWNLOAD_v52bt.md`.

### Known preview-env caveat (not a bug)
DocuSign JWT keys in preview are rejected (`invalid_grant`) so the orphan
410 path can't be live-exercised; the code is correct per spec, and the
resend endpoint still fails gracefully (424 with readable detail, no
traceback). Verified on a prod-equivalent run via the testing agent.

---


## v52bs — Stakeholder CSV network error + Tender Builder industry master + BOQ inline editor (10 Oct 2026)

Backend
- `routers/boqs.py` — new `PATCH /api/v1/boq/templates/{id}` (admin). Updates
  `items / name / currency / unspsc_code / unspsc_title`. Server validates
  rows (description required, qty/rate numeric ≥ 0), auto-renumbers `sl_no`,
  trims strings, keeps `unspsc_code` + `unspsc_title` + `remarks`, audit
  log `boq_template.update`.

Frontend
- `lib/api.js`:
  - `stakeholderReportsApi.csvUrl` now returns a PATH ONLY. Full URLs caused
    axios to call the preview backend origin from a production page →
    "Network Error" (CORS). Path-only lets axios reuse the baseURL +
    attached Bearer token, so it's same-origin on both envs.
  - `boqApi.updateTemplate(id, patch)` wired.
- `apps/admin-console/boq/BOQTemplatesTab.jsx` — full rewrite of the viewer:
  Add / Edit / Delete line items inline; Description * / Unit / Qty / Rate /
  live Line Total; **UNSPSC picker** (master-backed) per row; empty state
  ("No line items yet…") instead of fake "1-5 of 5" pager; all actions
  persist via the new PATCH endpoint and refresh the viewer + the list card.
- `apps/admin-console/TenderBuilderPanel.jsx` — Industry dropdown now sourced
  from the **Categories master** (`mastersApi.listCategoriesPublic`) unioned
  with template-derived strings. Selecting "Public Works / Construction /
  PMC" now actually filters masters + drafts.

Verified via Playwright:
- Stakeholder CSV: 200 `text/csv`, 2.9 KB downloaded (`stakeholder-tenders.csv`).
- Tender Builder industry options include master categories (full taxonomy).
- BOQ viewer: empty state visible before add; after adding
  "Concrete M30 — 150 m³ × 12,000", rows render and persist (sl_no 1).

Bundles: `pmc-frontend-v52bs-prod-build.zip` + `pmc-backend-v52bs.zip`
(backend changed — redeploy EB).

---



## v52br — Stakeholder CSV 401 + Work Packages sample CSV 401 + Tender Builder promoted matches (10 Oct 2026)

Same root-cause class as the tender PDF bug: admin-gated download links were
raw `<a href target="_blank">` navigations that drop the Bearer token → new
tab showed `{"detail":"Not authenticated"}`.

Frontend (backend unchanged from v52bp):
- `lib/api.js` — new shared helper `downloadAuthedFile(path, filename)`:
  axios `responseType: "blob"` → Blob → `a.download` click.
- `admin-console-e/AdminStakeholderReportsE.jsx` — Download CSV now uses the
  helper (downloads `stakeholder-<tab>.csv`). Verified: `stakeholder-tenders.csv`,
  2,933 bytes.
- `admin-console/PackagesPanel.jsx` — Sample CSV now uses the helper
  (verified: `pmc-work-packages-sample.csv`, 300 bytes, header
  `title,category,phase,value,currency,float_target_date,status`).
- `admin-console/TenderBuilderPanel.jsx` — when search/country/industry is
  active, a **Matches** panel renders directly under the filter bar (above
  Kind picker + Master Library) with clickable results that open the draft.
  Verified: hidden at rest, 4 rows on "Standard", click opens draft.

Bundle: `pmc-frontend-v52br-prod-build.zip` (3.0 MB). Backend: keep v52bp.

---



## v52bq — Tender Builder DOWNLOAD PDF 401 fix (10 Oct 2026)

Bug: Tender Builder → DOWNLOAD PDF opened a raw browser tab to
`GET /api/v1/tender-templates/<id>/export/pdf` (admin-only). Browser
navigations don't carry the Bearer token → new tab showed
`{"detail":"Not authenticated"}`.

Fix (`apps/admin-console/tender/tenderPdf.js`): `exportTenderPdf(..., {download:true})`
now fetches via the authenticated axios `api` client (`responseType: "blob"`),
wraps the result in a Blob and triggers a real download
(`<tender-name>_<lang>.pdf`); failures toast instead of dead-ending in a
JSON tab. Added `import { api } from "@/lib/api"` + `import { toast } from
"sonner"`. PRINT / PDF stays client-side (iframe + window.print).

Verified via Playwright: export endpoint returns 200 `application/pdf`,
browser download fired (`Standard_PSU_e-Tender_…_en.pdf`, 30,864 bytes).

Bundle: `pmc-frontend-v52bq-prod-build.zip` (frontend-only; backend stays v52bp).

---



## v52bp addendum — Tender Builder filters fixed end-to-end (10 Oct 2026)

User confirmed the filters "exist but don't filter anything". Root causes found
via Playwright E2E:
- `applyTenderFilters` was applied ONLY to drafts; the Master Library received
  the raw list, so country/industry/search/sort looked dead on masters.
- The Country dropdown was derived only from the loaded templates' own country
  values — most preview templates have none, so the dropdown rendered just
  "All countries" and felt broken.

Fix (`admin-console/TenderBuilderPanel.jsx`):
- `filteredMasters = applyTenderFilters(masters, filters)` — same filters drive
  both lists; `TenderSidebar` now receives `filteredMasters`.
- Country options = union of template-derived values + the country master
  (`publicApi.countries()`), so the dropdown always carries the full ISO list
  (31 options in preview).

Verified via Playwright: country=UZ → masters 1→0, drafts 5→0; search
"Standard PSU" → masters 1, drafts 4; name-asc sort verified ordered.
Public notice page also gained the visible "📄 Download diff PDF" button per
corrigendum (v52bp edit that initially failed string-match, now applied).

Bundle: `pmc-frontend-v52bp-prod-build.zip` rebuilt with all fixes.

---



## v52bp — Public corrigendum PDF + vendor-bell deep link (10 Oct 2026)

Backend
- `routers/corrigenda.py`:
  - `attach_corrigendum_file` → uploads row now carries `scope=corrigendum-attachments`,
    `notice_ref`, `corrigendum_id`, both `bytes_b64` and `data_b64` (matches
    `_serve_file` reader). Attachment URL served through the PUBLIC path
    `/api/v1/uploads/public-files/<key>` so bidders no longer 401.
  - `publish_corrigendum` → in addition to email + push, now inserts a
    vendor-bell `notifications` record for every active bidder with
    `related_type=corrigendum`, `related_id=<cid>`,
    `related_url=/api/v1/notices/<ref>/corrigenda/<cid>/pdf`,
    `related_notice_ref=<ref>` so the vendor bell can deep-link to the PDF.
- `routers/uploads.py`:
  - `get_public_file` allow-list extended with `corrigendum-attachments`.

Frontend
- `apps/vendor-portal/VendorNotificationBell.jsx` — corrigendum alerts now
  render **📄 Open PDF** (new tab, auto-marks read) and **View notice**
  buttons using `related_url` + `related_notice_ref`.
- `apps/admin-console/CorrigendaPanel.jsx` — every active row shows a
  **📄 Download diff PDF** button hitting the public PDF endpoint.
- `apps/notice-board-e/NoticeDetailE.jsx` — same button in the public
  Corrigenda & amendments section (brass pill).

Bundle: `pmc-frontend-v52bp-prod-build.zip` + `pmc-backend-v52bp.zip`.

---



## v52bo — EMD zero allowed · Stakeholder reports sidebar · Live corrigendum pill · Corrigendum PDF email (10 Oct 2026)

Backend
- `routers/notices.py` — removed the "EMD must be positive" validation.
  Budget-amount>0 remains the only money validation on create. EMD = 0 is
  valid for walk-in tenders / free RFQs / pre-qualifications.
- `routers/corrigenda.py`:
  - `publish_corrigendum` now (a) builds a one-page diff PDF using
    `reportlab` via new helper `routers/corrigenda_pdf.py`, (b) fans the PDF
    out to every active bidder (`db.bids` non-withdrawn) via Resend as an
    email attachment, (c) stamps `pdf_generated_at` on the corrigendum doc,
    (d) logs the fan-out size.
  - New public endpoint `GET /{notice_ref}/corrigenda/{cid}/pdf` returns the
    same one-page diff PDF for in-browser download / inline view.
  - Added `import config` (fixes undefined name after email block).
- `routers/corrigenda_pdf.py` (NEW) — A4, PMC chrome, title, effective date,
  overall change description, Field/Before/After/Reason table (red/green
  colour-coded cells), deadline change, attachment names, audit footer.
- `emails.py` — `send_email()` now accepts an optional `attachments` list
  (`{filename, content_b64, content_type}`) forwarded to Resend.

Frontend
- `apps/admin-console/NoticesPanel.jsx` — removed client-side EMD>0 guard.
- `lib/pmcELiveData.js` — `useNoticeDetailLive` now patches the hero
  `pmc-pill--info` corrigendum chip from the latest active corrigendum in
  the live record (`effective_from || published_at`); hides the chip when
  no active corrigenda exist. Removes the stale demo "Corrigendum 1 · 26 Sep".
- `apps/admin-console-e/Admin{BiddingOps,VendorKyc,TenderBuilder,Programme,
  EvaluationList,Dashboard}E.jsx` — added the "Stakeholder reports" sidebar
  entry (was missing on Bidding Ops and 5 other E-pages).

Bundle
- Frontend: `pmc-frontend-v52bo-prod-build.zip` (3.0 MB)
- Backend: `pmc-backend-v52bo.zip` (EB-ready root layout)

---



## v52bn — Public corrigendum diff + live-notice Edit → Corrigendum flow (10 Oct 2026)

User-approved regulated-procurement flow: everything on a LIVE notice (fields
AND attachments) changes only via a versioned corrigendum; public page shows
date only (author emails stay internal).

Frontend (backend unchanged from v52bl):
- `notice-board-e/NoticeDetailE.jsx` — new React section **Corrigenda &
  amendments** on the public page: per corrigendum → No., date
  (`effective_from || published_at`), title, overall description, deadline
  callout, full **Field/Before/After/Reason** table, attachments. Fetched via
  `corrigendaApi.listPublic(ref)`. The static "Corrigenda" tab now shows the
  live count and smooth-scrolls to the section.
- `notice-board/NoticeDetail.jsx` — legacy banner upgraded with the same diff
  table + date (no author).
- `admin-console/NoticesPanel.jsx` — per-row **Edit** is context-aware:
  Draft → inline edit modal (unchanged); Live → `navigate(/admin/e/corrigenda?notice=<ref>)`
  with label "Edit ▸ Corrigendum".
- `admin-console/CorrigendaPanel.jsx` — honours `?notice=` deep-link
  (preselect + auto-open form); after publish redirects to `/notices/<ref>`;
  per-row **Attach document** upload (`corrigendaApi.attach` → existing
  backend endpoint) + attachment chips. Fixed stale-closure race where the
  default notice pick clobbered the `?notice=` preselect (functional setState).
- `admin-console/notice/NoticeEditModal.jsx` — safety net: live notices render
  a locked banner + "Open Corrigendum workspace" instead of the editable form.
- `admin-console/notice/NoticeViewModal.jsx` — on live notices, document
  Delete is replaced by a "Locked" chip + hint; draft behaviour unchanged.
- `lib/api.js` — `corrigendaApi.attach(ref, cid, file)` (multipart).

Verified via Playwright + curl:
- Public `/notices/PMC-NOT-2026-0020` shows corrigenda section; Corrigendum 4
  diff table renders both rows; date shown; no author email.
- Admin Notices → Edit (live) → lands on `/admin/e/corrigenda?notice=…0020`,
  form open, picker preselected to PMC-NOT-2026-0020, 14 field rows with
  current values.

Bundle: `pmc-frontend-v52bn-prod-build.zip` (3.0 MB). Backend: keep v52bl.

---



## v52bm — Rich Corrigendum form + bundle regeneration (10 Oct 2026, follow-up)

Frontend-only update (backend unchanged from v52bl).

- `apps/admin-console/CorrigendaPanel.jsx` — complete rewrite of the create
  form. When a notice is picked the admin now sees a 14-row table of every
  amendable field with four columns:
  `Field · Current value · New value (optional) · Reason for this change`.
  - Fields: Title, Description, Category, Document type, Delivery country,
    Submission deadline, Budget currency, Budget amount, Tender fee,
    Form of contract, EMD fixed amount, EMD % of budget, Pre-bid meeting,
    Clarifications close.
  - Per-row Reason input becomes required only when a New value is typed.
  - Added mandatory `Corrigendum date` (defaults to now) → serialised as
    `effective_from` on the payload; recorded in the audit ledger.
  - Overall change description now hard-blocks on min 8 chars.
  - Published rows render the full before/after/reason table + corrigendum
    date in the admin list.
  - Uses `adminApi.getNoticeAdmin` first so DRAFT notices populate too (public
    endpoint returned 404 for unpublished notices).
- Fresh frontend bundle shipped as **pmc-frontend-v52bm-prod-build.zip**
  (3.0 MB). Backend untouched — keep `pmc-backend-v52bl.zip`.

Verified via Playwright: 14 field-rows render for picked notice, Title/
Description/Category current values populate, mandatory Corrigendum date
visible. All existing testids preserved for regression.

---



## v52bm — Create-notice submit no longer hijacked to Tender builder (10 Oct 2026)

Bug: on Admin → Notices → New notice, pressing **Create notice** with missing
required fields (category / budget / EMD / primary doc) showed the validation
toast but ALSO navigated to `/admin/e/tender-builder`, closing the form and
losing context.

Root cause: `components/PmcLinkPatcher.jsx` global delegated click handler —
its catch-all regex `/^(create|new\s+(tender|notice|package))/` (and the
`ADMIN_LINKS` label map) routed ANY admin button whose label starts with
"Create"/"New" to the Tender builder, including the wired React
`data-testid="notice-create"` button. React's onClick fired (toast) while the
patcher navigated anyway.

Fix: `PmcLinkPatcher.jsx` — wired admin controls (`data-testid` present, per
project mandate) now bypass both `resolveClickAction` and the label-map /
regex fallbacks (`isWiredAdminControl` guard). Static template buttons
without testids keep the legacy routing behaviour.

Verified via Playwright repro (before/after):
- Submit with missing category+budget → URL stays `/admin/e/notices`,
  `notice-new-form` remains open, typed Title/Description preserved,
  toast "Category is required" visible on the SAME page.
- New notice toggle (Cancel → re-open) also stays on the same page.

Note: frontend-only change — v52bl frontend zip predates this fix; next
bundle (v52bm) should be regenerated before deploy.

---



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
