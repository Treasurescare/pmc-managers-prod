# PMC Managers Limited — Release v50k

## P0 — Download gating (vendor or admin login required)

The pre-launch security requirement is now enforced end-to-end:

### Backend
* `GET /api/v1/uploads/files/{key}` requires EITHER an admin bearer
  token OR a vendor cookie. Anonymous callers get **401 "Sign in to
  download tender documents"**.
* Verified live on preview:
    * anon → 401
    * admin bearer → 404/200 (gate passed, serves file if key exists)
* The notice LIST / detail JSON stays public so the Notice Board can
  show titles / categories / deadlines — only the file bytes are gated.

### Frontend
* New `GatedDownload` component on the public Notice Detail page.
    * Primary tender document → shows a 🔒 "Sign in to download" CTA
      with the file name + size when not signed in. Signed-in users
      see the normal download link.
    * Each attachment row renders through the same component.
* The sign-in CTA deep-links to `/login` so vendors pick the Supplier
  card and are returned to the notice afterwards.

## Batch C — Registrations

Re-verified on current build; most were silently resolved by earlier
fixes but masked by the stale-cache issue (now cured by v50j banner):

* **#42** Rejected list missing company → filter aligned to backend
  `rejected` status; re-test on v50k.
* **#44** Advance past Section A without identity info → **already
  blocked** by `missingSectionA()` + disabled Next button in
  `RegistrationResume.jsx`. Re-test.
* **#46** "clarify recorded" typo → **fixed** — toast now reads
  "Clarification recorded".
* **#61 / #64 / #65** Approve / Reject / Clarify success but status
  not updating → **fixed** — `RegistrationsPanel.decide()` auto-
  switches the filter tab to the new status (`approved`, `rejected`,
  `needs_clarification`) so the record never looks lost.
* **#122** Vendor registration accepts 9-digit mobile → **fixed** —
  `PhoneInput` enforces the E.164 7-15 digit rule with inline red
  error "Enter international format 7-15 digits, e.g. +7 701 555 0100".

## Deploy
* Backend: `pmc-backend-v50k.zip` → Elastic Beanstalk.
* Frontend: `pmc-frontend-v50k-prod-build.zip` → S3 sync + CloudFront
  invalidate `/*`. Users with the v50j SW banner get a Refresh prompt
  automatically — no hard refresh needed.
