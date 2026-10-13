# PMC Managers v2 — Changelog
# PMC Managers v2 — Changelog

## 2026-02-13 — v52cu Landing page shows newly published notices instantly

### User report
"the moment the publish button is hit in the admin console it should appear
immediately on the landing page" — user confirmed option (c) from the
nine-reason analysis.

### Fix
- `backend/routers/notices.py` — public `GET /api/v1/notices` now returns a
  `JSONResponse` with `Cache-Control: no-store, no-cache, must-revalidate`,
  `Pragma: no-cache`, `Expires: 0` (mirrors the admin `/admin/all` route).
  Previously it returned a plain dict with no cache headers, so CloudFront /
  the browser could serve a briefly-stale list after Publish.
- `backend/routers/meta.py` — `GET /api/v1/meta/public/stats` (landing
  "tenders open for bids" counter) gets the same no-store headers.

### Verification
- curl on preview confirms both endpoints send the no-store headers.
- `test_v52cp_notices.py` 7/7 still pass.

### Note
Remaining (not requested) reasons a tender may not appear on landing:
limit=30 default cap (a), null published_at sinking in sort (b).
Offered to user as follow-ups.




## 2026-02-13 — v52ct New Notice ↔ Tender Builder bridge — six-point fix

### User report
Admin → New Notice form had six defects: (1) Tender Template picker shown below Title, (2) picking a template only prefilled title/description/budget — not category/country/EMD, (3) Category was a static country-curated `<select>`, not the full UNSPSC search, (4) notices could be created with budget 0, (5) upload required, (6) public cards missed budget/EMD/country.

### Fix
- **NoticesPanel.jsx**:
  - Imported `UnspscPicker`.
  - Added `category_code` to draft state (initial + reset).
  - Replaced static category `<select>` with `UnspscPicker` using proper `value`/`title`/`testidPrefix='notice-category'` props so the UNSPSC search backs the field.
  - `pickTemplate(tpl)` now also prefills `category`, `category_code`, `delivery_country`, `budget_currency` and `emd_config.currency` from the tender header (`product_category`/`sub_category`/`tender_category`, `delivery_country`/`country`, `budget_currency`, `budget_amount`/`tender_value`).
  - Tender Template picker remains at the TOP of the form (confirmed via DOM order: tender-template index 1 < title index 3).
- **Backend** already enforced `budget_amount > 0` at `routers/notices.py:160` and already serialized flat `emd_amount`/`emd_currency` on every public response in `_out()`.
- **Tests**: added 3 new regressions to `test_v52cp_notices.py` (zero-budget rejection, full template → notice round-trip with category/country/budget/EMD assertions, stable zero-EMD public shape). 7/7 pass.

### Verification
Testing agent iteration 61: 100% backend (7/7), 100% frontend (6/6 acceptance points). Confirmed on preview:
- Template picker above Title.
- `notice-category-input` opens `notice-category-dropdown` with real UNSPSC options.
- Toast "Budget amount must be greater than zero" fires both for empty and 0.
- Primary document labelled OPTIONAL; create succeeds without it.
- `/tenders/all` cards show country, budget currency+amount, EMD chip.





## 2026-10-04 — v51n Floating help drawer searches the full manual

### User report
Drawer search for "tender" returned 1 result while the Help Centre page
returned 2 (supplier) / 13 (staff). Reason: the drawer searched only its 7
hardcoded quick FAQs; the Help Centre searches the full 28-module manual.

### Fix (PmcHelpDrawer.jsx)
- Drawer now fetches /api/v1/meta/help on first open and searches the full
  manual in addition to the quick FAQs: quick answers render first, then a
  "From the full manual" section with up to 6 matching guides linking to
  /help/<slug>. Empty state only when neither matches.


## 2026-10-04 — v51m Help Centre topic cards cross-role + dead drawer scrub

### User report (video on production v51l)
Clicking "Signatures & contracts" / "EMD & payments" as a supplier showed
"No guide matches"; the floating "?" drawer's search box did not filter.

### Root causes
1. v51l topic→module mapping pointed at admin-surface modules
   (admin-docusign, admin-escrow, …) while the default "supplier" role tab
   excluded admin surfaces — so most topic cards filtered to zero guides
   for suppliers.
2. Twelve static pages still embed the original mockup help drawer
   (search box with no handler). It shares .pmc-drawer/.pmc-helpfab
   classes with the real React PmcHelpDrawer and rendered on top of it.

### Fixes
- HelpCentreE: topic cards now search the ENTIRE manual regardless of
  selected role (guides carry Suppliers / Buyers & staff chips); role
  tabs only scope the unfiltered library view. Verified: Signatures=2,
  EMD=2 guides for suppliers.
- PmcHelpDrawer: on mount and on every route change, removes any
  non-React duplicate drawers/fabs/scrims from the DOM, leaving the
  single working drawer (live FAQ search). Verified: exactly 1 drawer on
  the homepage, "emd" search filters correctly.


## 2026-10-04 — v51l Help Centre fully wired (was a static mockup)

### User report
"The help module does not work — none of the tabs which show chapters work"
+ "even the search bar does not work."

### Root cause
help-centre/HelpCentreE.jsx and HelpArticleE.jsx were static design mockups:
topic cards, guided tours, Raise-a-ticket all `<a href="#">`; the search
input carried a data-faq-q attribute no listener consumed; /help/:slug
ignored the slug and rendered one fixed sample article.

### Fix (full rewrite of both components)
- HelpCentreE fetches /api/v1/meta/help (28 real manual modules) and
  renders them as searchable accordions (title, purpose, prerequisites,
  action steps, expected outcomes).
- The 8 topic cards now filter the library via code mapping with live
  counts; role tabs split supplier (vendor/public/registration surfaces)
  vs buyer & staff (admin/staff/magic).
- Search box matches across titles, purposes, action labels and steps
  (all words must match).
- Raise a ticket opens a modal posting to the real public endpoint
  POST /api/v1/auth/help-request (kind="other") — lands in the admin
  help-requests queue.
- HelpArticleE renders the module matching the :slug (deep links like
  /help/admin-docusign work) with a not-found state.
- Dead Guided-tours column removed.
- Verified live: cards filter (3 supplier guides), staff role shows 25,
  search "docusign" → admin-docusign, ticket submits with success toast,
  deep link renders the DocuSign guide.


## 2026-10-04 — v51k Platform-branding scrub ("how did the client know?")

### User question
A client told the user the app was built with Claude + Emergent. Full
case-insensitive sweep of frontend src/build, backend, public assets,
manifests and service worker.

### Leak points found (ranked by visibility)
1. **Help Centre content** (backend/pmc_lib/help_content_data.py, served
   via routers/help_content.py) literally said "Emergent LLM copilot",
   "Emergent LLM outlier detector", "Emergent LLM Universal Key proxy" —
   readable by any logged-in user. → All neutralised to "AI copilot" /
   "AI outlier detector" / "AI engine".
2. **Source maps shipped in production builds** (main.*.js.map) — full
   original source incl. comments browsable in DevTools. → Build now sets
   GENERATE_SOURCEMAP=false and stale .map files are deleted before zip.
3. **One literal string in the live JS bundle**: ".preview.emergentagent
   .com" (api.js preview-domain guard). → Assembled from fragments so a
   bundle text search for "emergent" returns zero hits.
4. **Backend internals** (EMERGENT_LLM_KEY env names, proxy URL, comments)
   — never served publicly; only visible inside backend zips under
   /downloads/ (which only the site owner downloads). No HTTPException
   detail leaks the proxy URL (verified by grep).
5. No "claude" string anywhere in src, build, backend or public assets.

### Verification
Fresh production bundle scanned: zero matches for emergent/claude in
shipped JS/CSS/index.html/manifest/service-worker; 0 source-map files.
Backend module compiles.

### Remaining traces that are infrastructure, not code
- Transactional email routing passes through the platform email proxy;
  a recipient inspecting raw SMTP headers may see the upstream provider.
  Eliminating that requires moving to direct Resend/LLM keys.
- Preview URLs (*.preview.emergentagent.com) exist in chat history, not
  in the deployed product.


## 2026-10-04 — v51j Tender builder: DPR char-count note hidden + cover numbering fix

### User reports (screenshots from production)
1. "DPR fields the AI could not extract" box shows a technical line
   "Document is 57,687 chars — deep-dive analysed first 74,000 chars in
   2 chunks" on EVERY DPR — user: not necessary to display; keep it only
   for the audit trail.
2. Cover Details numbering broken: 3 covers show 1, 1, 2 (and 2 covers
   show 1 & 1) — should be 1, 2, 3.

### Root causes & fixes
1. backend/routers/tender_pro.py:211 appended the ingestion note into the
   `warnings` list that renders as unextracted fields (only when the doc
   exceeded the chunk budget — i.e. most real DPRs; the maths even
   overcounted: 74,000 > 57,687). Removed the append; frontend additionally
   filters the persisted note from display for previously generated drafts
   (TenderHeaderForm warnings filter). Audit ledger untouched.
2. TenderHeaderForm.jsx default covers template had cover_no 1,1,2 baked
   in. Defaults corrected to 1,2,3 and every loaded covers array is
   renumbered sequentially (repairs legacy drafts). addCover already used
   length+1 correctly. Verified live: default draft shows 1,2,3.


## 2026-10-04 — v51i All sign-outs land on the unified /login page

### User report (with screenshot)
"THIS is the page the signout should trigger" — the unified SignInE role-
picker page — "not the navy blue page" (legacy VendorLogin). Sign-out
paths were inconsistent: mobile nav and desktop vendor avatar went to
/vendor/login, admin went to /, staff to /staff/login.

### Fix — every sign-out now navigates to /login
- PmcMobileNav doSignOut (vendor top bar + drawer + admin top bar)
- VendorPortalChrome avatar-menu sign out
- AdminDashboard logout (was "/")
- StaffDashboard logout (was /staff/login)
- VendorDashboard legacy logout (was /vendor/login)
PmcLinkPatcher's handleSignOut already went to /login. Auth guards that
redirect unauthenticated users are unchanged (they carry return-to state).


## 2026-10-04 — v51h Vendor sign-in page: ghost labels + navy band

### User report
After sign-out, /vendor/login (legacy VendorLogin.jsx) shows washed-out,
near-invisible "Email"/"Password" labels on both iPhone and desktop Safari,
plus a dark navy band at the bottom of the mobile page.

### Root cause
The legacy page relies on Tailwind slate utilities (text-slate-700/500)
which render inconsistently across bundles in this project (production
bundle variations purge or remap them — same class family that rendered
bg-slate-50 as a dark block in the DocuSign console). The outer wrapper's
inline #0b1e3f background showed through as a navy band on mobile where
100vh < visual viewport under Safari's chrome.

### Fix (VendorLogin.jsx — deterministic inline styles)
- Labels: color #334155 + fontWeight 600 (inline, immune to palette purge).
- Subtitle/footer links: #64748b inline.
- Inputs: explicit color #0f172a on #ffffff.
- Outer wrapper background white; left promo panel carries its own
  #0b1e3f — desktop unchanged, mobile navy band eliminated.
- Verified live: label rgb(51,65,85), root bg white.


## 2026-10-04 — v51g Vendor mobile top bar restructure

### User report after v51f
Drawer Sign out still not acceptable — user asked: "move the signout and
avatar button to the top right, and move the hamburger to the top left."

### Fix (PmcMobileNav.jsx vendor branch)
New vendor mobile top bar layout, left to right:
  [hamburger] [back (sub-pages only)] [brand] ... [bell] [avatar] [Sign out]
- Avatar circle shows company initials (fetched via vendorApi.me) and links
  to /vendor/account.
- Sign out is a persistent bordered button in the top bar — always visible,
  no drawer needed. (Drawer keeps its brass Sign out as a second path.)
- Brand subtitle ("Supplier portal") hidden on ≤767px to make room;
  verified at 390px: hamburger left=16px, avatar "MA" at 266px, Sign out
  70px wide at 304px, no horizontal overflow.


## 2026-10-04 — v51f build-break postmortem
A rogue `//` comment on line 1199 of mobile-fix.css (left behind by an
earlier search_replace) caused the CSS minifier to fail every v51f build
with "Unexpected '/'. Escaping special characters with \\ may help." —
CSS has no `//` syntax; the minifier read it as two bare slashes. Replaced
with a `/* ... */` block comment. Build succeeded; v51f bundle regenerated
at 2.9MB (was shipping a stale 879KB stub before the fix).


## 2026-10-04 — v51f Mobile vendor chrome polish + /login layout fix

### User reports after v51e deploy (iPhone 5G screenshots)
1. Sign out button is NOT visible in the mobile drawer (empty green area
   under Help & FAQs).
2. There is no avatar icon anywhere on mobile — only the hamburger.
3. The notifications/bell lives in the Alerts bottom tab; user wants it in
   the top bar next to the hamburger.
4. The /login page is broken on mobile — role picker cards and inputs
   overflow the right edge of the viewport ("Forg…", "…ute").

### Fixes
1. Alerts removed from bottom tab bar (now 4 tabs: Home / Tenders / Bids /
   Account); a bell icon added to the vendor mobile top bar, left of the
   hamburger, linking to /vendor/alerts.
2. Drawer Sign out is now a full-width brass primary button (previously an
   invisible ghost — the shared `.pmc-mob-menu-cta a.ghost` CSS only styled
   `<a>` elements, so the raw `<button>` had no appearance). Both the
   inline style AND a belt-and-braces CSS rule at
   `.pmc-mob-menu-cta button[data-testid="pmc-mobile-menu-signout"]` force
   bg #d9bd72 / 48px min-height / border-radius 6 / weight 700 / 100% width.
   Verified live: bg rgb(217,189,114), 326×48, visible:true.
3. /login (SignInE) rewrites itself on ≤767px: the left pmc-chrome hero
   collapses (display:none), the inline 2-column grid becomes 1fr, the
   right section pads 20/16, the form fills 100% width, and every
   .pmc-input is max-width:100% + border-box. Screenshot: role cards and
   inputs fit cleanly inside the viewport, no horizontal scroll.


## 2026-10-04 — v51e Design + mobile sign-out/back + Print-in-tab

### User reports after v51d deploy
1. Vendor bid workspace design broken — "EligibilityKYC match",
   "2Technical envelopeNot sealed" etc. all on one line.
2. Mobile view had NO sign-out option and NO back buttons anywhere.
3. v51d downloads worked, but Print opened a browser Save-As dialog
   instead of printing.
4. Save PDF stored into "PMC storage" but no visible way to see/access it.

### Fixes
1. `.pmc-steplist > a` CSS rules were duplicated three times but
   VendorBidWorkspaceE.jsx renders the five steps as `<div>` elements.
   Added mirror rules for `.pmc-steplist > div` (flex layout, 12px gap,
   small→block). Also added `.pmc-pill { white-space:nowrap }` and
   tablet-friendly collapse of the 260/1fr/300 workspace grid at
   ≤1300px (aux card drops below main) and ≤900px (all stacked).
2. **PmcMobileNav** rewritten:
   - Vendor mobile now renders a top bar (back + brand + hamburger) +
     a drawer with secondary nav links and a **Sign out** button +
     the existing bottom tab bar.
   - Admin/staff mobile now renders a compact top bar with back + brand
     + inline Sign out (desktop sidebar collapses on <=767).
   - Both use a unified `doSignOut()` that calls the right logout API
     and routes to the right login page.
   - Verified live: admin+vendor mobile both show working back + Sign out.
3. **Print** button in admin DocuSign console now calls `printSigned()`
   which opens the signed PDF inline in a new tab via `window.open(blobUrl)`
   so the browser's built-in PDF viewer loads it — admin clicks the
   viewer's own Print icon. Previous behaviour forced Save-As.
   Added separate ⬇ Download button in view modal.
4. Visibility of PMC-stored copies:
   - Each stored envelope now shows a **✓ PMC stored** green chip in
     the row and in the view modal.
   - Save PDF button auto-hides once stored and the chip appears.
   - Save PDF success toast now explains: "Download and Print now serve
     this copy even if DocuSign is unreachable."
   - Chip's title attribute carries the storage key for admins who need
     the DB key directly (uploads collection, `docusign-archived/<id>.pdf`).


## 2026-10-04 — v51d DocuSign download bytes fix + Archived tab

### User report after v51c deploy
Screen recording on pmcmanagers.com: "View / Print / Save PDF / signed
download all still broken". Toasts clearly showed TWO messages — "Download
failed · Could not read the fetched PDF from disk" and "Save PDF failed ·
Request failed with status code 500". Reassign + Archive working.

### Root cause (production, not preview)
Every PDF endpoint relied on `envelopes_api.get_document()` returning a
string path to a NamedTemporaryFile that we then `Path(p).read_bytes()`'d.
On AWS Elastic Beanstalk the SDK's temp file was auto-removed before our
next line ran (GC race / SDK version), so DocuSign auth was fine but
`read_bytes` 500'd. Preview sandbox never surfaced this because the
upstream 424 fired first.

### Fix — `_fetch_document_bytes()` helper
Reads raw urllib3 response bytes via `_preload_content=False`, bypassing
the tempfile hop entirely. Falls back to the old path style for very old
SDK versions. Also validates length > 0 (502 if empty). Replaced all 5
`get_document()` call sites:
- admin `combined-pdf`
- vendor `mine/.../combined-pdf`
- vendor `mine/.../document.pdf`
- admin `archive-pdf`
- (dead-duplicate archive-pdf body removed — leftover from v51c refactor)

### Archived tab
`DocuSignPanel.jsx` filter row now has 7 chips with live counts:
All / Sent / Waiting / Signed / Rejected / Voided / **Archived**. Archived
rows live in exactly one tab — "All" and status tabs hide them. Verified
live: All (3), Archived (1), zero chip leakage.


### v51c follow-up 2 (user preview verification, same day)
User: "save pdf still not working; save/print/download still having issues"
(preview) + mobile batch:
1. **Gateway swallowed error details** — the preview ingress replaces any 5xx
   response with its own HTML error page, so toasts only showed "Request
   failed with status code 502". All DocuSign upstream failures in
   docusign.py remapped 502 → **424 Failed Dependency** with explicit JSON
   ("DocuSign authentication failed — integration key/consent invalid/expired
   in this environment; check DOCUSIGN_*"). Verified: combined-pdf now returns
   424 + full JSON through the gateway. Frontend download handlers additionally
   unwrap blob error bodies so the real server reason renders in the toast
   (DocuSignPanel.jsx, VendorSignaturesE.jsx).
   Reminder: preview DocuSign sandbox key is expired (invalid_grant /
   issuer_not_found) — live-DocuSign buttons can only fully succeed on
   production or with fresh sandbox creds in preview env.
2. **Mobile input overflow** — global ≤767px guard: all input/select/textarea
   max-width:100% + border-box. Verified no visible overflow at 390px and
   360px on /vendor/login, /, /tenders/live (earlier "overflowing" elements
   were the off-canvas drawer — expected).
3. **Frozen mobile chrome** — .pmc-mobile-topbar now position:fixed top:0
   (was sticky, broke under some ancestors) + body:has() padding-top:60px;
   .pmc-mobile-tabbar z-index 950; page-bottom clearance extended beyond
   vendor roots ([data-pmc-e-page], .pmc-app, main get 104px) so the fixed
   bottom menu never covers the last buttons. Verified: header frozen at
   scroll 500-800px; vendor mybids bottom content clears the tab bar
   (the "hidden button" in probes was the closed help drawer's footer —
   off-canvas, not a bug).
4. **Tender listing edge-to-edge** — root cause: two existing rules set
   `padding: 16px 0 40px !important` on grid .pmc-wrap variants at higher
   specificity. Changed both to `16px 12px 40px` and bumped the generic
   mobile wrap rule to `[data-ui="e"] .pmc-wrap`. Verified: tl-row
   left=13/right=357 at 390px viewport.


### v51c follow-up (user preview verification, same day)
User confirmed Archive works but found 3 more issues via screenshots:
1. **Save PDF 403 "CSRF token missing or invalid"** — `archive-pdf` was the ONLY
   endpoint in the docusign router using `require_role("admin")` (bundles the
   cookie-based `require_csrf` check). Session cookies are SameSite=Lax, so any
   context where cookies can't flow (preview iframe at app.emergent.sh,
   third-party blocking) 403'd while Bearer-auth siblings worked. Fixed:
   archive-pdf now uses `current_admin` like every other endpoint in the router.
2. **Admin Print/download fragility** — `download_combined_pdf` (admin) always
   called live DocuSign; now serves `archived_file_key` from PMC storage first
   (same behaviour the vendor endpoints already had).
3. **Archived row unreadable** — `opacity-50 bg-slate-50` on the <tr> rendered
   as a dark washed-out block (Tailwind slate classes misbehaving in this
   build). Replaced with deterministic inline styles: light warm-grey row
   (#e8e5df), readable text, dark "archived" chip, full-strength buttons.
Verified in preview: archived row bg=rgb(232,229,223) text=rgb(20,38,31)
chip+Restore present; Save PDF reaches DocuSign (502 in preview = expired
sandbox creds, environmental only); restore leaves data clean.

## 2026-10-04 — v51c DocuSign console regression fix (reassign / archive / resend / download / duplicate Archive)

### User report (production, v51b)
Print/download + Archive dead; Reassign dialog opened but "Reassign & save" did
nothing; TWO buttons both labelled "Archive"; signed download dead; Resend dead.
Archive showed a blue toast but nothing changed.

### Root causes (4 distinct bugs)
1. **Missing API client methods** — v51b added `reassignEnvelope`,
   `archiveEnvelope`, `unarchiveEnvelope` calls in DocuSignPanel.jsx but the
   methods were never added to `docusignApi` in lib/api.js (a failed
   exact-string edit during v51b). Every click threw a silent TypeError.
2. **Silent error toasts GLOBALLY** — `showApiError()` used
   `require("sonner")`, which resolves to sonner's CJS build — a SEPARATE store
   from the ESM store the mounted `<Toaster/>` listens to. Error toasts were
   dispatched into the void on every API failure app-wide; only direct-import
   toasts rendered. Fixed with a top-level ESM import in api.js. This was the
   main "no error messages are displayed" culprit.
3. **Resend 502 by design bug** — `docusign.py` resend embedded branch called
   `_recipient_view()` with 4 of 6 required args (missing client_user_id +
   return_url) → TypeError → HTTP 502 on every embedded resend. Fixed, plus a
   recipient repair pass (stamps client_user_id when missing).
4. **Duplicate "Archive" labels** — two DIFFERENT actions shared the label:
   amber ⇩ = "save signed PDF into PMC storage" (repair tool, completed only);
   slate ⌧ = "hide envelope from vendors" (v51b). Amber button renamed to
   "⇩ Save PDF" with a clarifying tooltip; the view-modal button likewise.

### Also in this pass
- Archived rows now visibly change: dimmed (opacity-50) + "ARCHIVED" chip next
  to the status; Archive button swaps to ⟲ Restore (restores visibility).
- Resend/Save-PDF loading toasts now resolve into success/error via sonner id
  replacement instead of lingering and auto-dismissing.
- Resend pre-flight guard now blocks "declined" (was the non-existent
  "rejected"); reassign modal Cancel button got data-testid.

### Verified in preview
- curl (admin JWT+CSRF): listEnvelopes 200, reassign 200, archive 200
  (archived:true persisted), unarchive 200 — iteration_45.json backend 100%.
- testing_agent iteration_45: reassign valid/invalid, archive, restore, unique
  labels, vendor /vendor/signatures — all PASS.
- Main-agent self-test after toast fix: Resend, Print, Save PDF now render
  visible error toasts on failure (preview DocuSign sandbox creds are invalid
  — invalid_grant — so live-DocuSign calls 502 in preview by environment, not
  code; production creds work).
- Per-row label audit: exactly one "Archive" per row; "Save PDF" distinct.

### Production note
If any live-DocuSign action still fails after the next deploy, the toast will
now show the exact server reason — capture it for diagnosis.

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

## 2026-10-03 — v50v (rebuilt): EMD "nothing to pay" root cause + fix
- RCA: User's workspace URL bid (PMC-BID-2026-00026) already had status=emd_paid (4000/4000 paid). The static prod workspace hardcoded "Awaiting your EMD" so vendors could click Pay on a settled bid; backend correctly rejected with 400 "EMD not payable at status emd_paid", surfacing as a dead-end error.
- Fix 1 (v50v live workspace): paid bids now show "Settled" pill and disabled "EMD settled" button — verified on preview (PMC-BID-2026-00017: pill=Settled, button disabled).
- Fix 2 (BidPayRedirect): 400s like "not payable / already paid / no emd due" now render "This EMD is already settled… you're all set" with Back-to-My-bids + EMD & payments links. Verified on preview.
- Bundle contents re-verified: friendly-error fix, workspace routing fix, KYC categories tab all present in pmc-frontend-v50v-prod-build.zip.

## 2026-10-03 — v50w EMD proof upload document list
- VendorBidWorkspaceE: uploads previously showed only a toast and vanished. Now every uploaded EMD proof / BG lands in an "Uploaded (N)" panel with filename, size, View (inline new tab via /api/v1/uploads/files/{key}, auth-gated) and Delete. Multi-file supported.
- Verified on preview: 2 PDFs uploaded → both rows listed, View HTTP 200, Delete 2→1.

## 2026-10-03 — v50x EMD workspace UX
- Zero-EMD tenders (emd_due_amount=0): Pay EMD / Submit-for-review button hidden entirely; workspace shows "No EMD required for this bid".
- View on uploaded proofs now opens an in-page preview modal (iframe for PDF, img for images) with Close + Open-in-new-tab fallback, instead of navigating away.
- File URL fix: key appended raw instead of encodeURIComponent — %2F slashes were 404ing through CloudFront/nginx ("new page shows nothing").
- Verified: zero-EMD bid hides button; modal opens on same page; iframe src clean.

## 2026-10-03 — v50y Legal entity types master + registration doc view/download
- Backend: new router /api/v1/masters/legal-entity-types (CRUD + /public), seeded on startup with LLC/JSC/Sole Proprietorship/Partnership/Branch/Other.
- Backend: new /api/v1/registrations/{id}/documents/{slot}/file (magic-token auth) + /admin-file (admin cookie/bearer). Replaces /uploads/files which required a signed-in session and 401'd for vendors mid-registration.
- Frontend DocSlot: View/Download now hit the new token-authed endpoint. Admin RegDocCard uses /admin-file by regId+slot (no more key-path CDN quirks).
- Frontend SectionA: Legal entity type dropdown reads /legal-entity-types/public with EN/RU/KZ labels; falls back to the hard-coded list only if the API is unreachable.
- Frontend SectionD: Business categories replaced by a searchable multi-select fed by /masters/categories/public with chips + UNSPSC codes.
- Admin MastersPanel: new "Legal entity types" tab (LegalEntityTypesTab) with CRUD, country scope, EN/RU/KZ names, deactivate/reactivate.
- Verified end-to-end on preview: 6 defaults seeded, token-auth 200/404 pathway, admin-file 200, categories/public returns 105, admin create works.

## 2026-10-03 — v50z Vendor login links + DocuSign envelope scoping
- Vendor invite / activation / registration-approved emails linked "Sign in" to legacy /vendor/login (old split-screen page). All three (vendor_full_invite.py, vendor_invites.py, registrations_helpers.py) now link to the unified /login.
- /api/v1/docusign/mine scoped envelopes by email only → re-registered vendor reusing an email inherited stale envelopes (prod: PMC-SUP-000150 saw 3 pending from previous data). Now: bid ownership matched by vendor_id; signer_email matches only count for envelopes created after this registration. current_vendor dependency now returns created_at to support the guard.
- Verified on preview: seeded stale envelope (2026-01-01) + fresh vendor (today) → /mine returns 0; regression manualvendor unaffected. Test data cleaned up.

## 2026-10-03 — v51a Masters tabs + instant deactivate/reactivate
- MastersPanel tab bar: labels no longer wrap (whitespace-nowrap + shrink-0), single scrollable row; shortened verbose "(moved → Market)" labels.
- Legal entity types: optimistic toggle with rollback — row flips instantly; root cause of "needed hard refresh" was twofold: (1) audit_log called with admin.get("email") string instead of dict → HTTP 500 on deactivate/reactivate (fixed, also return_document=True → ReturnDocument.AFTER); (2) CloudFront could serve cached GET lists post-mutation (fixed with Cache-Control: no-store middleware on all /api/ responses in server.py).
- Verified: browser deactivate hides row immediately, show-inactive reveals Inactive, reactivate flips back; no-store header present on preview API.

## 2026-10-03 — v51b Language footer + Tender country mode + DocuSign reassign/archive
- PmcFooter: added LangSwitcher (dark variant) in the bottom bar on every page.
- TenderFilterBar + applyTenderFilters: country_mode radio toggle ("only" default | "all"); when "all" selected, country filter is bypassed.
- docusign.py: POST /envelopes/{id}/reassign (updates signer_email/name, audit log) + /archive + /unarchive. list_my_envelopes query now carries archived:{$ne:true} so vendors never see hidden envelopes.
- DocuSignPanel: ↪ Reassign modal (email/name/reason), ⌧ Archive / ⟲ Restore buttons on every row.
- Verified: /archive → 200, /unarchive → 200, /reassign bad-email → 400, py_compile OK.

## v51y — 06 Oct 2026
- **P0 fix**: Admin → Money & compliance panels "This panel hit an error" crash. Root cause was `InfoDot` rendering a `<button>` nested inside parent `<button>` elements (Evaluation lock-technical/commercial/report, L1 run, Permissions reset/save, Awards picker). Changed InfoDot trigger to `<span role="img">` which is valid HTML inside a button. One-component fix clears the crash on all 9 Money pages.
- **P0 fix**: Reverse auctions — Start returned HTTP 400 "need ≥2 participants" but admin had no UI to invite. `AdminAuctionsE` now shows an **Invite vendors** button per row that opens an inline panel with emails textarea, optional note, list of registered participants with aliases, and pending invite links with Copy-link buttons.
- Notices filters (date created / creator email / tender ref / status incl. Draft) retained from v51x; verified end-to-end.
- Testing: iteration_46 passed 18/18 (3 backend + 15 frontend).
- Bundle: `pmc-frontend-v51y-prod-build.zip` + `pmc-backend-v51y.zip` in `/frontend/public/downloads/`.

## v51z — 06 Oct 2026
- **Enhancement**: Reverse-auction Invite panel auto-emails vendors via Resend (default-on checkbox); backend `/invite` falls back to a built-in template when `auto_send=true` and no `template_id` is supplied, so admins never need to pre-seed.
- **Enhancement**: Every Draft auction row now shows an amber `0/2 participants` / `1/2 participants` or emerald `✓ 2/2 ready` badge next to the status pill. Backend list endpoint adds `participant_count` to each row (one round-trip for the whole table).
- **Enhancement**: Admin Notices filter state (`status`, `q`, `creator`, `from`, `to`, `templates`) is mirrored to the URL via `history.replaceState`, so operators can bookmark / share the exact view. Clear strips all params. Deep links rehydrate on first paint.
- Added `data-testid="auction-invite-pending-{token}"` to each pending-invite row for test stability.
- Testing: iteration_47 passed 19/19 (3 backend + 16 frontend; no regressions).
- Bundle: `pmc-frontend-v51z-prod-build.zip` + `pmc-backend-v51z.zip` in `/frontend/public/downloads/`.

## v51z hotfix — 06 Oct 2026 (bundled into v51z zip)
- **Bug fix**: Submitting a tender notice for approval with the Contact Email field left blank threw HTTP 422 "value is not a valid email address: An email address must have an @-sign." Root cause: Pydantic `EmailStr` rejects `""`. Backend `NoticeIn.contact_email` now coerces empty / whitespace strings to None via a `@field_validator(mode='before')`; frontend `NoticeEditModal.save()` additionally strips blank `contact_email` / `contact_name` before PATCH. Verified across 5 unit cases: empty string, whitespace, missing field, valid email, invalid email.

## v51aa — 06 Oct 2026
- **Feature**: Admin bulk-invite CSV template now covers every Sections A–E field (identity, contact, banking, business profile, declarations). New GET /api/v1/vendors/invite-bulk/template emits the full header set with one sample row. Parser coerces lists (|/;-separated), decl_* booleans, employees_count int, turnover_year* floats and stores them under vendor.profile for pre-fill on first login.
- **Feature**: Clearer 409 handling on single-vendor invite. Backend now returns structured detail {code:'vendor_already_active', vendor_ref, company_name, email}; admin UI shows a Sonner toast with an inline 'Edit full profile' action that jumps to /admin/vendors/{ref}/edit.
- **Feature**: New admin route /admin/vendors/:vendor_ref/edit (AdminVendorEdit.jsx) that lets an admin edit the ENTIRE Sections A–E profile of any created-but-unpublished vendor (and active ones). Each tab has its own Save button; backend PATCH /admin/{ref}/full merge-patches the profile sub-doc and audit-logs with profile_updated_at + profile_updated_by.
- Every vendor row in the admin panel now exposes an Edit full profile link (data-testid=vendor-edit-{vendor_ref}).
- Testing: iteration_48 passed 100% (4/4 backend pytest + full frontend walk-through); no regressions on prior v51y / v51z fixes.
- Bundle: pmc-frontend-v51aa-prod-build.zip + pmc-backend-v51aa.zip in /frontend/public/downloads/.

## v51ab — 07 Oct 2026
- **Feature**: Working Money & compliance search across every panel. New `MoneyFilterBar` (search tender/title, created-by, created from→to, expires from→to, status dropdown, clear) mounted on Reverse auctions, Bidding ops, Awards, Billing, Escrow/EMD, Evaluation, L1 comparison, DocuSign. Reverse auctions filters its React state directly; legacy panels filter via a MutationObserver that tags rows with status/created-at data-attrs on first paint.
- **Feature**: Reverse auction row **Edit** button on every draft. Inline edit form for title, currency, starting/floor price, min decrement, duration, anti-snipe seconds. Backend: PATCH /api/v1/reverse-auctions/{aid} with draft-only guard and floor<start validation.
- Preview smoke test: all 8 Money pages show the filter bar with no ErrorBoundary; typing a non-matching query shows the empty-filtered state; the Edit button opens the inline form pre-filled.
- Bundle: pmc-frontend-v51ab-prod-build.zip + pmc-backend-v51ab.zip in /frontend/public/downloads/.

## v51ac — 07 Oct 2026
- **Feature**: Per-row Edit sections on every non-approved registration (Draft / Submitted / Needs clarification). Opens the vendor-facing 5-section flow in a new tab (via admin-only /api/v1/registrations/admin/{rid}/resume-link); audit-logged. Approved registrations surface Edit full vendor profile linking to /admin/vendors/{ref}/edit.
- **Bug fix**: Expires from / Expires to filters were showing on panels that have no expiry concept (Awards, Billing, Escrow/EMD, Evaluation, L1 comparison, DocuSign). Hidden on those panels; still shown on Reverse auctions where each row carries end_at.
- Preview smoke test: Expires-fields hidden on 6 legacy panels, visible on Reverse auctions, Edit sections link renders on each non-approved registration row.
- Bundle: pmc-frontend-v51ac-prod-build.zip + pmc-backend-v51ac.zip in /frontend/public/downloads/.

## v51ad — 07 Oct 2026
- **Feature**: Corrigenda full workflow. Admin publishes numbered addenda; backend now accepts `extend_deadline_days` (auto-adds N days to the notice's current deadline) and `field_amendments[]` (versioned before/after diffs). New `GET /api/v1/corrigenda/outstanding` lists corrigenda a vendor must ACK; `POST /api/v1/corrigenda/{id}/acknowledge` records consent on the audit log; admin side gets `/corrigenda/{cid}/acknowledgements`.
- **Feature**: Saved views on every Money & compliance panel. New `/api/v1/filter-presets` CRUD (per admin user × scope). MoneyFilterBar shows a Saved views dropdown + Save view + Delete view when `presetScope` is set. Enabled on auctions, awards, billing, escrow, evaluation, l1, docusign.
- **Backend**: new routers `corrigenda._vendor_router` (vendor-side ack) and `filter_presets.router` mounted in server.py.
- Preview smoke test: preset-save button present on 7/7 panels; corrigenda extend-days + field-amendments UI live.
- Bundle: pmc-frontend-v51ad-prod-build.zip + pmc-backend-v51ad.zip in /frontend/public/downloads/.
