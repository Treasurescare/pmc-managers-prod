# PMC Managers — Release v56c (18 Jun 2026)

## What changed since v56b
1. **Joint account naming** — accounts with a blank display name now show a
   professional fallback label: **"<Institution> Escrow ••<last4>"** (or
   "Joint Escrow Account ••<last4>" when no institution). New accounts still
   require a display name. Shown in the list, the edit header and confirm dialogs.
2. **Escrow institution picker honours country scope** — in both the "New joint
   account" form and the "Edit signers" panel, each institution option is
   tagged with its country scope (e.g. "V52F Bank · MY/SG" or "· Global"), and
   a **country filter** appears above the dropdown to narrow the list to
   global-or-matching institutions. (The filter stays hidden until at least one
   institution has a country scope set — configure it in Escrow institutions →
   select institution → Country scope.)

## Artifacts
- Backend: `pmc-backend-v56c.zip`
- Frontend: `pmc-frontend-v56c-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk, wait green.
2. Frontend build → S3 root (overwrite). 3. CloudFront invalidation `/*`.
4. Footer should read **Frontend v56c · Backend v56c**.
