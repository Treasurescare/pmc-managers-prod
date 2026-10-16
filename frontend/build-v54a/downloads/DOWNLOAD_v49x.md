# PMC Managers Limited — Release v49x

## What's fixed (3 issues — root causes verified on production)

### 1. Sidebar still scrolled (v49w sticky fix defeated)
Verified on production: the sidebar computed `position: sticky` but still
moved with the page. Root cause: the global rule
`html, body { overflow-x: hidden }` (pmc-responsive.css, applied at ALL
widths) creates a new scroll container on body, which silently breaks
`position: sticky` everywhere — sidebar, sticky top bars, everything.

Fix (`frontend/src/pmc-responsive.css`):
- Global rule changed to `overflow-x: clip` — stops horizontal bleed but
  does NOT create a scroll container, so sticky works again.
- Sidebar rule hardened to `position: fixed; top: 0; left: 0;
  width: 260px; height: 100vh; overflow-y: auto` (desktop ≥1101 px).
  Fixed positioning is immune to ancestor overflow. The `.pmc-adm` grid
  keeps its explicit 260px first track, so the main column never shifts.
  Mobile drawer behaviour is untouched.

### 2. "Open the full Help Centre" inside the drawer didn't navigate
Verified on production: clicking it left you on the same page. Root
cause: the Help-trigger regex `/help|faqs?/` in PmcLinkPatcher matched
the label "open the full help centre" and re-dispatched the drawer-open
event instead of navigating to `/help`. (This is also why it "worked
after opening another tab and coming back" — DOM order changed which
drawer was on top.)

Fix (`PmcLinkPatcher.jsx`): anchors with a real `/help...` href now
navigate to the Help Centre (and close the drawer) BEFORE the
drawer-trigger regex runs.

### 3. DocuSign "resend" (and initial send) never emailed signers
Verified on production: the resend API works (v49w backend returned
`resent_to`), BUT your real envelopes are `delivery: embedded`. Setting
`client_user_id` tells DocuSign to deliberately NOT email the signer —
embedded means in-portal signing only. So no email ever goes out for
those envelopes, at creation or resend. (Envelopes created with
delivery = "email" do get DocuSign-hosted emails.)

Fix (`backend/routers/docusign.py`):
- New `_email_signer()` helper sends a branded Resend email with a link
  to the supplier portal Signatures page.
- Award envelopes (embedded) → signer is emailed at creation.
- Bid-acknowledgement envelopes (always embedded) → emailed at creation.
- Resend on an embedded envelope → reminder email goes out, response
  includes `emailed: <signer email>` so the UI can confirm.
- Email-delivery envelopes still resend via DocuSign's own reminder.

Service-worker cache bumped to `pmc-shell-v49x-rev1`.

## Bundles
* Frontend: `pmc-frontend-v49x-prod-build.zip` (same-origin build;
  includes v49r→v49w).
* Backend: `pmc-backend-v49x.zip` — REQUIRED (DocuSign email fix).

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.
Backend — Elastic Beanstalk: upload `pmc-backend-v49x.zip`, wait for
Health = OK.

Verify:
- Admin dashboard: scroll a long page — sidebar stays fixed with its own
  scrollbar.
- Open Help → "Open the full Help Centre" → lands on `/help`.
- DocuSign → Resend on a sent envelope → signer receives a reminder
  email (check spam too); embedded envelopes now email the portal link.

## Rollback
Frontend v49w / backend v49w. No schema changes.
