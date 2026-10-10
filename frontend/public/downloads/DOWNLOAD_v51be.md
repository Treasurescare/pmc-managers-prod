# PMC Managers — Release v51be (10 Oct 2026)

Follow-on fixes + feature after v51bd.

## Downloads
- Frontend: `/downloads/pmc-frontend-v51be-prod-build.zip`
- Backend : `/downloads/pmc-backend-v51be.zip` (EB root layout)

## What changed

### Bug fix — CSRF resilience (the "HTTP 403 CSRF missing" on Blacklist)
Some browser/profile combos silently drop the JS-readable `csrf_token`
cookie (strict ITP / 3rd-party cookie partitioning / private browsing).
Without the cookie the request interceptor had nothing to echo in
`X-CSRF-Token`, so every POST/PUT/DELETE 403'd. The front-end now also
caches the `csrf_token` returned in the admin/staff/vendor login JSON
and uses it as a fallback when the cookie is unreadable. Caches are
cleared on logout. (`frontend/src/lib/api.js`)

### Feature — Appeal decision workflow
- `POST /api/v1/vendor-intel/blacklist/{vendor_ref}/appeals/{idx}/decision`
  (admin-only, CSRF). Body: `{decision: "approved"|"rejected", note,
  whitelist}`. On approve+whitelist, the blacklist is deleted. Audit log
  entry + vendor email (`notify._notify_appeal_decided`) + admin
  `notify_role` fired for every outcome.
- Admin modal: each pending appeal now renders an inline form with
  Approve / Reject buttons, decision-note textarea, and an "Also
  whitelist on approval" checkbox. Decided appeals show the status
  badge, who decided, when, and the decision note (also audit-logged).

## Verification (preview, end-to-end curl)
- Reject appeal #0 → `appeals[0].status="rejected"`, `decided_by`,
  `decided_at`, `decision_note="Documents insufficient"` persisted.
- Approve appeal #1 with `whitelist:true` → `{ok:true, whitelisted:true}`,
  vendor's `/my-blacklist` now returns `{blacklisted:false}`.
- Invalid decision → `422`. Decision on an already-whitelisted vendor → `404`.

## Deploy order
1. Backend v51be first.
2. Frontend v51be after (CloudFront `/*` invalidation).
