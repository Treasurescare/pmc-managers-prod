# PMC Managers — Release v51t (cumulative, supersedes v51o–v51s)

## Fixes & features in this build

### 1. Admin Registrations — tap-to-inline detail on mobile
Same pattern as the Vendors list: on narrow screens, tapping a
registration opens the review panel INLINE directly below the tapped
row (instead of at the far bottom of the page). Desktop keeps the
right-hand column.

### 2. Vendor Change Password screen — no more mobile overflow
The 2-column hero/form grid was fixed to `minmax(0,1fr) minmax(0,1fr)`
with 48px padding, so inputs overflowed on phones. The grid now
collapses to a single column at ≤1023px with reduced padding; the hero
headline shrinks from 56 to 32px.

### 3. Admin avatar dropdown — React Portal (final fix)
The dropdown is now rendered via `createPortal(document.body)` so no
ancestor overflow/clip can hide it. Its position is computed from the
button's bounding rect on open + on resize/scroll. On ≤767px it also
hides the Create / Help button LABELS (keeping icons) so the topbar
row doesn't push the avatar past the right edge.

### 4. Company Name request change — supporting document now required
Vendors changing their company name must attach a scanned
**Certificate of Incorporation** or **Change-of-Name Certificate**.
The dialog shows a yellow help panel explaining this. The Submit
button stays disabled until an evidence file is uploaded.
Mobile / office-phone / address changes also offer an optional
evidence upload (phone bill, utility bill) that admins see in the
Masters → Profile change requests panel.

### 5. Office tel / mobile verification before admin approval
A new confirmation gate: when a vendor requests a mobile or office-
telephone change, the backend emails a click-link to the vendor's
**current email**. The vendor must click it before admin can approve.
The admin panel shows a yellow "⚠ Awaiting vendor confirmation on
current email" badge until confirmed, then a green "✓ Confirmed by
vendor" badge. Attempting to approve without confirmation returns
HTTP 412 with a clear error. Email changes already had this gate via
the NEW address; email changes still work as before.

> **Note on full SMS OTP**: A real SMS OTP to the new mobile number
> (not just an email click-link) still needs an SMS gateway (Twilio or
> MessageBird) which is not integrated. The current dual-channel flow
> — click-link to current email + optional phone-bill evidence — is
> what admin reviews today. Let us know when you want to turn on SMS
> OTP and we'll wire the gateway.

### Also included (v51o–v51s)
- Bidding Ops: tabs wrap, counts match visible rows, row-card checkbox.
- Admin drawer: scrolls to Masters on iOS (100dvh).
- Admin Vendors: toolbar wraps 2-up; tap-to-inline KPI/KYC detail;
  giant-button padding bug fixed.
- Masters: 13 tabs visible as wrapping chips.
- Start-bid: Submit visible above tab bar; uploaded files readable
  with View link; upload slots stack 1-col on phones.
- Mobile tab bar: Home · Tenders · My Bids · Sign · Account.
- Vendor Account: Password + Other devices rows wrap cleanly.

## Deploy
- Frontend: `pmc-frontend-v51t-prod-build.zip` → S3, CloudFront
  invalidate `/*`. Supersedes v51o–v51s.
- Backend: **CHANGED** since v51n — must deploy `pmc-backend-v51t.zip`
  to Elastic Beanstalk (new /phone-verify endpoint, new ChangeRequestIn
  fields, phone-confirmation gate on admin approve).
