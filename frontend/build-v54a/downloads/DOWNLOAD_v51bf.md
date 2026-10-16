# PMC Managers — Release v51bf (10 Oct 2026)

Frontend-only readability fix.

## Downloads
- Frontend: `/downloads/pmc-frontend-v51bf-prod-build.zip`
- Backend : unchanged — stay on v51be.

## What changed
- `frontend/src/index.css` — scoped CSS carve-out for the Vendor Intel
  surface (`[data-testid="admin-vendor-intel-panel"]` and
  `[data-testid="blacklist-dashboard-panel"]`) so the Option E theme can
  no longer wash slate text / bg-white into cream-on-cream. Covers:
    * Compliance triage KPI tiles + table (headers, rows, counts)
    * Manage modal (reason field, Whitelist button, evidence manager)
    * Evidence rows (filename, meta line, View/Download/Print/Delete)
    * Appeal cards + decision form
    * Inputs/selects/textareas and placeholders
- Verified in preview: triage panel now shows dark slate labels on white
  cards, REFRESH + MANAGE buttons legible, vendor summary table readable.

## Deploy
Frontend only: unzip into S3 (overwrite), CloudFront `/*` invalidation.
Backend stays on v51be.
