# PMC Managers — Release v51u (cumulative, supersedes v51o–v51t)

## Hotfix in this build

### Company & KYC (and any other dialog) — "Cancel" no longer crashes the panel
The Help drawer's static-markup cleanup (introduced in v51m to remove dead
mockup drawers) was deleting ANY element with the `.pmc-drawer-scrim` class
that wasn't the React help drawer — including the licence dialog's scrim on
Company & KYC. With the scrim gone from the DOM, React's unmount on Cancel
threw `NotFoundError: removeChild` and the error boundary showed
"This panel hit an error".

The scrub now only removes a scrim when it shares a parent with a real
static (non-React) drawer, and never touches scrims with inline
`display:block` (all React dialogs set that). Verified: opening and
cancelling the licence dialog repeatedly inside the scrub window no longer
crashes; the Help drawer still opens and closes normally.

## Also included (v51o–v51t)
- Admin Registrations: tap-to-inline review detail on mobile.
- Vendor Change Password: mobile overflow fixed (single column).
- Admin avatar dropdown: React Portal, never clipped; topbar buttons go
  icon-only on mobile.
- Company name change: incorporation evidence upload now REQUIRED + help
  text; admins see the evidence link in Masters → Profile changes.
- Mobile/office-phone change: vendor must confirm via click-link emailed
  to their current email before admin can approve (412 otherwise).
- Bidding Ops mobile: tabs wrap, counts match rows, checkbox alignment.
- Admin drawer scrolls to Masters on iOS (100dvh).
- Admin Vendors: toolbar wraps; inline KPI detail on mobile; giant-button
  padding bug fixed.
- Masters: 13 tabs visible as wrapping chips.
- Start-bid: Submit above tab bar; uploaded files readable with View link.
- Mobile tab bar: Home · Tenders · My Bids · Sign · Account.
- Vendor Account: Password / Other devices rows wrap cleanly.

## Deploy
- Frontend: `pmc-frontend-v51u-prod-build.zip` → S3, CloudFront
  invalidate `/*`. Supersedes all v51o–v51t.
- Backend: **MUST deploy** `pmc-backend-v51u.zip` (contains the v51t
  /phone-verify endpoint + evidence fields; unchanged since v51t).
