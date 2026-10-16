# PMC Managers — Release v53p (frontend + backend)

## What's new since v53o

### 1. In-app Staff Role Switching
**New endpoint:** `POST /api/v1/staff/auth/switch-role` (CSRF-gated, requires an existing staff session).

Request body: `{ "active_role": "<role>" }`. Validates the signed-in staff member actually holds that role on `admin_users.roles`; re-issues the JWT with the new `active_role` and refreshes both the `access_token` httpOnly cookie and the `csrf_token` cookie / returned token. Audit event: `staff.switch_role` with `{from, to}`.

Guards:
- 403 if the user does not hold the requested role.
- 403 if the role is in `HIGH_RISK_ROLES` (`escrow_agent`, `legal_counsel`, `accounting`) and the user does not have MFA enabled.

**UI:** The Staff Portal header now shows an **Active role** dropdown next to the user email, listing every role the user actually holds. Switching from the dropdown:
- fires the switch-role endpoint,
- refreshes `staffApi.me()`,
- repaints the queue for the new role,
- or redirects to `/admin` if the new role is `admin`.

The selector is hidden when the user only holds a single role, so single-role staff see no clutter.

Verified live on preview with `adminsupport@pmcmanagers.com` holding 8 roles — switch to `reviewer` returned 200 with fresh CSRF; switch back to `admin` returned 200 with new CSRF.

### 2. Permission Preview drawer in Masters → Staff
A new **"Preview what this staff can do →"** button sits below the Roles multi-select in the New Staff form. Clicking it opens an inline drawer that:
- Lists every ticked role with its **landing route after sign-in** so admins can see at a glance whether the user will land on `/admin` (full console) or `/staff` (specialist queue) — e.g. *"Reviewer: /admin — review notices, bids, vendor registrations"* vs *"Escrow Agent: /staff — EMD-paid bids awaiting escrow acceptance"*.
- Pulls the current permission matrix (`GET /api/v1/permissions`) and renders rows for each ticked role as a table: Role · Doc type · view / create / modify / delete / publish, with ✓ or `·` per cell.
- Explicitly notes that the matrix doesn't include `admin` because `admin` always holds implicit full access.

This solves the "every new staff seems to have admin permissions" visibility gap you flagged — now the admin can confirm the exact post-save permissions BEFORE clicking **Create staff**.

Button is disabled while no roles are ticked, so you can't preview an empty role set.

## Deploy

1. **Backend** — `pmc-backend-v53p.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53p-prod-build.zip` → S3 root + CloudFront invalidate `/*`.

## Files touched

Backend
- `routers/staff_auth.py` — new `SwitchRoleIn` model + `POST /auth/switch-role` endpoint; also imports `pydantic.BaseModel` and `StaffRole`.

Frontend
- `lib/api.js` — new `staffApi.switchRole(active_role)`.
- `apps/staff-portal/StaffDashboard.jsx` — Active-role dropdown in header, extended `ROLE_LABELS`, in-place `switchRole()` handler.
- `apps/admin-console/masters/StaffTab.jsx` — permission preview drawer with per-role landing-route list + live permission matrix rows.
