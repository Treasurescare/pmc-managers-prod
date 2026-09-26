# PMC Managers v2 — Release v47g (Sep 2026)

## What is in this release

### 1 · Admin bid detail view (finalized from v47f)
- Every row in Admin → Bidding now has a **View** button opening a full bid detail modal:
  vendor identity, notice context, commercial breakdown (price, EMD due/paid/source),
  technical & commercial notes, **all uploaded documents** (inline preview for images/PDF,
  open-in-new-tab for everything else), workflow history, and Print/Save-PDF.
- Backend: `GET /api/v1/bids/admin/{bid_id}` (admin/reviewer/escrow/certifier/legal/accounting/committee roles).

### 2 · Platform-wide pagination (10 / 20 / 30 / All)
- Reusable `ListPager` (`useListPager`) with page-size chooser, prev/next, and "x–y of z" indicator.
- Rolled out to **every major listing**:
  - Admin console: Bids, DocuSign envelopes, Registrations, Vendors, Notices, Live Auctions,
    Engagements, Billing transactions, Audit log, Vendor Intel, Meetings, Masters (Staff /
    Companies / Tenants), BOQ templates, Contracts, Product Catalog, Escrow EMD ledger,
    Corrigenda (active + withdrawn).
  - Vendor portal: Open tenders, My bids, Signature envelope history.
- Each pager has a unique `data-testid` (e.g. `list-pager`, `ds-pager`, `vendor-pager`,
  `notice-pager`, `staff-pager`, `vendor-bid-pager` …) for regression testing.

### 3 · DocuSign envelope actions (finalized from v47f)
- Per-row **View** (envelope detail modal), **Resend** (only on unsigned envelopes —
  sent/delivered), **Print / download signed PDF** (only on completed envelopes).
- Backend: `POST /api/v1/docusign/envelopes/{id}/resend` (400 on completed/declined/voided),
  `GET /api/v1/docusign/envelopes/{id}/combined-pdf`.
- Bug fixed: the v47f DocuSign pager hook was invoked conditionally inside a render IIFE and
  its controls were discarded — the pager never rendered and the panel could crash on
  empty→non-empty transitions. Now hoisted to top level.

## Verification
- Testing agent (iteration_26): **100% backend, 100% frontend pass**.
  - 6/6 backend contract tests (admin bid detail, resend status rules, 404s, combined-pdf no-crash).
  - Bid modal open/close verified; 12 bids paginate 10 + 2 across 2 pages.
  - All 20 pagers render across admin + vendor panels; Resend/Print visibility rules verified.
- Production build scanned: **0 preview-URL references** (built with `REACT_APP_BACKEND_URL=`
  empty for same-origin relative API paths).

## Bundles
- `pmc-backend-v47g.zip` — Elastic Beanstalk (Dockerfile, Dockerrun.aws.json, .platform, backend/).
- `pmc-frontend-v47g-prod-build.zip` — S3/CloudFront static build (excludes downloads/).

## Deploy notes
- Frontend: upload **all** files including `static/`; set `index.html`, `service-worker.js`,
  `manifest.json` to no-cache. Service worker cache bumped to `pmc-shell-v47g`.
- Backend: no new env vars required.
- DocuSign resend/print require valid DocuSign JWT config in EB; without it the API returns a
  well-formed 502 (contract verified — no crash).
