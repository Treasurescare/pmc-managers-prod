# PMC Managers — Release v50q (cumulative: v50m → v50q)

## New in this build

### Bug #6 — Vendor activation verified end-to-end
Full flow re-tested via API: admin-create (verify mode) → vendor appears in
list → Activate with set_password → vendor signs in (must_change_password
enforced). No code change needed — the flow works on current backend.

### Bug #60 — Blank registration form regenerated
New branded PMC blank registration form (2-page PDF: sections A–E + K
declarations with signature block) generated and uploaded as the live
registration template. Download endpoint verified returning
`Content-Type: application/pdf` with a valid %PDF payload.

### DocuSign — Admin "Archive PDF" repair tool
- `POST /api/v1/docusign/envelopes/{id}/archive-pdf` (admin) fetches the
  combined signed PDF from DocuSign and stores it in PMC storage
  (`docusign-archived/{id}.pdf`).
- Vendor + admin download endpoints now serve the archived copy first, so
  envelopes DocuSign can no longer serve are repaired from the console —
  no DocuSign support ticket needed.
- `/api/v1/docusign/mine` marks `has_document=true` for archived envelopes.
- Admin console → DocuSign: new "⇩ Archive" button on completed envelopes
  (list row + view modal).

### EMD Master Editor UI (Admin → Masters → EMD rules)
- New tab under Masters with list/create/edit/delete for EMD & fee rules:
  name, country (dropdown), kind (EMD / tender fee / registration /
  subscription…), optional category scope, currency, active toggle, notes.
- Slab editor: min/max tender value ranges, fixed or percentage fee, with
  pct min / pct max caps.
- Quick calculator: pick a rule + tender value → computed fee with the
  matching slab shown.
- Verified: 2% of 1.2M = USD 24,000 (within 5k–50k caps); 100k → fixed
  USD 5,000.

## Carried from v50m–v50p
Vendor portal rewrite (Home/Tenders/Signatures/Account/KYC on live APIs,
real Router links), profile-edit approval queue (structured address,
company name, phone country validation, email verify+approve), avatar
dropdown, licences CRUD, PmcLinkPatcher React-page guard, SEC-001/SEC-003
fixes, Batch D admin pages (Reverse auctions, Stakeholder reports,
L1 dropdown, escrow validation, anomaly contrast), category request flow.

## Deploy
- Backend: `pmc-backend-v50q.zip` → EB.
- Frontend: `pmc-frontend-v50q-prod-build.zip` → S3 + CF invalidate.
- No new env vars required.
