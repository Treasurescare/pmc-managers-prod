# PMC Managers — Release v50y (cumulative v50m → v50y)

## Fixes in this build
- **Masters → Legal entity types (new tab)**: full CRUD for the Legal
  entity type dropdown. Pre-seeded with LLC / JSC / Sole Proprietorship /
  Partnership / Branch / Other. Supports EN/RU/KZ names + country scope.
- **Section A dropdown now reads from the master**: vendor registration
  Section A pulls `/api/v1/masters/legal-entity-types/public`; falls
  back to the hard-coded list only if the API is unreachable.
- **Section A/B/C View & Download now work**: added
  `GET /api/v1/registrations/{id}/documents/{slot}/file?token=xxx` with
  magic-token auth. The old `/uploads/files/{key}` route required a
  signed-in session, so vendors mid-registration always hit 401 and
  View/Download appeared broken.
- **Section D "Business verticals" → multi-select from UNSPSC Categories
  master**: searchable list fed by `/api/v1/masters/categories/public`,
  chips for selected items, UNSPSC codes visible. Replaces the earlier
  free-text comma-separated input.
- **Admin: view/download registration documents before approving**:
  `RegDocCard` now hits a new `/admin-file` variant that fetches by
  registration id + slot — no more key-path CDN quirks.

## Deploy
- Backend: `pmc-backend-v50y.zip` → EB (new /legal-entity-types router +
  registration doc endpoints; backend MUST be deployed for this release)
- Frontend: `pmc-frontend-v50y-prod-build.zip` → S3 + CloudFront `/*`
