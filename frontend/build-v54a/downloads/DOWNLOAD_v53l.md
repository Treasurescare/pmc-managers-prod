# PMC Managers — Release v53l (frontend + backend)

## What's new since v53k

Two small follow-ups to the v53k joint-escrow rework.

### 1. "Signatory required" badge on every out-of-sync account
Each joint escrow row now compares its current signers to the signatory
pool and flags anything the EMD-release step would fail on:
- the account's `institution` legal_name doesn't match any approved
  escrow institution master row, OR
- the PMC officer email isn't in the escrow-signatory staff pool, OR
- the escrow officer email isn't a signatory of the matched institution.
Red **SIGNATORY REQUIRED** badge next to the account name, red `✗` next
to each specific officer whose email is out of pool, and a detail list
telling the admin exactly which of the three parts is broken.

### 2. One-click "Backfill" per broken row
`POST /api/v1/escrow/accounts/{aid}/backfill-signers` (admin-only).
Rules it runs:
1. Match `institution` → approved institution master (case + whitespace
   insensitive). If no match, returns 409 with the three closest
   legal_name suggestions so the admin can fix the master and retry.
2. If the PMC officer's current email matches a flagged staff → refresh
   the row's name + designation from the master (preserves history,
   fixes typos / stale designations).
3. If the escrow officer's current email matches a signatory of the
   matched institution → refresh name + designation.
4. Otherwise, if the institution has at least one signatory, swap the
   escrow officer to its first registered signatory.
5. Audit event `escrow.account.backfill_signers` is written with a full
   `diagnostics` object showing exactly which pieces were refreshed vs.
   swapped vs. left as-is.

UI: a red **BACKFILL** button appears on every row flagged
"signatory required". Admin clicks, confirms the summary of what the
backfill will change, and the row auto-refreshes with the fixed signers.

## Known production issue (NOT in this bundle)

> "unable to login into escrow institution login. system crashes and
>  brings back to login — same with staff login"

This is a **production-side** regression. Preview with v53k runs both
flows cleanly:
- escrow institution login (`escrowdemo@pmcmanagers.com`) lands on
  `/escrow/me` dashboard.
- staff login returns 200 with csrf_token.

Attempting an automated RCA against your deployed site returned
*"v3 deployment not found"* — the deployer tool only works for Emergent
v3 apps, and your deployment is AWS Elastic Beanstalk + S3/CloudFront.
I can't inspect your production logs or secrets from here.

### Likely root causes (highest likelihood first)
1. **Stale frontend bundle on S3 while backend was already updated** —
   old UI calls deprecated login shape, backend 2xxs but the UI's then
   call to `/auth/me` with stale cookies 401s and the auth guard bounces
   you back. Fix: redeploy v53l frontend AND backend together, then
   CloudFront `invalidate /*`.
2. **COOKIE_DOMAIN mismatch** — backend sets the session cookie for the
   wrong domain, so the cookie never reaches `/auth/me`. Classic "bounce
   back to login" symptom. Check EB env var `COOKIE_DOMAIN` matches the
   exact deployed origin (e.g. `.pmcmanagers.com`).
3. **PASSWORD_PEPPER drift** — if `PASSWORD_PEPPER` was rotated on EB
   but the stored `password_hash` for `accounts@pmcmanagers.com` was
   generated against the old pepper, login will reject the correct
   password silently. The staff password change you ran was signed with
   the current pepper, so this would only hurt pre-rotation accounts.
4. **Browser cache** — a hard refresh (Cmd+Shift+R) after you redeploy
   should rule this out.

### How to confirm root cause yourself in 2 minutes
Open the deployed site, hit F12 → Network tab, then click Sign in.
Look at the login request:
- `POST /api/v1/staff/auth/login` → **status**
- `POST /api/v1/escrow-accounts/auth/login` → **status**

- If it's **200** and you still bounce back, root cause is #1 or #2
  (session cookie not reaching `/auth/me`). Grab the `Set-Cookie`
  response header on the login call; `Domain=` must exactly match the
  site you're on.
- If it's **401** / **403**, the credentials or `password_hash` are the
  issue → root cause #3. Reset the password AGAIN after you redeploy
  v53l backend so the hash is re-signed with the live pepper.
- If it's **500**, read the response body — most likely a Mongo/Resend
  env var is missing. Deploy with EB env vars matching
  `backend/.env.example` or whatever lives in SSM `/pmc/prod/`.

## Deploy

1. **Backend** — `pmc-backend-v53l.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53l-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. On any joint escrow account that was created before v53k, open
   Admin → Escrow and click the red **Backfill** button on each row
   with a **SIGNATORY REQUIRED** badge.

## Files touched

- Backend
  - `routers/escrow.py` — new `POST /accounts/{aid}/backfill-signers`;
    helper `_build_pool` and `_norm` shared with `/signatory-pool`.
- Frontend
  - `lib/api.js` — `escrowApi.backfillSigners(aid)`.
  - `apps/admin-console/escrow/EscrowAccountsSection.jsx` — per-row
    health evaluation + badge + ✗ marks + red Backfill button with
    diagnostics toast.
