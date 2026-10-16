# PMC Managers — Release v51bd (10 Oct 2026)

Adds the three follow-on features requested after v51bc.

## Downloads
- Frontend: `/downloads/pmc-frontend-v51bd-prod-build.zip`
- Backend : `/downloads/pmc-backend-v51bd.zip` (correct EB root layout)

## Backend changes
- `routers/bid_drafts.py` (new) — server-side bid drafts so vendors can
  switch devices mid-bid.
    * `GET  /api/v1/bids/drafts/{notice_ref}` — fetch a draft or `{found:false}`
    * `PUT  /api/v1/bids/drafts/{notice_ref}` — overwrite / upsert a draft
    * `DELETE /api/v1/bids/drafts/{notice_ref}` — explicit remove
    * `GET  /api/v1/bids/drafts` — list the vendor's open drafts
    * Draft rows are auto-deleted the instant `POST /api/v1/bids` succeeds.
- `routers/vendor_intel.py`
    * `GET /api/v1/vendor-intel/blacklist-dashboard` — one row per
      blacklist with evidence_count, appeal_count, pending_appeal_count,
      latest_appeal_at + status, so compliance can triage in one glance.
    * Appeal notifications: `POST /my-blacklist/appeal` fires
      `notify_role("admin", …)` + a confirmation email to the vendor.
      `DELETE /blacklist/{ref}` (whitelist) emails the vendor
      "Your account has been whitelisted" and notifies the admin role.
- `server.py` — registered the new `bid_drafts` router.

## Frontend changes
- `lib/api.js`
    * `bidApi.getDraft / saveDraft / deleteDraft / listDrafts`
    * `vendorIntelApi.blacklistDashboard`
- `apps/vendor-portal/BidSubmit.jsx`
    * Load prefers server draft, falls back to localStorage.
    * "Save draft" now pushes to the backend (and still mirrors locally).
    * Successful submit deletes both the local and server drafts.
- `apps/admin-console/BlacklistDashboardPanel.jsx` (new) — compliance
  triage table with KPI tiles, free-text search, filter chips
  (All / Pending appeals / With admin evidence / No evidence yet) and a
  **Manage** button that opens the full vendor modal in place.
- `apps/admin-console/VendorIntelPanel.jsx` — the triage panel is
  rendered above the legacy summary table.

## Verification (preview)
- Dashboard empty, then one row after blacklist + evidence + appeal
  (evidence_count=1, pending_appeal_count=1).
- Appeal submission returns ok and triggers the admin+vendor emails.
- Draft PUT → `{ok:true, updated_at:…}`, GET returns the stored payload,
  DELETE clears it, and a real `POST /api/v1/bids` auto-wipes any draft.
- Whitelist returns ok and surfaces the "whitelisted" decision email
  (via `vendor_confirm` + `notify_role("admin", …)`).

## Deploy order
1. **Backend v51bd** to Elastic Beanstalk (the new endpoints must exist
   before the frontend calls them).
2. **Frontend v51bd** to S3 + CloudFront `/*` invalidation.
