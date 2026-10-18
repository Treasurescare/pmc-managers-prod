# PMC Managers — Release v56j (18 Jun 2026)

## 1. Admin Audit drill-down → CSV export per officer
The Audit ledger already had an **Actor email** filter (type a person's email to
see only their events). v56j adds an **Export CSV** button next to the results
count — it exports exactly what's on screen, so filtering by one officer and
clicking Export gives you that person's full decision history as a CSV.
(Admin console → Overview → Audit ledger.)

## 2. Staff "Completed" tab → date / action filters + CSV
The staff Completed tab now has **From / To date** filters, an **Action** filter,
a **Clear** button, and **Export CSV** of the filtered decisions (bid, action,
status transition, comment, timestamp) for easy record-keeping.

## 3. Signed-action mismatch guardrail
When a PMC officer signs a release action that DIFFERS from what the escrow
institution already signed, a confirmation now warns: *"The escrow institution
already signed X, but you chose Y. Both officers must sign the SAME action or the
release stays blocked. Sign anyway?"* — preventing the mismatch that previously
blocked releases.

## Note
PMC-BID-2026-00060 is already **RELEASED_TO_CONTRACTOR** in production — the full
EMD → dual-signature → release flow is working end-to-end. 🎉

## Artifacts
- Backend: `pmc-backend-v56j.zip`  ·  Frontend: `pmc-frontend-v56j-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. **CloudFront `/*` invalidation** (critical). 4. Hard refresh → footer v56j / v56j.
