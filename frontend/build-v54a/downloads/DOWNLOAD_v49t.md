# PMC Managers Limited — Release v49t

## What's fixed
### Admin dashboard numbers now match the linked lists
User report: dashboard shows 0 drafts awaiting approval (actual 29),
notices published 20 (actual 29), technical evaluation 1 (list shows
13), awarded 3 (list shows 13), bids waiting 6 (list shows >13).

Root causes in `useAdminDashboardLive` (frontend only — backend was
returning correct data):
1. **Drafts=0 & Published capped at 20** — the hook called
   `publicApi.listNotices({})` which server-side filters
   `is_published: True` (so drafts NEVER came back) and defaults to
   `limit=30` (so a DB with ~29 published notices returned ~20).
2. **Technical eval "1"** — filter matched only 2 statuses of the 8
   real evaluation-phase statuses, so most evaluation bids were
   ignored.
3. **Commercial eval / Awarded** — same too-narrow filter pattern.
4. **KPI "Active contracts" figure** used a `form_of_contract` heuristic
   on published notices (produced arbitrary numbers unrelated to the
   awarded list).

Fixes (`frontend/src/lib/pmcELiveData.js` + AdminDashboardE.jsx):
- Switched to `GET /api/v1/notices/admin/all?limit=500` — includes
  drafts and returns everything. Falls back to the public list if the
  admin cookie has not landed yet.
- `Draft`, `Published`, `Bidding`, `Closing this week`, `Approvals
  queue` counts now derive from that complete list.
- Broadened stage V/VI/VII filters:
  - **Technical eval** = emd_paid, escrow_accepted, admin_flagged,
    certifier_cleared
  - **Commercial eval** = legal_cleared, accounting_cleared
  - **Awarded** = awarded, closed
- "Bids awaiting EMD" attention pill now includes blank-status bids
  and `submitted` alongside `emd_pending`.
- KPI "Active contracts" now shows the actual awarded-bid count
  (same number the Awards page lists).
- Service-worker cache bumped to `pmc-shell-v49t-rev1`.

## Bundles
* Frontend: `pmc-frontend-v49t-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront).
  **Includes the v49r download-link fix AND the v49s sign-in⇄register
  cross-links** — deploy v49t instead of v49r or v49s.
* Backend: unchanged — `pmc-backend-v49q.zip` (already live).

## Deploy — Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49t-prod-build.zip`.
2. `aws s3 sync --delete` the contents into your S3 bucket root.
3. Invalidate CloudFront: paths `/*`.
4. Verify at `/admin/e/dashboard`:
   - "Drafts awaiting approval" and the pipeline **Draft** stage both
     read the same non-zero count.
   - **Published** stage count = the number rows on `/admin/e/notices`
     with the Published pill.
   - Pipeline **Technical eval / Awarded** counts match the tabs on
     `/admin/e/bidding`.

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
