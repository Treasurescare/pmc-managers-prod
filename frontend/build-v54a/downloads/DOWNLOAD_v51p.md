# PMC Managers — Release v51p (hotfix over v51o)

## Fix in this build

**Admin → Vendors page on iPhone (giant stretched buttons).**
v51o fixed the toolbar wrapping, but the buttons/search/status filters were
still rendered 120–145px tall. Root cause: a mobile rule meant to add 88px
bottom clearance on vendor-portal pages used the selector
`[data-testid^="vendor-"]`, which also matched every control inside the
admin Vendors panel (`vendor-search`, `vendor-invite-toggle`,
`vendor-bulk-invite-open`, `vendor-status-filter-*`…). Each of those got
88px of forced bottom padding.

The rule is now scoped to actual page roots (`[data-pmc-e-page^="vendor-"]`)
only, so:
- admin Vendors controls are back to normal height (26–62px measured),
- vendor-portal pages still keep the 88px bottom clearance so the fixed
  bottom tab bar never covers content.

Includes everything from v51o (Bidding Ops tabs/counts, row-card layout,
drawer scroll to Masters, toolbar wrap).

## Deploy
- Frontend: `pmc-frontend-v51p-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. **This supersedes v51o** — skip v51o if not deployed yet.
- Backend: unchanged since v51n (`pmc-backend-v51p.zip` identical, included
  for convenience).
