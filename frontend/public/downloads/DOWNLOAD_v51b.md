# PMC Managers — Release v51b (cumulative v50m → v51b)

## Features in this build
- **Footer language switcher** (#123): EN/RU/KZ dropdown now sits at the
  bottom-right of every page, mirroring the one in the top header.
- **Tender Builder country mode** (#99): when a country is selected the
  admin picks between "This country only" (default) and "All templates".
- **DocuSign Reassign + Archive**: every envelope row gets ↪ Reassign
  (new signer email/name + audit reason) and ⌧ Archive / ⟲ Restore. A
  reassigned envelope resurfaces for the new vendor on their next
  Signatures page load. Archived envelopes are hidden from
  /api/v1/docusign/mine so vendors never see orphaned items.

## Deploy
- Backend: `pmc-backend-v51b.zip` → EB (new reassign/archive endpoints)
- Frontend: `pmc-frontend-v51b-prod-build.zip` → S3 + CloudFront `/*`
