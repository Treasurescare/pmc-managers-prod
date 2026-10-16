# PMC Managers Limited — Release v50a

## What's fixed
### Admin content pane would not scroll at all (v49z regression)
User report after deploying v49z: sidebar is fixed (good) but the
content section cannot scroll — anything below the fold is unreachable.

Root cause: v49z targeted `.pmc-adm > main.pmc-amain` as the scroll
container, but in the real DOM the main column is an **unnamed wrapper
div** (`<div><header class="pmc-atop">…<main class="pmc-amain">…</div>`)
— a grandchild, not a direct child. The rule matched nothing, while
`.pmc-adm { height: 100vh; overflow: hidden }` clipped the page. No
element was scrollable → content trapped.

Fix (`pmc-responsive.css`, desktop ≥1101 px): the scroll container is
now the actual second grid column, whichever form it takes:

```css
[data-ui="e"] .pmc-adm > div:not(.pmc-drawer):not(.pmc-drawer-scrim),
[data-ui="e"] .pmc-adm > main.pmc-amain {
  height: 100vh; max-height: 100vh;
  overflow-y: auto; overflow-x: hidden; min-width: 0;
}
```

Bonus: the sticky `.pmc-atop` top bar now sticks inside the scrolling
wrapper, so the breadcrumb/search/help row stays visible while you
scroll — matching the sidebar behaviour.

Verified on preview (fresh session):
- `/admin/e/docusign` (the exact page reported): wrapper scrolls
  (`scrolledTo: 1500`), sidebar `top` unchanged before/after scroll,
  window scroll = 0.
- `/admin/e/dashboard`: same — wrapper scrolls, sidebar fixed, top bar
  present.

Service-worker cache bumped to `pmc-shell-v50a-rev1`.

## Bundles
* **Frontend: `pmc-frontend-v50a-prod-build.zip`** — deploy ONLY this
  (supersedes v49r → v49z).
* **Backend: `pmc-backend-v49y.zip`** — unchanged (DocuSign polling
  sync + completion notifications + embedded-signer emails + resend
  fix). Deploy if you haven't since v49q.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.
Backend — Elastic Beanstalk: upload `pmc-backend-v49y.zip`.

Verify:
- Admin dashboard + DocuSign page: content scrolls, sidebar + top bar
  stay put.
- Help → "Open the full Help Centre" → same-tab `/help`; "Back to
  tender board" returns to the dashboard.

## Rollback
Frontend v49q (pre-sidebar-work). No API or schema changes.
