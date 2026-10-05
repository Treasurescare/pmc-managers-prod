# PMC Managers — Release v51q (cumulative, supersedes v51o/v51p)

## Changes in this build

### Admin → Vendors: detail opens right where you tap (mobile)
Previously, tapping a vendor in the list on a phone rendered the KPI/KYC
detail panel at the very bottom of the page (the two-column desktop layout
simply stacked). Now the detail expands **inline, directly below the tapped
row** — accordion style. Desktop (≥1024px) is unchanged: the detail still
opens in the right-hand column.

### Admin → Masters: all tabs visible, active one highlighted
The Masters tab bar was a single horizontally-scrolling row — only the
active tab was obvious, the rest were hidden off-screen. The bar is now a
wrapping chip grid: all 13 masters visible at once. Active chip = solid
navy with white text; inactive chips = outlined navy on white.

### Also included (from v51o + v51p)
- Bidding Ops: mobile tabs wrap, tab counts always match visible rows,
  row-card checkbox alignment fixed.
- Admin drawer scrolls to Masters / Events on iOS (100dvh fix).
- Admin Vendors toolbar wraps 2-up; giant-button padding bug fixed
  (88px bottom-tab clearance rule scoped to vendor-portal page roots).

## Deploy
- Frontend: `pmc-frontend-v51q-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. Supersedes v51o/v51p — deploy this one only.
- Backend: unchanged since v51n (`pmc-backend-v51q.zip` identical,
  included for convenience).
