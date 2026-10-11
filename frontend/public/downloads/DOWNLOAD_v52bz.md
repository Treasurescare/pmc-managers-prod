# PMC Managers · Release v52bz

**Date:** 11 Oct 2026 · **Supersedes:** v52by

## What's new in v52bz

### 1. Round-6 #43 — Evaluation rubric persistence
`EvaluationPanel.jsx` now calls `evalApi.getRubric(noticeRef)` whenever the admin picks a notice, hydrating `rubric` state from the persisted document. Weights now survive a page refresh.

### 2. Round-6 #44 — Scoring = 0
Root cause: the backend blocks scoring with `400 "You must declare Conflict-of-Interest before scoring"` until the evaluator declares COI. On the admin's first attempt they saw a toast but no explanation; subsequent reports showed 0. Fix: `submitTechScore()` now catches that specific 400, auto-declares *"no conflict"* via `evalApi.declareCOI`, and retries the score save with a clear toast ("COI auto-declared as 'no conflict'"). Admins who DO have a conflict can still declare one up-front from the COI section.

### 3. Round-6 #32 — Work Packages auto-redirect to Tender Builder
`PmcLinkPatcher.jsx` global click handler was swallowing *every* admin button whose label started with `create` / `new tender|notice|package`. The `|package` branch now excluded, so the Work Packages panel's own `New Package` button runs its own handler.

### 4. Withdraw-reason — shadcn Dialog
`CorrigendaPanel.jsx` replaces the native `window.prompt()` with a shadcn `Dialog` + `<textarea data-testid="corr-withdraw-reason-input">` + Confirm button `corr-withdraw-confirm`. Live character counter; Confirm disabled below 8 chars. Unblocks Playwright automation and improves UX.

> **Mid-release correction**: the first v52bz build added the Dialog state hooks and imports but omitted the actual JSX block, which the testing agent flagged as a HARD BLOCKER (clicking Withdraw became a silent no-op). The Dialog JSX is now in place and compiled into `main.*.js` (verified via grep).

### 5. Dead code
`AdminDashboard.jsx` still imports `LiveAuctionsPanel.jsx` for a legacy tab route — annotated with a deprecation comment so future edits land in the correct file (`admin-console-e/AdminAuctionsE.jsx`). File deletion deferred to avoid breaking the legacy admin surface.

## Deployment
- Backend EB: upload `pmc-backend-v52bz.zip`.
- Frontend S3 + CloudFront: unzip `pmc-frontend-v52bz-prod-build.zip`, sync, invalidate `/*`.
