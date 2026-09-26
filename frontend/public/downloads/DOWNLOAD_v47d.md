# v47d — Security sign-in alert emails on every login (all portals)

## What's new

Every successful login now triggers a branded security email to the account holder, across **all** portals:

| Portal / endpoint | Alert label |
|---|---|
| Admin Console (`/api/v1/admin/auth/login`) | "Admin Console" |
| Staff — escrow / certifier / legal / accounting / committee / management / partners / agents (`/api/v1/staff/auth/login`) | "Staff Portal · {active_role}" |
| Vendor Portal (`/api/v1/vendor/auth/login`) | "Vendor Portal" |

The email includes:
- Portal name and UTC timestamp
- Client IP address and device (user-agent)
- "If this wasn't you, change your password immediately and contact PMC support" call-to-action

### Behaviour notes
- The alert fires **after** full authentication — for MFA-enabled staff, only after the OTP passes. Failed logins send nothing.
- Fire-and-forget: an email outage can never block or delay sign-in.
- No new config needed — reuses the verified `admin@mail.pmcmanagers.com` Resend sender.

## Verified on preview
- Admin login → HTTP 200 + Resend 200 (alert sent) ✅
- Staff login (management role) → HTTP 200 + Resend 200 ✅
- Vendor login → HTTP 200 + Resend 200 ✅

## Deploy
Backend-only: upload `pmc-backend-v47d.zip` to EB. Contains v47c (vendor confirmatory emails), v47b (Send EMD link + stage emails), v47a (Approve/Hold/Resume), v46z (EMD fallback + View/Print) and v46y (Rate-a-Peer) — one deploy covers everything.

No frontend change; the v47b frontend build stays current.
