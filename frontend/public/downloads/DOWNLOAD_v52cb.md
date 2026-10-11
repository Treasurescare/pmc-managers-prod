# PMC Managers — Frontend v52cb (11 Oct 2026)

## What's in this build (3 user-reported fixes)

### 1. Registrations — "Edit sections" link appears attached to the next vendor
`RegistrationsPanel.jsx` — the row divider line was on the vendor-name
button, so the "Edit sections (opens vendor view in new tab)" link sat
*below* the divider and visually attached itself to the next vendor card.
Moved the border onto the row wrapper so each card (name + email + status +
edit link) is one contiguous visual group. New testid `reg-card-<id>`.

### 2. Registrations — Back button lands on main public tab
`RegistrationResume.jsx` — when an admin opens "Edit sections" in a new
tab (`?from=admin`), the resume page now shows an explicit "← BACK TO
REGISTRATIONS" button at the top of the stepper. Click → `window.close()`
first (closes the tab), falls back to `/admin/e/registrations` if the
browser refuses. New testid `reg-resume-back-admin`.

### 3. Evaluation — tender number lookup didn't work
`EvaluationPanel.jsx` — the "Tender notice ref" field was a plain text
input, so typing "18" didn't surface PMC-NOT-2026-0018. Replaced with a
proper notice picker: loads every notice from `adminApi.listAllNotices`
and renders a dropdown that filters live on substring of **ref AND title**.
Typing "18" now shows `PMC-NOT-2026-0018 — TEST_committee_notice_5bb539`
plus any title containing "18"; clicking a row locks the full ref into
state. Friendly no-match message when the fragment matches nothing. New
testids `eval-notice-picker`, `eval-notice-opt-<ref>`, `eval-notice-nomatch`.

## Deploy
- Backend: unchanged from v52bz (`pmc-backend-v52bz.zip`).
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.

File: `pmc-frontend-v52cb-prod-build.zip`
