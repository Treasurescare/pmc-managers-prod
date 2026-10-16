# PMC Managers — Release v53n (frontend + backend)

## Blocker fix: "set-password-then-crash-to-login" loop

Your report (verbatim): *"admin approves institution. sends magic link.
magic link reaches email. we click on the set password. once the
password is set and confirmed again and save and login. it crashes and
moves to login page. but then the same credentials are not working while
entering through escrow institution."*

### Root cause

Two different kinds of people can sign into the Escrow portal:

| Who | Auth model | Cookie | /auth/me |
|---|---|---|---|
| Institution account (register-first) | `escrow_accounts` row | `escrow_account_token` | `/api/v1/escrow-accounts/auth/me` |
| Named signatory (claims via approval magic link) | `escrow_signatories` row | `escrow_sig_token` | `/api/v1/escrow-signatories/auth/me` |

When admin **approves** an institution, the email contains
`/escrow/login?claim=1&iid=<id>&token=<magic>`. Setting a password
there calls `POST /escrow-signatories/claim`, which creates the
signatory row **and auto-signs them in** by dropping the
`escrow_sig_token` cookie. The frontend then navigates to `/escrow/me`.

`EscrowMePage` **only** called `/escrow-accounts/auth/me`. The signatory
cookie doesn't match that endpoint, so it 401'd and the error handler
redirected back to `/escrow/login`. Login would succeed (signatory
endpoint accepts the password), then nav back to `/escrow/me`, then
bounce back to `/escrow/login` — the "crash loop" you were seeing. And
because the first redirect happened BEFORE anything rendered, the user
assumed the password save had failed.

### Fix

`EscrowMePage.jsx` now tries **both** `/auth/me` endpoints in
sequence:

1. `GET /api/v1/escrow-accounts/auth/me` — identifies an institution
   account.
2. On 401, fall back to `GET /api/v1/escrow-signatories/auth/me`.
3. Only when both fail does the page bounce to `/escrow/login`.

When the signatory path matches, a new **`EscrowSignatoryDashboard`**
component renders. It reads from `GET /api/v1/escrow-signatories/dashboard`
(unchanged, pre-existing endpoint) and shows:

- Signatory name + the institutions they're registered on.
- Three KPI tiles: *Awaiting your signature*, *Joint accounts you can
  sign*, *Total transactions*.
- Three tables: pending signatures, joint accounts, recent transactions.

So after setting a password from the magic link, the user now lands
cleanly on their signatory dashboard — no more redirect loop, no more
"same credentials don't work" because they ARE the right credentials;
they just have to be checked against the right endpoint.

### Deploy

1. **Backend** — `pmc-backend-v53n.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53n-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. Re-approve the institution if needed so a fresh magic link goes out,
   or ask the signatory to click the same link again — set-password
   now completes and lands them on the signatory dashboard.

### Files touched

- Frontend
  - `apps/escrow-portal/EscrowMePage.jsx` — try both account AND
    signatory /auth/me endpoints.
  - `apps/escrow-portal/EscrowSignatoryDashboard.jsx` — NEW. Signatory
    view with KPIs + pending signatures + joint accounts + transactions.

(Backend bundle is unchanged vs v53m — included only so a fresh deploy
is self-contained.)
