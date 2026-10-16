# PMC Managers Limited — Release v49k

## What's new in v49k

### 1 · Negative amounts are now rejected server-side (422)
`NoticeIn` already guarded `budget_amount` with `ge=0`, but
`extra="allow"` let `tender_fee`, `emd_config` and other money-ish
fields pass through unvalidated. Added a `@model_validator(mode="after")`
on `NoticeIn` that sweeps:
- `budget_amount`, `tender_fee`
- every key inside `emd_config`
- every extra field whose name contains `amount` / `fee` / `emd` /
  `price` / `value`

and refuses any negative value with a clear `"<field> cannot be negative"`
error.

Verified live:
- `budget_amount: -5000` → **422**
- `tender_fee: -100` → **422** (`"tender_fee cannot be negative"`)
- `emd_config.amount: -500` → **422**
- Valid create (`budget 50000, fee 0, emd 1500`) → **200**,
  `PMC-NOT-2026-0031` created.

A database sweep confirmed **no existing notice currently holds a negative
amount** — nothing to repair.

### 2 · Vendor identity pill now has a real menu (sign-out + avatar)
The `.pmc-who` pill on every vendor page declared `aria-haspopup="menu"`
but no menu existed — vendors had **no sign-out button anywhere**. The
delegated click handler in `PmcLinkPatcher` now opens a dropdown:

- **Account & security** → `/vendor/account`
- **Change photo** → opens the avatar file picker (PNG/JPEG/WebP, ≤ 2.5 MB)
  and uploads via `POST /api/v1/vendor/auth/avatar`; the new photo is
  painted into every `.pmc-avatar` badge on screen immediately.
- **Sign out** → calls vendor + admin logout, toasts "Signed out", lands
  on `/login`.

On admin pages the same pill opens a menu with **Sign out**.

Verified live: login → click pill → menu opens with all three items →
Sign out → redirected to `/login`; revisiting `/vendor` bounces back to
login (session really dead).

### 3 · Carried over from v49j (same release branch)
- Global event-delegation architecture for all Option-E pages (no more
  dead buttons when live-data hooks rewrite the DOM).
- In-app change-password modal (current + new + confirm) from Account &
  Security — no email round-trip.
- Notice-detail Download buttons wired to real attachments when present,
  register-gate for guests otherwise.

## Bundles
- **Frontend:** `pmc-frontend-v49k-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49k.zip` (416 KB — includes the validator;
  redeploy this one)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- Backend: upload to Elastic Beanstalk (validator needs to be live).
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49i` if needed.
