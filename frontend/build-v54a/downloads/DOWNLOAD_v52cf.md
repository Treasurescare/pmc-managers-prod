# PMC Managers — Frontend v52cf + Backend v52cf (12 Oct 2026)

Quick-wins pack from your Tender Builder follow-up.

## What's in this build

### 1. Tender Builder "Your drafts" — created date + author
Each draft row in the left sidebar now shows **Created DD/MM/YYYY · by email**
under the name + sections line, so same-named drafts are distinguishable.
Backend list endpoint `/api/v1/tender-templates` now returns
`created_by_email` resolved in a single admin lookup (no N+1).
Testid: `tb-draft-meta-<id>`.

### 2. Audit Ledger — pagination numbers visible
`AuditPanel.jsx`: the pager (`Show / N / Prev · page / pageCount · Next`)
used to sit inside the table's `overflow-x-auto` wrapper and got clipped
on narrow screens. Table and pager are now sibling blocks — numbers always
visible.

### 3. BOQ "View" button — unmistakable visual feedback
`BOQTemplatesTab.jsx`: scrollIntoView already ran, but if the viewer was
already in the viewport (short template list) you'd see nothing move. The
viewer now flashes with an **amber ring + bold banner "↓ Viewing <name> —
details below"** for 1.2 s on every open. Testid: `boq-viewer-flash`.

### 4. Sidebar active state — solid primary pill
`AdminSideNavE.jsx` + `pmc-theme-e.css`: active row now has a **brass
background, bold on-brass text, and a 3-px inset left bar**. The active
item is also auto-detected from `window.location.pathname`, so pages that
forgot to pass the `active` prop (Billing, Escrow/EMD, Evaluation, Audit…)
now highlight correctly. Class: `.pmc-side__item--active`.

### 5. EMD badge in the Notices tender-picker rows
`NoticesPanel.jsx`: each picker row now shows an amber badge
"EMD ₹ 50,000 · 2%" (whichever fields the tender carries) so you can
compare EMD cost between tenders before linking one.
Testid: `notice-tpl-emd-<id>`.

## Deploy
- Backend: ship `pmc-backend-v52cf.zip` (list endpoint only; schema unchanged).
- Frontend: sync `pmc-frontend-v52cf-prod-build.zip` to S3, invalidate `/*`.

Files:
- `pmc-frontend-v52cf-prod-build.zip`
- `pmc-backend-v52cf.zip`
