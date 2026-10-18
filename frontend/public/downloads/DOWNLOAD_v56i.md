# PMC Managers — Release v56i (18 Jun 2026)

## Fix — the "HTTP 422 — Input should be release_to_contractor…" error
What you saw: you picked **Release → Contractor** but got a 422 toast and the PMC
signature didn't update.

Why: your PMC side had already signed **acknowledge_receipt** (via DocuSign), so
the release dropdown initialised to that stale value. The dropdown *looked* like
"Release → Contractor" but its underlying value was still `acknowledge_receipt`,
which is not a valid *release* action → the server rejected it with 422.

Fix: the dropdown now always defaults to a valid release action
(`release_to_contractor`). Pick your action and click **Update my signature** —
it will record `release_to_contractor`, matching the institution, and the admin
RELEASE button unlocks.

(The RED inline message "⚠ Action mismatch…" is NOT an error — it's the system
correctly explaining that PMC signed *acknowledge* while the institution signed
*release to contractor*, so they must match. Once you re-sign the release action
it clears.)

## New — "Completed / processed by you" view (certifier & all staff)
After a certifier (or any staff role) Accepts + comments, the item correctly
advances to the next stage and leaves the work queue — which looked like it
"just moved away". There is now a **Completed** tab in the sidebar showing every
item you processed, with the action, status transition, YOUR comment and the
timestamp — i.e. your personal audit trail. (All of this was already captured in
the admin Audit ledger + the bid's workflow history; now staff can see their own.)

## Artifacts
- Backend: `pmc-backend-v56i.zip`  ·  Frontend: `pmc-frontend-v56i-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. **CloudFront `/*` invalidation** (critical — or the old bundle keeps loading).
4. Hard refresh. Footer must read **v56i / v56i**.
