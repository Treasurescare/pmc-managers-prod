# PMC Managers v2 — Release v48c (Feb 2026, rev-2)

## Headline
**Option E design overhaul + 4 team-reported bug fixes. Opt-in via `?ui=e`; legacy Tender-Hub UI is still the default.**
No user sees a different UI unless they add `?ui=e` to the URL (which then sticks in `localStorage`).
`?ui=default` (or clearing `localStorage.pmc_ui_theme`) reverts to legacy instantly.

## What's in this release

### 1. New Option E theme (opt-in)
Forest green `#0F3B2E` + sovereign gold `#D2B46A` + cream `#F3EFE4` palette, with
Cormorant Garamond display serif + Public Sans + JetBrains Mono, built to match the
5 uploaded HTML mockups.

### 2. Structural rewrites (visible only when `?ui=e`)
- **Home** — hero band with italic gold "sealed" headline, cream search pill, live-board
  panel driven by the 5 soonest-closing notices.
- **Tenders list** — "Refine" left aside (search / country / status key + status dots),
  pill tab switcher (Live / Completed / All), "Register of tenders" table with roman-
  numeral rows, gold countdown chips + status chips.
- **Notice detail** — forest-green hero band with breadcrumb, notice-ref pill,
  closing-soon chip, corrigendum chip, big Cormorant title, 6-column KPI strip
  (Estimated value / EMD / Tender fee / Deadline / Pre-bid / Evaluation).
- **Vendor Portal** — greeting band ("Good morning, [Name]"), 4 clickable KPI cards
  (Bids in progress / EMD due (amber attention) / Awarded / Open opportunities) that
  filter the bids table, "Sealed bid in progress" 5-step progression card.
- **Admin Overview** — attention strip (bidding / approvals / eval signatures) + 7-stage
  pipeline (Draft → Awarded, active stage IV highlighted in gold).
- **Admin shell + every admin tab** — dark forest sidebar, gold-highlighted active nav,
  cream content pane with gold accents. All existing tabs (Vendors, Bidding, DocuSign,
  Evaluation, Awards, Escrow, Meetings, Auctions, BOQ, Contracts, Masters, Audit, etc.)
  inherit the palette automatically via CSS overrides scoped under `[data-ui="e"]`.
- **Registration / Staff / Committee / Mobile / Payment / all other public routes** —
  auto-themed via body-level `data-ui="e"` toggle. No component changes needed.

### 3. Bug fixes (v48c)
- **Bidding ops sidebar tab** now appears as first item under "Money & Compliance"
  (AdminShell.jsx).
- **Work-package Kanban cards** are now clickable → opens detail modal with ref, title,
  status, category, value, float date, owner, notice, description, milestones. Drag-drop
  preserved. **Rev-5** — each card also shows an always-visible "View" pill in the
  top-right so the entry point is unmistakable.
- **Reverse auction Start button** now shows `<count>/2` and is disabled with tooltip
  when fewer than 2 participants are registered.
- **Meeting invite emails** now dispatch via Resend on `POST /api/v1/meetings` AND
  `POST /api/v1/meetings/{id}/invitees`. Response includes `invites_sent`.
- **Admin sidebar tab clicks** now sync to the URL query (`?tab=<code>`) so links can
  be shared and bookmarked.
- **Rev-4 — Android download prompt** — /register now shows two buttons: `View` opens
  the PDF inline in a new tab, `Download` uses `?inline=false` + HTML5 `download`
  attribute so Android Chrome reliably saves the file.
- **Rev-4 — Approved / rejected registration guard** — once a registration is decided,
  the detail pane hides the Approve/Clarify/Reject buttons and shows a coloured status
  banner instead.
- **Rev-4 — Pending review moderation chip** — Option E admin Overview attention strip
  now surfaces `N vendor reviews pending`; click to jump into Vendor Intel and scroll to
  the moderation table.
- **Rev-6 — Bulletproof blank-form download** — the two /register buttons now go via
  `fetch → Blob → URL.createObjectURL` instead of a plain `<a download>` anchor. This
  sidesteps Android Chrome / in-app WebView / corporate-proxy issues that would drop
  the Content-Disposition attachment header, and force-names the file
  `pmc-registration-form.pdf` so Windows always associates it with a PDF viewer.
- **Rev-6 — Service worker cache bumped to `pmc-shell-v48c-rev6`** so browsers actually
  pick up the new bundle without needing a hard-refresh.

### 4. Email sender
All outbound emails send **FROM `admin@mail.pmcmanagers.com`** (verified Resend domain).
Configured via `EMAIL_FROM_ADDRESS` in backend `.env`.

### 5. Rollback safety
- The v47h prod bundles (`pmc-backend-v47h.zip`, `pmc-frontend-v47h-prod-build.zip`) are
  still on disk in `/app/frontend/public/downloads/`. If v48c misbehaves, redeploy v47h
  and Option E disappears entirely.
- Alternatively, any user can hit `?ui=default` in the URL to revert their own browser.

## Verification
- Frontend testing agent iteration_27: 9/9 Option E scenarios PASS.
- Frontend + backend testing agent iteration_28: 6/6 bug-fix scenarios PASS.
- Manual smoke: Home, Tenders, Notice Detail, Registration, Vendor Portal (post-login),
  Admin Console (Overview + Vendors + all other tabs) — all render mockup-close in
  Option E, all render exactly like v47h in default mode.
- Production build scanned: **0 preview-URL references** (built with `REACT_APP_BACKEND_URL=`
  empty for same-origin `/api/*` routing). SW cache `pmc-shell-v48a`.

## Bundles
- `pmc-backend-v48c.zip` — Elastic Beanstalk. Includes meeting-invite email dispatcher.
- `pmc-frontend-v48c-prod-build.zip` — S3 + CloudFront (excludes `downloads/`). Includes
  the 4 bug fixes + tab deep-link sync.

## Deploy notes
- **Frontend**: upload every file inside the zip, including `static/`. Set no-cache
  headers on `index.html`, `service-worker.js`, `manifest.json`. Invalidate CloudFront
  `/*` after upload so the new SW takes effect on first paint.
- **Backend**: no new env vars, no DB migration. Same Docker image contract as v47h.
- **Announce**: share `https://your-domain/?ui=e` internally to preview Option E on
  production; the default remains v47h Tender-Hub for every other visitor.

## Not code bugs — action needed on your side
- **DocuSign PO shows "TEST_WV26_Vendor_1"** — that literally IS the vendor's registered
  `company_name`. Real vendors will show their real company name. No fix needed.
- **Vendor registration blank form downloads blank** — no admin has uploaded a template.
  Upload a PDF/DOCX via the admin console (Vendors → Registration template) or:
  `POST /api/v1/vendors/registration-template/upload` (multipart, field `file`).

## Rollback
If anything goes wrong:
1. Redeploy `pmc-frontend-v47h-prod-build.zip` to S3 + invalidate CloudFront `/*`.
2. Redeploy `pmc-backend-v47h.zip` to Elastic Beanstalk.
3. Users' `localStorage.pmc_ui_theme` values stay set but the code is gone — Option E
   simply won't render.

## Headline
**Option E design overhaul — opt-in via `?ui=e`. Legacy "Tender-Hub" (v47h) UI is still the default.**
No user sees a different UI unless they add `?ui=e` to the URL (which then sticks in `localStorage`).
`?ui=default` (or clearing `localStorage.pmc_ui_theme`) reverts to legacy instantly.

## What's in this release

### 1. New Option E theme (opt-in)
Forest green `#0F3B2E` + sovereign gold `#D2B46A` + cream `#F3EFE4` palette, with
Cormorant Garamond display serif + Public Sans + JetBrains Mono, built to match the
5 uploaded HTML mockups.

### 2. Structural rewrites (visible only when `?ui=e`)
- **Home** — hero band with italic gold "sealed" headline, cream search pill, live-board
  panel driven by the 5 soonest-closing notices.
- **Tenders list** — "Refine" left aside (search / country / status key + status dots),
  pill tab switcher (Live / Completed / All), "Register of tenders" table with roman-
  numeral rows, gold countdown chips + status chips.
- **Notice detail** — forest-green hero band with breadcrumb, notice-ref pill,
  closing-soon chip, corrigendum chip, big Cormorant title, 6-column KPI strip
  (Estimated value / EMD / Tender fee / Deadline / Pre-bid / Evaluation).
- **Vendor Portal** — greeting band ("Good morning, [Name]"), 4 clickable KPI cards
  (Bids in progress / EMD due (amber attention) / Awarded / Open opportunities) that
  filter the bids table, "Sealed bid in progress" 5-step progression card.
- **Admin Overview** — attention strip (bidding / approvals / eval signatures) + 7-stage
  pipeline (Draft → Awarded, active stage IV highlighted in gold).
- **Admin shell + every admin tab** — dark forest sidebar, gold-highlighted active nav,
  cream content pane with gold accents. All existing tabs (Vendors, Bidding, DocuSign,
  Evaluation, Awards, Escrow, Meetings, Auctions, BOQ, Contracts, Masters, Audit, etc.)
  inherit the palette automatically via CSS overrides scoped under `[data-ui="e"]`.
- **Registration / Staff / Committee / Mobile / Payment / all other public routes** —
  auto-themed via body-level `data-ui="e"` toggle. No component changes needed.

### 3. Rollback safety
- The v47h prod bundles (`pmc-backend-v47h.zip`, `pmc-frontend-v47h-prod-build.zip`) are
  still on disk in `/app/frontend/public/downloads/`. If v48c misbehaves, redeploy v47h
  and Option E disappears entirely.
- Alternatively, any user can hit `?ui=default` in the URL to revert their own browser.

## Verification
- Frontend testing agent iteration_27: 9/9 scenarios PASS (persistence, scoping, legacy
  regression, admin-shell isolation, `?ui=default` revert).
- Manual smoke: Home, Tenders, Notice Detail, Registration, Vendor Portal (post-login),
  Admin Console (Overview + Vendors + all other tabs) — all render mockup-close in
  Option E, all render exactly like v47h in default mode.
- Production build scanned: **0 preview-URL references** (built with `REACT_APP_BACKEND_URL=`
  empty for same-origin `/api/*` routing). SW cache bumped to `pmc-shell-v48a`.

## Bundles
- `pmc-backend-v48c.zip` — Elastic Beanstalk (no backend changes vs v47h; same code,
  fresh label).
- `pmc-frontend-v48c-prod-build.zip` — S3 + CloudFront (excludes `downloads/`).

## Deploy notes
- **Frontend**: upload every file inside the zip, including `static/`. Set no-cache
  headers on `index.html`, `service-worker.js`, `manifest.json`. Invalidate CloudFront
  `/*` after upload so the new SW takes effect on first paint.
- **Backend**: no new env vars, no DB migration. Same Docker image contract as v47h.
- **Announce**: share `https://your-domain/?ui=e` internally to preview Option E on
  production; the default remains v47h Tender-Hub for every other visitor.

## Rollback
If anything goes wrong:
1. Redeploy `pmc-frontend-v47h-prod-build.zip` to S3 + invalidate CloudFront `/*`.
2. Redeploy `pmc-backend-v47h.zip` to Elastic Beanstalk.
3. Users' `localStorage.pmc_ui_theme` values stay set but the code is gone — Option E
   simply won't render.
