# PMC Managers v2 — Changelog

## 2026-09-19 · Batch #9b — Committee dissolve/create hotfix (v38 frontend, backend unchanged)
**Not yet deployed to AWS · awaiting user verification on preview**

### Root cause (P0)
`CommitteeList.jsx` used a raw `fetch()` call for the Dissolve + Resend-invite actions that
did NOT attach the `X-CSRF-Token` header. Backend responded with **HTTP 403 "CSRF token
missing or invalid"** for every dissolve attempt, so committees stayed `status="open"`
forever. That in turn made every subsequent **Form committee** attempt on the same tender
fail with **HTTP 409 "Open committee already exists for this tender"** — which the user
correctly reported as "committee is neither formed".

### Fix (v38 · main.<new-hash>.js)
- `CommitteeList.jsx` migrated from raw `fetch` to the shared `api` axios instance
  (`api.post()` auto-attaches `X-CSRF-Token` from the `csrf_token` cookie via the
  request interceptor in `lib/api.js`).
- Error toasts now show the actual backend detail via `formatApiError()` so future
  auth/CSRF regressions are visible to the operator.
- Prod cleanup: the 2 zombie committees still open on preview were dissolved via curl
  with CSRF header. Any zombie committees left on prod (pmcmanagers.com) will now
  dissolve cleanly from the UI once v38 is deployed.

### Verified in preview
- Dissolve committee button → HTTP 200 with `{"ok": true}` ✓
- Both zombie committees moved to "Recently closed / dissolved" ✓
- Form committee no longer blocked by 409 on the same tender ✓
- Production build compiles cleanly (`Compiled successfully`)

---

## 2026-09-19 · Batch #9 — Final bug-tracker clearance (v37 frontend · v22e backend)
**Not yet deployed to AWS · awaiting user verification on preview**

### Frontend (v37 · main.2d540e4e.js)
- **#21** — NoticesPanel: `isMasterAdmin` role check now case-insensitive and tolerates spaces/hyphens (`master admin`, `MASTER_ADMIN`, `Master-Admin` all accepted)
- **#28** — Added trilingual `panels.vendors.*` and `panels.registrations.*` keys (EN/RU/KK) to `lib/i18n-strings.js`; `VendorsPanel.jsx` and `RegistrationsPanel.jsx` fully rewired via `useI18n`
- **#29** — (paired with backend) fresh avatar visible on next tab immediately (no more stale `/me`)
- **#30** — New `EmailInput` and `PhoneInput` helpers in `FormPrimitives.jsx` with inline error styling; wired into `SectionB.jsx`
- **#49** — `RubricEditor.jsx` computes weightSum, per-criterion bounds, commercial weight range, and cutoff bounds; disables "Save rubric" and shows inline error list when invalid
- **#63** — `AdminVendorCreate` redirects to `/admin?tab=vendors` after successful create; `AdminDashboard` reads `?tab=` from URL on mount and on every `location.search` change
- **#84** — `VendorIntelPanel` table wrapped in `overflow-x-auto` container with `min-w-[640px]` for horizontal scroll on mobile

### Backend (v22e)
- **#29** — `/api/v1/admin/auth/me` + `/api/v1/vendor/auth/me` now emit `Cache-Control: no-store, no-cache, must-revalidate`
- **#49** — `models/evaluation.py::ScoringRubricIn` migrated from `model_post_init` (which silently swallows ValueError) to `@model_validator(mode="after")` so invalid rubrics return proper 422s. Also added `minimum_technical` 0-100 bound
- **#52** — `evaluations.submit_score` now reads `notice.{kind}_locked_at` and returns HTTP 409 with the lock timestamp when the envelope is locked; per-criterion max_score bound enforced (422 on overflow); commercial score forced 0-100

### Verified in preview
- Login → /admin OK
- `Cache-Control: no-store` on `/me` ✓
- Rubric weight=2 → 422 with clear message ✓
- Rubric min_tech=150 → 422 ✓
- Deep-link `/admin?tab=evaluation` lands on Evaluation panel ✓
- Publish checkbox enabled for master admin (`disabled = None`) ✓
- Production build compiles cleanly (`craco build` → `Compiled successfully`)

---

## Prior session (2026-02-19) — Batches #6, #7, #8 (v22c/d, v32/34/35)
Complete GoDaddy → Route 53 DNS migration. Same-origin frontend (bypasses Safari ITP). CloudFront apex→www 301 redirect. 100% purge of "Emergent" branding from prod bundles. Notice draft flow, vendor invite pipeline, and Tender Builder Clone/Delete/History fixes.

## Earlier session (2026-01) — Batches #1–#5 (v20/21, ≤v30)
57 bugs closed covering Auth, Bidding Ops, BOQ, Committee, Escrow, L1, Reverse Auctions, Registrations, Audit, Vendors invite pipeline, and Analytics anomaly scoring.
