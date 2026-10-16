# PMC Managers — Release v51a (cumulative v50m → v51a)

## Fixes in this build
- **Masters tab bar realigned**: tab labels no longer wrap onto two lines
  ("LEGAL ENTITY TYPES" etc.); single horizontally-scrollable row with
  consistent spacing. Verbose "(moved → Market)" suffixes removed.
- **Instant deactivate/reactivate**: Legal entity types (and the same
  class of bug anywhere) — the row flips immediately on click with
  rollback if the server call fails. Previously the refetch could return
  a CloudFront-cached pre-mutation list, forcing a hard refresh.
- **API cache safety (root cause)**: every /api/ response now sends
  `Cache-Control: no-store, no-cache, must-revalidate` so CloudFront can
  never serve a stale list after a mutation.

## Deploy (backend REQUIRED for the cache fix)
1. `pmc-backend-v51a.zip` → Elastic Beanstalk
2. `pmc-frontend-v51a-prod-build.zip` → S3 + CloudFront invalidate `/*`
