# PMC Managers — Release v56l (18 Jun 2026)

## 1. Gate UI hint — "Release to contractor" locked until awarded
In the staff portal's escrow signing panel, the **Release → Contractor** option
is now **greyed/disabled** ("— locked until awarded") until the bid is `awarded`.
When it's selected the Sign button is disabled, reads "Locked until awarded" and
shows a tooltip, plus a warning hint naming the current bid status. Refund →
Vendor and Forfeit stay available. The signatures API now returns each row's
`bid_status` so the UI enforces the same rule as the backend (no surprise 409).

## 2. Release confirmation email (+ signed PDF)
When an admin fires a release, a confirmation email (amount, bid, beneficiary,
authoriser, memo) is now sent to **both officers AND the beneficiary** (the
vendor on the bid), with the signed PDF attached when available. Best-effort —
never blocks the release.

## QA
Testing agent iteration_96: 100% pass on both layers of the gate (UI lock +
backend 409) and the staff Completed filters/CSV. No blockers.

## Artifacts
- Backend: `pmc-backend-v56l.zip`  ·  Frontend: `pmc-frontend-v56l-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. **CloudFront `/*` invalidation**. 4. Hard refresh → footer v56l / v56l.
