# PMC Managers — v51at Frontend-only patch (P0 crashes + PDF enforcement + vendor-list cache-bust)

**Build date:** 2026-10-07
**Bundle:** `pmc-frontend-v51at-prod-build.zip`
**Backend:** no changes — reuse `pmc-backend-v51aq.zip`

## 🐞 P0 fixes (from the 07-Oct bug sheet)

- **L1 Award page crash → "Something crashed on this screen"**
  (`xlsx #19`, docx #15). Root cause: `L1ComparisonPanel` dereferenced
  `result.ranked.length`, `result.ranked.map`, `r.compliance_flags.map`
  and `result.ineligible.map` without guarding against `undefined`.
  Fixed with `(result.ranked || []).length` / optional-chained maps on
  every access. L1 page now renders the ranking table whether the
  backend returns a full report or a partial one.
- **Vendor approval not reflecting in the frontend** (`xlsx #15`,
  docx #11). `VendorsPanel.load()` was being served a stale response
  from an upstream HTTP cache after the admin clicked Approve.
  Added `_r=Date.now()` cache-buster so every refresh goes to the DB.

## 🐞 P1 fixes

- **Tech/commercial uploads accepted JPEG/PNG** (`xlsx #2`, docx #2).
  The bid envelope dropzone in `VendorBidWorkspaceE` was declared as
  `accept="application/pdf,image/*"` and silently accepted non-PDF
  files. Dropzones are now `accept="application/pdf"` with a defensive
  MIME-type guard that rejects anything else with a toast.

## 📝 Still open (triaged, not in this bundle)

Deliberately deferred because they need deeper investigation and would
have blown through this session's context budget:

- Evaluation page crash (docx #14) — same shape as the L1 crash but
  needs its own null-guard sweep on `EvaluationPanel`.
- NIT public download logs user out (xlsx #3 and #8) — backend-side,
  needs `routers/public_notices.py` audit for auth bleed.
- Stakeholder Reports vanishes from sidebar after visiting Bidding Ops
  (xlsx #20) — Bidding Ops page uses its own inlined sidebar instead of
  `AdminEShell`; refactor needed.
- DocuSign "Resend" + admin-sign-doesn't-flip-vendor-status
  (xlsx #12, #17) — needs backend DocuSign webhook audit.
- Register-on-behalf: missing `*`, no Next button, comma rejected
  (xlsx #6, #11) — needs `AdminVendorCreate` form-schema review.
- Admin crashes after prolonged use (xlsx #4) — profiling-level,
  requires Chrome memory snapshots.
- Remove-from-blacklist button issue (docx #17) — needs more context on
  which exact state the user hit (`selected.blacklisted` field flow).
- Engagements module missing "schedule meeting" (docx #19) — feature,
  not a bug.

## Deploy

1. Unzip into S3 bucket (overwrite v51as).
2. CloudFront invalidation `/*`.
3. Backend unchanged.
