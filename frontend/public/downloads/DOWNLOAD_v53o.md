# PMC Managers — Release v53o (frontend + backend)

## Fix: Staff Role Resolution & Portal Routing

### What was causing "every new staff created has admin permissions":

1. **`SignInE.jsx` (`/login`) Staff card missing roles**: When signing in under the "Staff" role card on `/login`, the frontend attempted to match candidate roles from a hardcoded list that was missing `escrow_agent`, `certifier`, `legal_counsel`, `accounting`, `auditor`, `support`. It fell through and attempted `admin` or routed `reviewer` directly to `/admin` instead of the Staff Portal (`/staff`).
2. **`StaffLogin.jsx` (`/staff/login`) Defaulted to Admin**: The dropdown defaulted to `role = "admin"`. If staff submitted without selecting their specific role, it attempted an admin login.
3. **Hardcoded "Administrator" in Avatar Menu**: `AdminAvatarMenu.jsx` displayed `<div className="pmc-muted">Administrator</div>` statically for all staff users regardless of their actual role (e.g., Reviewer, Escrow Agent).
4. **Portal Routing**: Staff users holding non-admin roles (Reviewer, Escrow Agent, Site Certifier, Legal, Accounting, etc.) are now routed directly to their designated queue on the **Staff Portal (`/staff`)**. Only explicit `admin` logins route to `/admin`.

### What changed in v53o:
- `SignInE.jsx`: Expanded `allStaffRoles` to cover all enterprise staff roles. Staff sign-in now routes non-admin staff to `/staff` (Staff Dashboard).
- `StaffLogin.jsx`: Default role dropdown changed to `"reviewer"`. Only routes to `/admin` if the authenticated active role is `"admin"`.
- `AdminAvatarMenu.jsx`: Dynamically displays the user's actual role label (e.g. "Reviewer", "Escrow Agent", "Auditor", "Staff") instead of hardcoding "Administrator".

## Deploy

1. **Backend** — `pmc-backend-v53o.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53o-prod-build.zip` → S3 root, CloudFront invalidate `/*`.
