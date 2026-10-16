# PMC Managers — Release v53d (frontend only)

## What changed since v53c

### 1. FIXED: Phone-change Submit button permanently greyed out
**Root cause (your exact bug):** `validatePhoneForCountry()` returns `null`
on success, and the Submit button's disabled check was
`phoneError !== ""`. After typing any valid number, `phoneError` became
`null` — and `null !== ""` is **true**, so the button stayed disabled
forever. No request ever reached the backend → no confirmation email →
zero rows in the DB. Matches exactly what you saw.

**Fix:** success now stores `""` instead of `null`. Verified in preview:
- 10 digits (valid KZ) → button **enabled**
- 6 digits → button disabled + "Kazakhstan mobile numbers must be exactly
  10 digits (you entered 6)."

After deploy, the flow is: Submit request → confirmation email to your
current inbox → click link → admin approves under Market → Profile changes.

### 2. FIXED: Admin Reverse auctions "just says closed"
The v53b award button landed in a legacy component; the live admin panel
(`admin-console-e/AdminAuctionsE.jsx`) showed nothing on closed rows. Now
closed rows show:
- **Winner line:** "Won by <company> · USD 872,500 (−12.8%)" with the
  savings % vs start price
- **Award winner** button (dark) when a winner exists and hasn't been
  awarded → creates the `emd_paid` bid into Bidding Ops (v53b backend,
  idempotent)
- **"Awarded · in pipeline"** badge once awarded
- "Closed with no winning bid — nothing to award" for bid-less closes

Verified in preview: closed row renders winner line + AWARD WINNER button.

## Deploy

Frontend only: unzip `pmc-frontend-v53d-prod-build.zip` to S3 root,
CloudFront invalidate `/*`. (Backend v53b from earlier carries the
/award endpoint — make sure it's on EB.)
