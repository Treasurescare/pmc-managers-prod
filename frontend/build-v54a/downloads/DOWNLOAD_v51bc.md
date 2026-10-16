# PMC Managers — Release v51bc (10 Oct 2026)

Covers the five vendor-portal / find-tenders issues plus the vendor-intel
blacklist/whitelist/evidence/appeal workstream.

## Downloads
- Frontend (production build): `/downloads/pmc-frontend-v51bc-prod-build.zip`
- Backend (EB zip, root-level Dockerfile):  `/downloads/pmc-backend-v51bc.zip`

## Backend changes
- `routers/bids.py` — bid submission now rejects when the **commercial**
  envelope PDF is missing (was already rejecting without a technical PDF).
- `routers/vendor_intel.py` + `models/vendor_intel.py` — adds the full
  blacklist evidence + vendor appeal API:
    * `GET  /api/v1/vendor-intel/blacklist/{ref}` — full record incl. evidence/appeals (admin / reviewer / auditor)
    * `POST /api/v1/vendor-intel/blacklist/{ref}/evidence` — attach doc/photo (admin)
    * `PATCH /api/v1/vendor-intel/blacklist/{ref}/evidence/{i}` — edit note (admin)
    * `DELETE /api/v1/vendor-intel/blacklist/{ref}/evidence/{i}` — remove (admin)
    * `GET  /api/v1/vendor-intel/my-blacklist` — the signed-in vendor's own record
    * `POST /api/v1/vendor-intel/my-blacklist/appeal` — vendor files an appeal
    * `POST /api/v1/vendor-intel/my-blacklist/appeal/evidence` — vendor attaches evidence
    * `DELETE /api/v1/vendor-intel/my-blacklist/appeal/evidence/{i}` — vendor removes

## Frontend changes
- `lib/api.js` — new `uploadsApi.openInNewTab(key, {download, filename})`
  that fetches gated files through the authenticated axios client (fixes
  the "Sign in to download tender documents" 401 that appeared when the
  vendor clicked **View** on their uploaded Technical/Commercial PDF
  during bid submission).
- `apps/vendor-portal/BidSubmit.jsx`
    * View button now uses `openInNewTab` (401 fixed).
    * Toast title is now status-aware so `412` surfaces "Submission
      blocked — pre-condition failed · KYC verification required…"
      instead of the generic "Something went wrong".
- `components/EvidenceManager.jsx` — reusable module used by admin and
  vendor sides. Upload document OR capture a photo
  (`<input accept="image/*" capture="environment">`), inline list with
  **View / Download / Print / Delete**.
- `apps/admin-console/VendorIntelPanel.jsx`
    * Whitelist button now says "Whitelist / remove from blacklist" with
      confirmation prompt and emerald styling (brass "unblacklist" was
      easy to miss).
    * Admin modal shows the blacklist reason, admin evidence manager, and
      the vendor's appeals (with their evidence read-only).
- `apps/vendor-portal-e/VendorBlacklistAppeal.jsx` + wired into
  `VendorHomeE.jsx` — large red banner at the top of the vendor portal
  showing the reason, an "Appeal" text box, and the evidence manager.
- `apps/vendor-portal-e/VendorFindTendersE.jsx` — "Start bid" button now
  jumps straight to `/vendor/bid/new/{ref}` (previously pointed at the
  public mockup notice-detail which forced a re-login). Closed tenders
  show a **Closed** badge in place of the Start-bid button.

## Verification (preview)
- `POST /vendor-intel/blacklist` + add evidence → persisted (admin curl).
- `GET  /vendor-intel/blacklist/{ref}` returns reason + evidence[].
- `GET  /vendor-intel/my-blacklist` returns the record for a blacklisted
  vendor and `{blacklisted:false}` otherwise.
- Vendor appeal + evidence upload → persisted and visible to admin.
- Vendor home shows the "Account suspended" banner (screenshot).
- `DELETE /vendor-intel/blacklist/{ref}` → whitelists cleanly, both admin
  and vendor sides reflect it immediately.
- Bid submit rejects a tech-only payload with "A commercial envelope
  document is required to submit a bid".

## Deploy order
1. Backend v51bc to Elastic Beanstalk (new endpoints are required for the
   new UI panels — ship this first).
2. Frontend v51bc to S3 + CloudFront `/*` invalidation.
