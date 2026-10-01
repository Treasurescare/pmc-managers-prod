# PMC Managers Limited — Release v49z

## What's fixed
### 1. Layout collapse on v49w (sidebar overlapping main content)
Both prior sidebar attempts failed on production: `position: sticky`
(v49w) was defeated by a body `overflow-x` rule, and `position: fixed`
(v49x) overlapped the main column on some templates.

Fix (`pmc-responsive.css`, desktop ≥1101 px): the admin shell is now a
**two-pane scroll** — the page itself doesn't scroll:
```
.pmc-adm       { height: 100vh; overflow: hidden; }
.pmc-adm > aside.pmc-side { height: 100vh; overflow-y: auto; }
.pmc-adm > .pmc-amain     { height: 100vh; overflow-y: auto; }
```
The sidebar literally cannot move because window scroll is zero on
admin pages. Main content scrolls inside its own pane. The grid keeps
its explicit `260px minmax(0,1fr)` columns. Mobile drawer is scoped
out of this rule.

Verified on preview: `sidebarStays: true` after scrolling the main
pane 500 px.

### 2. Help Centre "Back to tender board" was dead; stray "Sign in"
`HelpCentreE.jsx` + `HelpArticleE.jsx` had `href="#"` on both buttons.

Fix:
- "Back to tender board" → `href="/admin/e/dashboard"` with
  `data-testid="help-back-to-board"`. PmcLinkPatcher turns the "/"
  href into SPA navigation (no new tab).
- Removed the "Sign in" button (nonsensical for logged-in users;
  signed-out users already see the usual sign-in link in the main nav).
- Help Centre brand link now goes to `/`; article brand link goes to
  `/help`.

### 3. "Open the full Help Centre" previously opened a new tab
v49x already fixed this: `/help` href navigates in the SAME tab via
the SPA router, and closes the drawer first. v49z keeps that.
If you prefer the Help to stay inline (never leaves the current page),
the quick-help drawer already shows the FAQ in-page — only the "Open
the full Help Centre" button goes to the full page, which is where
guided tours and ticket raising live.

Service-worker cache bumped to `pmc-shell-v49z-rev1`.

## Bundles
* **Frontend**: `pmc-frontend-v49z-prod-build.zip` — supersedes
  v49r/v49s/v49t/v49u/v49v/v49w/v49x. Deploy ONLY this.
* **Backend**: `pmc-backend-v49y.zip` — unchanged (DocuSign polling +
  completion notifications + embedded-signer emails + resend fix).
  Deploy this if you haven't already since v49q.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.
Backend — Elastic Beanstalk: upload `pmc-backend-v49y.zip`.

Verify:
- Admin dashboard: sidebar stays rock-steady while right pane scrolls.
- Help → "Open the full Help Centre" → opens `/help` in the same tab;
  "Back to tender board" returns to `/admin/e/dashboard`.
- DocuSign signing → completion appears in Admin DocuSign list
  automatically; admin + signer get confirmation emails.

## Rollback
Frontend v49q. No API or schema changes.
