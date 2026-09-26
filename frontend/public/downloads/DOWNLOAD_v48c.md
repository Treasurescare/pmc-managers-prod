# PMC Managers v2 — Release v48c (Feb 2026)

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
