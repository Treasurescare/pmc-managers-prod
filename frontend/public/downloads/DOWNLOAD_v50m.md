# PMC Managers — Release v50m

## Vendor Portal rewrite (removes static mockups)
- Shared `VendorPortalChrome` — every sidebar entry is now a real React
  Router `<Link>` (`/vendor`, `/vendor/tenders`, `/vendor/mybids`,
  `/vendor/emd`, `/vendor/signatures`, `/vendor/company`,
  `/vendor/categories`, `/vendor/reviews`, `/vendor/account`).
- `/vendor/tenders` — live `GET /api/v1/notices` with keyword search +
  9-per-page pagination. Heading count matches card count (fixes
  "12 match / 6 shown").
- `/vendor/signatures` — real `GET /api/v1/docusign/mine` with
  Review & sign (resume embedded view) and Download signed PDF.
- `/vendor/account` — new Profile Edit UI. Each field (address,
  office_phone, mobile, email) opens a Request-change dialog; Submit is
  disabled until the vendor types a new, different value.

## Vendor Profile Edit flow (Admin approval + email verification)
- Backend `routers/vendor_profile_changes.py`:
  * `GET  /api/v1/vendor/profile`
  * `GET  /api/v1/vendor/profile/requests`
  * `POST /api/v1/vendor/profile/request-change`
  * `GET  /api/v1/vendor/profile/email-verify/{token}`
  * `GET/POST /api/v1/vendors/profile-change-requests[/{id}/approve|reject]`
- **Email changes require BOTH** a verification click on the new address
  (link sent via Resend) AND an admin approval. Approve returns 412 until
  the vendor has verified. Address / phone / mobile only need admin approval.
- Admin Masters → **Profile changes** tab (`masters-tab-profile_requests`)
  lists pending/approved/rejected rows with approve/reject.
- New page `/vendor/verify-email-change/:token` for the email confirmation.

## Security fixes
- **SEC-001** — `config.py::_seed_password` honours env for ADMIN_PASSWORD,
  OWNER_PASSWORD and every STAFF_PW_*. Non-prod logs a `[PMC-SEC-001]`
  warning; `ENV=production` with missing seed → pod refuses to boot.
- **SEC-003** — `docusign.py::_verify_hmac` now fail-closes in production
  when `DOCUSIGN_CONNECT_HMAC_SECRET` is missing; non-prod still accepts
  with a `[PMC-SEC-003]` warning so sandbox webhooks keep working.

## Batch D bug fixes
- **#13 Escrow Create joint account** — client-side validation added for
  Display name, Institution, Account no., PMC officer name+email, Escrow
  officer name+email; also rejects if the two officer emails match.
  Toast now names the specific missing fields instead of a silent no-op.
- **#37 L1 Comparison dropdown** — switched from `publicApi.listNotices`
  (published only, limit 200) to `adminApi.listAllNotices({limit:500})`
  so drafts also show up and the panel no longer "hides" tenders.
- **#39-41 Reverse Auctions tab missing** — new Admin Option-E page
  `AdminAuctionsE.jsx` under Money & compliance → **Reverse auctions**
  (`/admin/e/auctions`). Lists every auction, has a New-auction form
  (notice picker + prices + duration), and wires inline Start / Close
  buttons that call `/api/v1/reverse-auctions/{aid}/start|close`.
- **#45 Stakeholder Reports** — new Admin Option-E page
  `AdminStakeholderReportsE.jsx` under Events → **Stakeholder reports**
  (`/admin/e/stakeholder-reports`). Four tabs (Tender pipeline / Awards /
  Escrow & EMD / SLA & Contracts), KPI cards, data table and one-click
  CSV export per tab. Fixes the earlier "JSON parse error" (tab didn't
  exist; backend endpoints always returned JSON — the frontend just
  wasn't calling them).
- **#118 AI Bid Anomaly dropdown contrast** — select now explicitly uses
  `text-brand-navy` + `bg-white` so the option text is readable instead
  of pale/faint.

## Deploy
- Backend: `pmc-backend-v50m.zip` → AWS Elastic Beanstalk.
- Frontend: `pmc-frontend-v50m-prod-build.zip` → S3 + CloudFront invalidate.
- SW banner from v50j auto-prompts Refresh after rollout.
- No new env vars required. Optional (recommended for production):
  `ENV=production`, `DOCUSIGN_CONNECT_HMAC_SECRET`,
  `ADMIN_PASSWORD`, `OWNER_PASSWORD`,
  `STAFF_PW_{ESCROW,CERTIFIER,LEGAL,ACCOUNTS,COMMITTEE}`.

## Testing
- Backend pytest `test_v50m_profile_changes.py` — 13/13 pass.
- Backend curl end-to-end — vendor requests email change → verifies token
  → admin approves (blocked until verify with HTTP 412) → vendor logs in
  with new email.
- Live DOM audit — every vendor sidebar entry renders with real routes.
- Reverse auctions list + Stakeholder reports endpoints verified live
  (6 auctions, 24 tenders, 1 escrow account, 2 txs on the preview env).
