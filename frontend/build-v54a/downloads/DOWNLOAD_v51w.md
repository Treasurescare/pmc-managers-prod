# PMC Managers — Release v51w (cumulative, supersedes v51o–v51v)

## New in this build

### Notice creator attribution
Every notice now records and displays the creator's email:
- New notices store `created_by_email` (from the signed-in admin/staff JWT).
- Admin → Notices list shows "Created by <email>" under each notice title.
- Public notice detail page shows "Posted by <email>" in the hero line.
- Existing notices: run the included one-off backfill after deploying the
  backend (matches created_by admin id → admin_users email):
  `python3 backfill_notice_creator.py`  (idempotent; safe to re-run)
  Preview backfill already ran: 10 notices stamped, 14 skipped (old seed
  rows whose creator id no longer exists — those simply show nothing).

## Also included (v51o–v51v)
- Light-shell vendor pages pinned light (bid submit / payment / sandbox /
  verify headings readable again)
- Company & KYC Cancel crash fix
- Admin Registrations inline detail on mobile
- Vendor Change Password mobile overflow fix
- Admin avatar dropdown via React Portal + icon-only topbar on mobile
- Company-name change: evidence upload required + help text
- Phone-change confirmation gate (click-link to current email, admin 412)
- Bidding Ops mobile tabs/counts/checkbox; admin drawer iOS scroll fix;
  Vendors toolbar + inline KPI; Masters chip grid; Start-bid clearance +
  readable upload chips; 5-icon mobile tab bar; Account rows wrap

## Deploy
- Frontend: `pmc-frontend-v51w-prod-build.zip` → S3, CloudFront invalidate `/*`
- Backend: **deploy** `pmc-backend-v51w.zip` to Elastic Beanstalk, then run
  the backfill script once inside the backend environment.
