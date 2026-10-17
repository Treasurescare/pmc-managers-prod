# PMC Managers v54f — Resume-link repair (token=undefined fix)

Release target: 17 Feb 2026

**Contains v54a…v54e plus this fix. Deploy this pair and skip earlier ones.**

## The bug you reported

Clicking the resume link from the email landed on
`/register/resume?token=undefined` — the form appeared empty/foreign,
uploads failed with "Enter the vendor email first", and the page bounced
you to a fresh registration with no email populated.

## Root cause

When a draft already exists for an email, the backend deliberately omits
the magic token from the API response (SEC-002 — never hand a private
token to whoever types an address). The start page navigated to
`/register/resume?token=${r.magic_token}` unconditionally, so the URL
became `token=undefined`, the resume fetch 404'd, and everything
downstream (uploads, view/download, the missing email) failed.

## Fixes

1. **Start page**: only navigates to the resume URL when a real token
   exists. On the existing-draft path it now tells you to continue from
   the freshly re-sent email and shows which address it went to.
2. **Resume page**: treats `undefined` / `null` / missing tokens as an
   invalid link — clear message + back to start to request a fresh link,
   instead of a confusing bounce.
3. **Resume page now displays the vendor's email** ("Registering as
   vendor@company.com · private draft link") at the top of the form, so
   the vendor immediately sees the form knows who they are.
4. **Backend**: legacy registration rows created before magic tokens
   existed get a token minted on first use (SEC-002 re-request, reminder
   emails, clarification emails) — previously those paths could 500 with
   a KeyError.

## Verified

- Fresh draft → token returned ✓
- Duplicate email → `{"ok": true, "message": …}`, no token ✓
- Legacy row (token stripped) → re-request succeeds, new token minted ✓
- All v54e registration checks remain green ✓

## Artifacts

* Backend: `pmc-backend-v54f.zip`
* Frontend: `pmc-frontend-v54f-prod-build.zip`
