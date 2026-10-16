# PMC Managers — Release v50r (cumulative: v50m → v50r)

## Fixes in this build (post-prod feedback)

### (a) Vendor Home redirection — fixed on ALL vendor pages
The remaining static Option-E pages (My bids / EMD / Reviews / Alerts) had
`href="#"` sidebar links that the global PmcLinkPatcher sometimes misrouted
to the public landing page. Every sidebar entry on those pages now carries
a real `/vendor/...` href. Clicking Home from anywhere in the supplier
portal lands on the vendor home — not pmcmanagers.com.

### (b) Admin Vendor requests crash fixed
`routers/vendor_categories` is now registered BEFORE `routers/vendors`
(same guard as `vendor_profile_changes`); the `/{vendor_ref}` catch-all
no longer gobbles `/api/v1/vendors/category-requests` and the
"This panel hit an error" ErrorBoundary never fires. Panel also hardened
to accept array-or-object payloads defensively.

### (c) Sidebar reorg — Vendor requests + Profile changes moved to Market
Both admin review queues are now top-level sidebar items under Market
(positions 5 & 6), each with its own route and page:
- `/admin/e/vendor-requests` — AdminVendorRequestsE
- `/admin/e/profile-changes` — AdminProfileChangesE
Masters still shows the panels under "(moved → Market)" labels for one
release so bookmarks keep working.

### (d) Help page "Back" is now a real back button
Both `/help` and `/help/:slug` headers used to show "Back to tender
board" with a hard link to `/admin/e/dashboard`. Now a `← Back` button
calls `window.history.back()` (falls back to the Help Centre root if
history is empty). Vendors return to the vendor page, admins return to
the admin page.

## Carried from v50m–v50q
- Vendor Portal rewritten (Home/Tenders/Signatures/Account/KYC on live
  APIs, structured address, phone validation, avatar dropdown)
- Vendor profile change approval queue (email verify + admin approve)
- SEC-001 fail-fast seeds, SEC-003 DocuSign HMAC fail-closed
- #6 Vendor activation verified end-to-end, #60 blank form regenerated
- DocuSign admin Archive-PDF repair tool
- EMD Master Editor UI (Masters → EMD rules + calculator)
- Reverse auctions page, Stakeholder reports page
- Admin Masters: Category Master, L1 all-notices, escrow validation,
  anomaly contrast

## Deploy
- Backend: `pmc-backend-v50r.zip` → EB
- Frontend: `pmc-frontend-v50r-prod-build.zip` → S3 + CF invalidate `/*`
- No new env vars required
