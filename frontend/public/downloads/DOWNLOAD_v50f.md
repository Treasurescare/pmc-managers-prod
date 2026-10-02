# PMC Managers Limited — Release v50f

## What's new
### Forgot-password portal selector — Administrator vs PMC staff split
User feedback: "the reset password button does not differentiate
staff and Admin user roles."

Backend reality: PMC admins and staff share the same `admin_users`
collection; the reset flow uses one `portal="staff"` branch for both.
UI previously collapsed this into a single "PMC staff / Admin" row,
which hid who could reset from where.

Fix (`frontend/src/apps/auth-e/ForgotPasswordE.jsx`):
Three clearly-labelled portal rows on `/forgot-password`:
1. **Supplier** — Vendor portal
2. **Administrator** — Admin console (Owner, Master Admin, Support)
3. **PMC staff** — Tender desk, evaluation, escrow, committee

Both admin rows map to `portal="staff"` under the hood so Owner,
Master Admin and all specialist roles can reset with equal effect.

Service-worker cache bumped to `pmc-shell-v50f-rev1`.

## Email delivery note — DNS lives in Route 53, NOT GoDaddy
Your GoDaddy DNS tab confirmed "DNS Provider: Amazon Route 53" — the
MX/TXT records for `mail.pmcmanagers.com` must be added inside AWS
Route 53, not GoDaddy. Public DNS still shows no MX/TXT for
`mail.pmcmanagers.com`; the two records from your Resend dashboard
(MX host `mail` priority 10 to feedback-smtp.*.amazonaws.com + TXT
host `mail` SPF `v=spf1 include:amazonses.com ~all`) will unlock
delivery.

Website + API performance is unaffected — those use separate A
records; mail subdomain changes are isolated.

## Bundles
* **Frontend: `pmc-frontend-v50f-prod-build.zip`** — deploy this.
* **Backend: `pmc-backend-v49y.zip`** — unchanged.

## Deploy
S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.
