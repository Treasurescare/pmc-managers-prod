# PMC Managers — Release v51v (cumulative, supersedes v51o–v51u)

## Hotfix in this build

### Vendor "Submit a bid" / payment / sandbox / verify pages — dark-on-dark heading
The global theme remap `[data-ui="e"] .bg-slate-50 → deep green` (meant for
dark pages) also repainted the LIGHT bid-submit shell, so after v51r's text
restore the page heading rendered dark-on-dark and was invisible. These four
light pages (bid submit, payment result, sandbox checkout, vendor verify)
are now explicitly pinned back to light slate-50 with dark ink.

## Also included (v51o–v51u)
- Company & KYC Cancel crash fix (scrim scrub guard)
- Admin Registrations inline detail on mobile
- Vendor Change Password mobile overflow fix
- Admin avatar dropdown via React Portal + icon-only topbar buttons on mobile
- Company-name change: incorporation evidence upload required + help text
- Phone-change confirmation gate (click-link to current email, admin 412)
- Bidding Ops mobile: tabs wrap, counts match rows, checkbox alignment
- Admin drawer iOS scroll fix, Vendors toolbar wrap, inline KPI detail,
  Masters chip grid, Start-bid bottom clearance + readable upload chips,
  5-icon mobile tab bar, Account rows wrap

## Deploy
- Frontend: `pmc-frontend-v51v-prod-build.zip` → S3, CloudFront invalidate `/*`.
- Backend: unchanged since v51t (`pmc-backend-v51v.zip` identical; if you
  already deployed v51t/v51u backend you can skip it).
