# PMC Managers — Release v53m (frontend + backend)

## Fixes shipped since v53l

### 1. Duplicate escrow institutions by email — cleanup + prevention
You reported *"in the masters by mistake there are three institutions by
the same email address. that itself is wrong."* Confirmed on preview DB
— three groups of 3 duplicate institutions each.

New endpoints:
- `GET /api/v1/escrow-institutions/duplicates` (admin). Aggregates
  institutions by lowercased `primary_contact_email` and returns every
  group with count > 1. Each row carries status, created_at, whether it
  has an owning account, and whether it has signatories, so you can tell
  the "real" one from the strays at a glance.
- `DELETE /api/v1/escrow-institutions/{iid}` (admin). Hard-deletes a
  single stray row. **Safe-only**: refuses with 409 if the row has an
  owning `escrow_accounts` record, or if any of its signatories' emails
  are already a signer on a joint escrow account. You can't orphan a
  live account by accident.

Admin UI:
- New red **Find duplicates** button in the Escrow institutions header.
  Opens a cleanup panel listing every email group with per-row Delete
  buttons, status chips, and `has-account` / `has-signatories` badges so
  you keep the right row.

### 2. Login error that actually tells you what's wrong
Escrow login (`POST /api/v1/escrow-accounts/auth/login`) used to return
a generic 401 "Invalid email or password" regardless of root cause.
Now:
- **404 `no_account`** — no account exists for that email at all.
- **404 `no_account_only_institution`** — admin invited the email but
  the invitee never finished registration + password-setting.
  Message: *"This email was invited by an admin but you haven't finished
  registration yet. Open the invite link in your mailbox, or ask the
  admin to resend it."*
- **401** — account exists but the password is wrong.
- **403 `unverified`** — unchanged (pre-existing).

Unified sign-in page (`/login` → Existing Institution role) now
surfaces that message verbatim instead of swallowing it.

This explains why `accounts@pmcmanagers.com` and
`escrowdemo@pmcmanagers.com` were bouncing on your deployed site: no
matching `escrow_accounts` row for the email you were typing. Either
you never completed the "set your password" step after admin-invite, or
the row was created under a different email. The new message will
pinpoint which.

### 3. v53l backfill endpoint stays shipped
If you still see the dropdowns in your Escrow accounts panel but
Backfill does nothing on production, that's because **production is
behind v53l** — the endpoint it calls doesn't exist on the old backend.
Deploying this v53m bundle (which includes v53i → v53m) fixes it.

## Deploy

1. **Backend** — `pmc-backend-v53m.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53m-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. Admin → Escrow institutions → click **Find duplicates** → delete the
   stragglers for each duplicate group. Keep the row with
   `has-account` + highest status (approved > submitted > draft).
4. Try the escrow login again. If it still fails you'll now see a clear
   reason — share the exact toast text and I'll finish from there.

## Files touched

Backend
- `routers/escrow_institutions.py` — `GET /duplicates`, `DELETE /{iid}`.
- `routers/escrow_accounts.py` — login error surfaces `no_account` /
  `no_account_only_institution` with structured detail.

Frontend
- `lib/api.js` — `escrowInstitutionsApi.duplicates()`, `.delete()`.
- `apps/admin-console-e/AdminEscrowInstitutionsE.jsx` — Find duplicates
  button + cleanup panel.
- `apps/auth-e/SignInE.jsx` — show backend's structured 404 detail
  verbatim instead of generic fallback.
