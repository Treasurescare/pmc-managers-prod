# PMC Managers — Release v54q (17 Jun 2026)

> **v54q supersedes v54p. Do not deploy v54p** — it had a privilege-escalation
> bug (the "PMC staff" card could log an admin-holding account in as admin).
> v54q reverts that and adds the account-type flag.

## What's new — account type at staff creation
Every staff member is now explicitly **Admin** or **Staff**:

- **Admin account** → signs in via the Administrator login → admin console.
  Must hold the Admin or Reviewer role.
- **Staff account** → signs in via the staff login → only the `/staff`
  specialist dashboard. **Cannot** hold the Admin or Reviewer role.

This is enforced on the server (create + edit) and in the Staff Master UI:
choosing "Staff" hides the Admin/Reviewer role checkboxes, so a specialist /
escrow signer can never be granted admin-console access. Existing accounts are
auto-classified (holds admin/reviewer ⇒ Admin, otherwise ⇒ Staff).

Also included: the "PMC staff" sign-in card never logs anyone in as admin, a
clear "enable 2FA" message for high-risk roles, and the v54o RBAC guard that
blocks specialists from the admin console.

## Artifacts
- Backend (Elastic Beanstalk): `pmc-backend-v54q.zip`
- Frontend (S3 + CloudFront): `pmc-frontend-v54q-prod-build.zip`

## Deploy steps
1. Upload `pmc-backend-v54q.zip` to EB; wait for green/healthy.
2. Sync the **contents** of `pmc-frontend-v54q-prod-build.zip` to S3 (NO `--delete`).
3. CloudFront invalidation for `/*`.
4. Confirm `GET https://www.pmcmanagers.com/api/v1/_version` returns **v54q**
   and the footer shows Frontend v54q / Backend v54q.

## Verify after deploy
- Masters → Staff → New Staff: an **Account type** (Staff/Admin) selector appears;
  "Staff" hides Admin/Reviewer roles.
- Edit the `accounts@` account, set type = **Staff** → Admin/Reviewer are removed;
  that account now lands on `/staff` and cannot open `/admin`.
- An Admin-type account signs in via the Administrator login and reaches the console.
