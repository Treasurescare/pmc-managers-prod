# PMC Managers — Release v52bf (10 Oct 2026)

Consolidated build covering every change since the last live deploy
(v51ba): bid-detail readability, Section D clean-up, bid-submit fixes,
blacklist evidence & vendor appeal, admin triage dashboard, appeal
decision workflow, CSRF resilience, Vendor Intel readability.

## Downloads
- Frontend: `/downloads/pmc-frontend-v52bf-prod-build.zip` (3.0 MB)
- Backend : `/downloads/pmc-backend-v52bf.zip` (532 KB, EB root layout)

## Rolled-up contents

### Readability
- Admin bid detail (v51ba) — scoped `[data-testid="admin-bid-page"]`
  carve-out ends the cream-on-cream text.
- Admin vendor create/edit (v51bb) — brighter page, visible input
  borders, emerald draft banner.
- Vendor Intel triage + modal (v51bf) — scoped
  `[data-testid="admin-vendor-intel-panel"]` and
  `[data-testid="blacklist-dashboard-panel"]` carve-outs; KPI tiles,
  Manage buttons, evidence rows and the Whitelist CTA all readable.

### Admin bid detail (v51ba)
- Award Record panel (tender dates, winning vendor, PMC/Legal/Escrow/
  Certifier/Accounts/Committee sign-offs, escrow ledger, DocuSign
  envelopes). Print Award Letter / Contract HTML + PDF endpoints:
    * `GET /api/v1/awards/bid/{id}/summary`
    * `GET /api/v1/awards/bid/{id}/award-letter.html`
    * `GET /api/v1/awards/bid/{id}/award-letter.pdf`
    * `GET /api/v1/awards/bid/{id}/contract.html`
    * `GET /api/v1/awards/bid/{id}/contract.pdf`

### Vendor portal + bid submission (v51bc / v51bd)
- Find tenders: Start bid now routes directly to `/vendor/bid/new/{ref}`
  (no more login loop via the public mockup); closed tenders show a
  Closed badge.
- `POST /api/v1/bids` requires BOTH Technical and Commercial envelope
  PDFs. Error toasts are status-aware (412 "KYC verification required…",
  409 duplicate bid, 422 missing info, 400 deadline / rule).
- Uploaded doc "View" button now streams through authenticated axios
  (`uploadsApi.openInNewTab`) — the 401 "Sign in to download tender
  documents" is gone.
- Save-draft persists BOTH to localStorage and to the backend via
  `GET/PUT/DELETE /api/v1/bids/drafts/{notice_ref}` + `GET
  /api/v1/bids/drafts`. A successful bid auto-deletes the draft.
- $0 EMD submissions no longer stall on Step 5 — workspace marks it
  done once both envelopes are sealed and the status is `submitted`.
- Vendor sidebar: Categories icon now renders; new Services nav entry.

### Blacklist / whitelist / appeals (v51bc / v51bd / v51be)
- `routers/vendor_intel.py`
    * `GET /vendor-intel/blacklist-dashboard` — triage rows with
      evidence/appeal counts.
    * `GET /vendor-intel/blacklist/{ref}` — full admin record.
    * `POST/PATCH/DELETE /vendor-intel/blacklist/{ref}/evidence[/{idx}]`
    * `DELETE /vendor-intel/blacklist/{ref}` — whitelist + vendor email.
    * `POST /vendor-intel/blacklist/{ref}/appeals/{idx}/decision` —
      admin approves/rejects with a note; optional auto-whitelist on
      approval; vendor + admin notified.
    * `GET /vendor-intel/my-blacklist`
    * `POST /vendor-intel/my-blacklist/appeal`
    * `POST/DELETE /vendor-intel/my-blacklist/appeal/evidence[/{idx}]`
- `EvidenceManager.jsx` — upload document OR capture photo
  (`<input accept="image/*" capture="environment">`), inline list with
  View / Download / Print / Delete.
- Admin VendorIntel modal: emerald Whitelist CTA with confirmation,
  admin evidence manager, vendor appeals with inline Approve / Reject
  decision form (note + "also whitelist on approval" toggle).
- Vendor portal home: red "Account suspended" banner with reason, appeal
  message, and evidence manager (file or camera).
- Admin dashboard: new BlacklistDashboardPanel (KPI tiles, search,
  filter chips, Manage) rendered above the legacy summary table.

### CSRF resilience (v51be)
- Front-end caches the `csrf_token` returned in the login JSON into
  sessionStorage and uses it as a fallback when the JS-readable
  `csrf_token` cookie is dropped by strict-tracking / partitioned-cookie
  browsers. Clears on logout. Fixes "HTTP 403 CSRF token missing or
  invalid" when clicking Blacklist.

## Deploy order
1. **Backend v52bf first** to Elastic Beanstalk — all the new vendor-intel
   endpoints, bid draft endpoints, awards print endpoints, and the
   commercial-doc requirement are only in this image.
2. **Frontend v52bf** to S3 after EB is healthy, then CloudFront `/*`
   invalidation.

## Verification (preview, before packaging)
- Award record panel + print views open; PDF downloads valid.
- Bid submit rejects without commercial PDF (422), after deadline (400).
- View-file 401 gone — uploaded PDF opens in a new tab.
- Draft PUT/GET/DELETE round-trip, auto-wipe on successful submit.
- Blacklist: evidence attach/view/delete, vendor appeal + evidence,
  admin approve/reject with note, auto-whitelist on approval, vendor
  home banner, triage dashboard counts.
- Vendor Intel readability: all buttons + rows clearly visible.
