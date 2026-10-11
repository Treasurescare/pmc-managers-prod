# PMC Managers · Release v52by

**Date:** 11 Oct 2026 · **Supersedes:** v52bx

## What's new in v52by

### 1. Round-6 #64/#59/#60 — Reverse Auction create & start
- **Backend `ReverseAuctionIn`**: `floor_price` now defaults to `0.0` and `min_decrement` to `1.0`, so draft creation no longer fails with a silent "field required" 422 when either input is left blank.
- **Frontend `LiveAuctionsPanel.create()`**: every numeric field is now coerced to `Number()` (never NaN), the client validates `starting_price > 0` and `floor < starting` with inline toasts, and the new draft is **optimistically prepended to the list** so admins see it instantly (no more "draft created but not listed").
- **Start button**: no longer client-side disabled. Clicking Start always calls the backend, which already returns a clear 400 naming the exact gate ("Need at least 2 registered participants, currently N"). Admins now get *feedback* instead of a dead button.

### 2. Round-6 #48/#57 — BOQ Excel + PDF Export
- Two new authenticated endpoints:
  - `GET /api/v1/boq/templates/{id}/export.xlsx` → openpyxl workbook with Sl.No, Description, Unit, Qty, Rate, Line Total, UNSPSC, Remarks.
  - `GET /api/v1/boq/templates/{id}/export.pdf` → WeasyPrint A4 PDF with branded header and totals.
- Frontend `boqApi.exportXlsx(id, name)` / `boqApi.exportPdf(id, name)` use the standard `downloadAuthedFile` blob pattern.
- Two new buttons on every BOQ template row in `BOQTemplatesTab`:
  - `boq-export-xlsx-<id>` → "Export Excel"
  - `boq-export-pdf-<id>` → "Export PDF"

### 3. Round-6 #49 — Corrigendum withdraw refresh
`CorrigendaPanel.withdraw()` now does an **optimistic local flip** (sets `is_active: false`, stamps `withdrawn_at` + `withdrawn_reason` on the row in state) before the refetch, so the withdrawn corrigendum leaves the active table immediately — no page reload needed.

## Deployment
- Backend EB: upload `pmc-backend-v52by.zip`.
- Frontend S3 + CloudFront: unzip `pmc-frontend-v52by-prod-build.zip`, sync, invalidate `/*`.

## Verify after deploy
1. Admin → Reverse Auctions → create a draft leaving floor_price blank → draft row appears immediately with `0/2` participants.
2. Click Start on a draft with <2 participants → toast surfaces the backend's "Need at least 2 registered participants" message (no more silent no-op).
3. Admin → BOQ → every template row shows **Export Excel** and **Export PDF** buttons; both download named files with correct content.
4. Admin → Corrigenda → pick a notice → Withdraw a corrigendum with a reason → it disappears from the Active list and appears in the Withdrawn list immediately.
