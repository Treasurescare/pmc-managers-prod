# PMC Managers — Release v53a (frontend only)

## What changed since v52z

### Vendor "Registered address" change form — masters-driven cascade
The address change form (Vendor portal → Account → Request change →
Registered address) is rebuilt around the geography masters instead of
free-text fields:

**New field order:** Country → State / County → City → Address line 1 →
Address line 2 (optional) → ZIP / postal code.

- **Country** — full 250-country master (`/api/v1/masters/countries`);
  previously only the ~30 licence-mapped countries.
- **State / County** — cascades from the states master for the chosen
  country (KZ shows 20 regions, etc.). Falls back to a free-text input
  only for countries with no states in the master.
- **City** — type-to-search against the 150k-row cities master, filtered
  by the selected state (datalist; free text still accepted for villages
  not in the master).
- **Address line 1** (required) and **Address line 2** (optional) replace
  the single "Street address" blob.
- Validation: country + city + address line 1 + ZIP required; state
  required only when the master has states for that country.
- Submitted `address_parts` now carry `address1/address2/state_code` so the
  admin approval view renders a clean structured address. The composed
  one-line value keeps the old format for the public profile.

**Verified:** masters cascade curl-tested (KZ → 20 states → cities by
state; free-text city search `q=alm` → Almaty); frontend build clean;
UI screenshot-verified in preview (vendor login → account → address form,
cascade live).

### Also in this session (already shipped in v52z bundle line)
- Create Notice 422 ("String should have at most 3 characters") fixed in
  v52z — see DOWNLOAD_v52z.md.

## Deploy

Frontend only: unzip `pmc-frontend-v53a-prod-build.zip` to the S3 bucket
root, CloudFront invalidate `/*`.

## Reminder — production email silence
Preview sends vendor profile-change emails fine (Resend 200 on test).
Production isn't delivering → the EB environment is missing
`RESEND_API_KEY` (same root cause as EB_ENV_FIX_missing_RESEND_key.md).
Add `RESEND_API_KEY` + `EMAIL_FROM_ADDRESS=admin@mail.pmcmanagers.com` to
EB env properties or the `/pmc/prod` SSM path and redeploy.
