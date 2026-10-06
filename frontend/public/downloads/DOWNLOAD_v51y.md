# PMC Managers — Release v51y (cumulative, supersedes v51o–v51x)

## P0 fixes in this build

### 1. "This panel hit an error" on every Money & compliance page — FIXED
Root cause: `InfoDot` (the inline ⓘ help icon) rendered as a `<button>`
inside parent `<button>` elements on Evaluation, L1 comparison,
Permissions, Awards, etc. React 18 production builds throw a real
error on `<button>` nested in `<button>`, which the shared
`ErrorBoundary` caught and surfaced as "This panel hit an error …
role-mismatched cookies can cause this."

Fix in `frontend/src/components/InfoDot.jsx` — one component change
that clears the crash across every panel that uses InfoDot.

### 2. Reverse auction HTTP 400 on Start — WORKAROUND SHIPPED
The 400 is a correct guardrail (`need at least 2 registered
participants`). What was missing was any UI to actually invite vendors
from the admin console — the backend already had `/invite`, but the
Admin → Money → Reverse auctions page didn't expose it.

Fix in `frontend/src/apps/admin-console-e/AdminAuctionsE.jsx` — each
auction row now has an **Invite vendors** button that opens an inline
panel with:
- paste-emails textarea (comma / newline / space separated)
- optional note
- list of registered participants (+ their aliases)
- list of pending invite links with **Copy link** (share any channel)

Flow: Draft → Invite vendors → vendors register → Start.

### 3. Admin Notices filter bar — unchanged from v51x
Still provides tender ref / title / creator / date-range / status
(incl. Draft) / template-only / clear.

## How to deploy
1. Upload `pmc-frontend-v51y-prod-build.zip` to the S3 bucket, extract
   to the site root, invalidate CloudFront `/*`.
2. Deploy `pmc-backend-v51y.zip` to Elastic Beanstalk (no new secrets).
3. Hard-refresh https://www.pmcmanagers.com, log in, open any Money &
   compliance page — the "This panel hit an error" page is gone.

Keep in mind production is user-managed; preview has been verified.
