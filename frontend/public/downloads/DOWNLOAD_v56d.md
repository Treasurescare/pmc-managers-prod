# PMC Managers — Release v56d (18 Jun 2026)

## Fix
- **Safari: "Open in DocuSign to sign" now works from the escrow institution
  dashboard.** The button opened the signing URL with `window.open()` AFTER an
  async fetch, which Safari blocks (popup outside the click gesture) — so
  clicking did nothing. Now a tab opens synchronously on click and navigates to
  the DocuSign recipient-view URL once it loads (falls back to same-tab if the
  popup is blocked). Sakina can now sign from Pending signatures, not only via
  the email link.

## Artifacts
- Backend: `pmc-backend-v56d.zip`
- Frontend: `pmc-frontend-v56d-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. CloudFront invalidation `/*`. 4. Footer should read Frontend v56d · Backend v56d.

## Coming next (confirmed, separate build)
- PMC officer signing view inside the Staff portal: the assigned escrow
  transaction listed alongside the acceptance queue, with an inline
  "Open in DocuSign" / Sign action + a left sidebar (Overview / Pending
  signatures / Transactions).
