# PMC Managers — Release v54o (17 Jun 2026)

## What's in this release
**Staff RBAC fix — specialist staff can no longer reach the admin console.**

- A staff member created in Staff Master with only a specialist role (e.g.
  Escrow Agent / "escrow signer") previously saw the FULL admin console after
  logging in. Root cause: the `/admin` and `/admin/e/*` routes had no frontend
  role guard.
- Now: only `admin` and `reviewer` can enter the admin console. Every other
  role is redirected to the `/staff` specialist dashboard.
- Backend hardened: the remaining any-staff endpoints (billing, docusign,
  engagements, auctions, evaluations, meetings, governance, help-requests,
  tenant-logo) now require the correct role — a specialist token gets 403.

### Enforced role → access map
- `admin` → full admin console
- `reviewer` → admin console (deputy)
- `escrow_agent`, `certifier`, `legal_counsel`, `accounting`,
  `committee_member`, `auditor`, `support`, `management`, `partner`, `agent`
  → `/staff` specialist dashboard only (their own queue)

Note: `escrow_agent`, `legal_counsel`, `accounting` require 2FA to log in.

## Artifacts
- Backend (Elastic Beanstalk): `pmc-backend-v54o.zip`
- Frontend (S3 + CloudFront): `pmc-frontend-v54o-prod-build.zip`

## Deploy steps
1. Upload `pmc-backend-v54o.zip` to Elastic Beanstalk; wait for green/healthy.
2. Sync the **contents** of `pmc-frontend-v54o-prod-build.zip` to your S3 bucket
   (do NOT use `--delete`).
3. Run a CloudFront invalidation for `/*`.
4. Confirm: `GET https://www.pmcmanagers.com/api/v1/_version` returns **v54o**
   and the footer shows Frontend v54o / Backend v54o.

## Verify after deploy
- Log in a specialist staff (e.g. a Site Certifier) → they land on `/staff`.
- Navigate them to `/admin` → they are bounced back to `/staff`.
- Log in as admin → full console loads normally.
