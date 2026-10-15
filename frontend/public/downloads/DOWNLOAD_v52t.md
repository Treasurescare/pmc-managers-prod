# PMC Managers — Release v52t (frontend + backend)

## What changed since v52r
- **Tender date-chain validation** (both sides, shared rule set).
  Enforced order: submission end ≥ today · publish ≥ today · pre-bid ≥
  publish · doc-dl start ≥ pre-bid · doc-dl end ≥ doc-dl start ·
  clarification start ≥ doc-dl end · clarification end > start · bid
  submission start ≥ clarification end · submission end ≥ start · new
  **Bid Award Date** header field ≥ submission end.
- **Tender Builder** now shows a live red "Date order problems" hint box in
  the Critical Dates group, and blocks "Create notice" while violations
  exist. Drafts still save.
- **Corrigendum publish** rejects past new deadlines, past deadline
  amendments, and pre-bid/clarification-close amendments landing after the
  effective submission deadline. Live toast hints in the admin form plus
  server-side enforcement.
- **Notice create** rejects past submission deadlines and pre-bid dates
  after the deadline. **Notice edit** enforces ordering only (legacy past
  dates still editable).
- **Every start/end date filter pair** across the admin console now uses
  native `min`/`max` guards: Audit ledger, Notices list, Escrow
  institutions (added in v52t); BOQ & contracts, Profile-change requests,
  Category requests, MoneyFilterBar (Billing etc.) already had them.

## Deploy

1. **Backend** — upload `pmc-backend-v52t.zip` to Elastic Beanstalk →
   Upload and deploy. `Dockerfile` at root, no `.env`, no nested
   `backend/`, no `docker-compose.yml` (AL2023 Docker contract).
2. **Frontend** — unzip `pmc-frontend-v52t-prod-build.zip` and upload the
   contents to your S3 bucket root (overwrite). Then CloudFront →
   invalidation `/*`.
3. Hard-reload any Tender Builder draft → the Critical Dates group now
   shows the new **Bid Award Date** field and the red hint box reacts
   instantly to wrong dates.
