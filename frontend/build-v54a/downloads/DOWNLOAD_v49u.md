# PMC Managers Limited — Release v49u

## What's fixed
### Notifications — vendor alerts page + notification bells
User report: "notifications not working."

Root causes (frontend only — backend was storing notifications correctly):
1. **Vendor Alerts page always empty** — `useVendorAlertsLive` called
   `/api/v1/notifications`, which requires an ADMIN session
   (`current_admin`). Vendors got 401, the catch swallowed it, and the
   page kept its 5 static mock rows forever.
2. **Notification bell completely dead** — `.pmc-bell` on vendor and
   admin pages had no click handler and `.pmc-bell__n` was hardcoded 0.

Fixes:
- `useVendorAlertsLive` now calls `/api/v1/notifications/vendor/mine`,
  renders real rows (subject, body preview, relative time, unread
  highlight, View action), and replaces the static "9 alerts · 2 need
  action" heading + tab counts with the live totals.
  Testid per row: `vendor-alert-row`.
- `PmcLinkPatcher` — bell click navigates: vendor → `/vendor/alerts`,
  admin → `/admin/e/events`.
- `PmcLinkPatcher` — on every route change, fetches the unread count
  (vendor or admin endpoint by page) and paints every `.pmc-bell__n`
  badge; badge hides itself at 0.
- "Mark all read" on the alerts page already hits the vendor endpoint
  and now pairs with the real rows.
- Service-worker cache bumped to `pmc-shell-v49u-rev1`.

Verified on preview: vendor sign-in shows 50 real alert rows, bell
badge = 10 unread; admin bell badge populated, click → events page.

## Bundles
* Frontend: `pmc-frontend-v49u-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront;
  `main.99235cc5.js`).
  **Includes v49r (download links) + v49s (sign-in⇄register) + v49t
  (dashboard counts)** — deploy v49t's replacement, this one.
* Backend: unchanged — `pmc-backend-v49q.zip` (already live).

## Deploy — Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49u-prod-build.zip`.
2. `aws s3 sync --delete` the contents into your S3 bucket root.
3. Invalidate CloudFront: paths `/*`.
4. Verify: vendor portal → bell shows unread count, Alerts page lists
   real notifications; admin dashboard bell → Events & alerts.

## Rollback
Roll back to `v49q` if needed. No API, route or schema changes.
