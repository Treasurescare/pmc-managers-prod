# PMC Managers · Release v52bt

**Date:** 11 Oct 2026
**Supersedes:** v52bs

## Bugs fixed in this release

### Admin sidebar inconsistency (highest impact)
- Market section only showed 4 items on some pages (Dashboard, Tender builder, Bidding ops, Registrations, Evaluation list, Programme) because those pages had a stale hard-coded sidebar HTML with the old item list.
- Fix: introduced a shared `AdminSideNavE` component (single source of truth) with the full 27-item list including Vendor requests, Profile changes, Escrow institutions, Reverse auctions, and Masters. Every admin page now renders the identical sidebar.

### EMD & Payment (Vendor /vendor/emd)
- "All statuses" and "All currencies" dropdowns were dead JSX selects with a single option each — now populated from the rendered deposit rows with real distinct values (data-testid `vemd-status-filter`, `vemd-currency-filter`), with live row filtering.
- Pay EMD button now resolves the correct bid via `data-bid-ref`/`data-bid-id` stamped on hydrated rows and genuinely opens a Stripe sandbox checkout session.

### Admin Escrow / EMD "Edit signers" opacity
- Replaced the washed-out outline style with a solid high-contrast `bg-brand-navy text-white` primary button; computed opacity now 1.

### DocuSign
- Resend on older envelopes created against a different sandbox key no longer surfaces a raw stack trace. If upstream returns `ENVELOPE_DOES_NOT_EXIST`, the endpoint now returns HTTP 410 with a friendly detail ("different DocuSign sandbox — use Reassign") and marks the local envelope row `status: "orphaned"`.
- Vendor-side bid/award status now updates the moment admin acts: `_apply_live_status` mirrors every DocuSign transition (sent/delivered/signed/completed) onto `db.bids` (`docusign_status`, `<sub_kind>_docusign_status`, `docusign_updated_at`) and `db.awards`. Previously only `completed` fired the mirror, so vendors saw their bid stuck on "submitted / pending".

### Work packages sample CSV
- Verified: the admin page's "Sample CSV" button downloads via authenticated blob fetch; file first line = `title,category,phase,value,currency,float_target_date,status`.

## Deployment

### Backend (Elastic Beanstalk, Docker)
Upload `pmc-backend-v52bt.zip` as a new EB application version. The archive has `Dockerfile`, `Dockerrun.aws.json`, and `.platform/` at the archive root.

### Frontend (S3 + CloudFront)
Unzip `pmc-frontend-v52bt-prod-build.zip` and sync to your S3 bucket, then invalidate CloudFront `/*`.

### Verification after deploy
1. Sign in as admin → navigate between any 3 admin pages → confirm the sidebar shows Masters, Reverse auctions, Vendor requests, Escrow institutions on every page.
2. Admin → Escrow / EMD → an account row shows a solid dark "Edit signers" button.
3. Vendor → EMD & payments → the two filter dropdowns are populated with multiple options; selecting one filters the table.
4. Admin → Work packages → "Sample CSV" button downloads the sample.
5. Admin → DocuSign → clicking Resend on a historical envelope now shows a friendly "different sandbox / use Reassign" message, not a stack trace.

## Testing summary
Backend pytest: 6/6 pass. Frontend end-to-end: 7/7 feature checks pass (`/app/test_reports/iteration_50.json`).
