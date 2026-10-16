# PMC Managers — Release v50o

## Vendor Account page
- **Company name** is now an editable field (same admin-approval queue as
  email/address/phone). Fixes the profile header not reflecting the
  current legal name.
- **Address change dialog is structured**: Street / City / State (optional)
  / Country (dropdown from the country master) / ZIP-postal code. Street,
  city, country and ZIP are mandatory; ZIP accepts 3–12 letters/digits.
  Backend stores both the composed address line and the structured
  `address_parts` so the admin panel renders it cleanly.

## Vendor avatar dropdown (top-right)
- Clicking the avatar now opens a menu instead of navigating:
  - **Change profile** → Company & KYC page
  - **Change photo** → upload avatar (≤400 KB, instant preview)
  - **Change password** → /vendor/change-password
  - **Sign out**
- Menu closes on outside-click / Esc.

## Deploy
- Backend: `pmc-backend-v50o.zip` → EB.
- Frontend: `pmc-frontend-v50o-prod-build.zip` → S3 + CF invalidate.
- No new env vars required.

## Testing
- Backend curl: company_name + structured-address requests created,
  admin-approved, profile shows updated values end-to-end.
- Browser: address dialog renders all five fields, Submit enables only
  when mandatory parts are filled, avatar menu lists all four actions.
