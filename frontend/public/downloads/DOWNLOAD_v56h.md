# PMC Managers — Release v56h (18 Jun 2026)

## ⚠️ If v56g "didn't change anything": it was a CloudFront cache
Your footer read **Frontend v56f · Backend v56g** → the browser/CDN was still
serving the OLD frontend bundle. After uploading the frontend build you MUST run
a CloudFront **`/*` invalidation** (and hard-refresh) or the old index.html keeps
loading the old hashed JS. v56h won't appear until you invalidate.

## 1. Staff portal restyled to the standard Option-E theme
The staff portal now uses the SAME palette as the admin console & escrow portals
(cream paper, emerald-green sidebar chrome, brass accents) via the theme tokens —
fully readable, dark-mode aware. A left **sidebar** (Overview · Escrow signatures ·
Work queue · Site inspections) replaces the old flat list.

## 2. PMC officer can now sign the RELEASE action (fixes the stuck release)
Root cause of "release blocked": the PMC officer could only *acknowledge* via
DocuSign, while the escrow officer signed *release_to_contractor* — two different
actions, so the RELEASE button stayed greyed (dual-control requires the SAME
action on both sides). The PMC officer's staff portal now has an **action-based
signing panel** (Release → Contractor / Refund → Vendor / Forfeit + comment),
exactly like the escrow officer portal. Once BOTH officers sign the same action,
an admin fires the final release.

Process recap for PMC-BID-2026-00060:
1. PMC officer (stafftest@pmcmanagers.com) → Staff portal → Escrow signatures →
   pick **Release → Contractor** → Sign.
2. Escrow officer (sakina@gdihelite.com) already signed release_to_contractor.
3. Admin → Escrow/EMD → the **RELEASE** button is now active → fires the release.
   (Admin is NOT an officer and cannot sign — admin only triggers the release.)

## 3. Universal CSRF fix (certifier Accept + all staff actions)
The "CSRF token missing or invalid" 403 (certifier Accept, escrow signers, etc.)
is fixed: the auto-recovery now re-issues a session-bound token and retries
WITHOUT letting a stale cookie clobber it. Applies to every staff action.

## 4. Certifier flow
Certifier bid rows now have a **comment** box; Accept & forward advances the bid
to the next stage (Legal) and notifies the next role. Every step is recorded in
the Audit ledger + the bid's workflow history (visible in the admin console).

## Artifacts
- Backend: `pmc-backend-v56h.zip`  ·  Frontend: `pmc-frontend-v56h-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. **CloudFront `/*` invalidation** (critical). 4. Hard refresh. Footer → v56h / v56h.
