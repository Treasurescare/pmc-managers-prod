# PMC Managers — Release v52u (frontend-only, hotfix)

## What changed since v52t
- **Tender Builder country dropdown** now loads the full 250-country
  master (`/api/v1/masters/countries`) instead of the 30-country
  licence-mapped subset. Previously admins saw only ~30 ISO codes
  (KZ/IN/etc. plus whatever had leaked onto an existing template);
  now the dropdown lists every country, sorted by name.

## Deferred (will land in v52v)
- Add Created by + Created from + Created to filters to:
  Work packages · Vendor requests · Bidding ops · Escrow EMD ·
  Evaluation · L1 comparison · Awards · Reverse auctions · DocuSign.
  Each panel will use the shared `MoneyFilterBar` with native min/max
  guards.

## Deploy

Backend: **no change** — v52t stays running.

Frontend:
1. Unzip `pmc-frontend-v52u-prod-build.zip`.
2. Upload the contents to your S3 bucket root (overwrite).
3. CloudFront → invalidation `/*`.
4. Hard-reload Tender Builder → the Country filter in the sidebar now
   lists all countries sorted alphabetically.
