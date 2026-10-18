# PMC Managers — Release v56g (18 Jun 2026)

## Fix — Staff portal is readable again + has a sidebar
The staff dashboard text was washed out because the global Option-E dark theme
(`[data-ui="e"]`) repaints `bg-slate-*` / some `text-slate-*` utilities. The
dashboard is rewritten with a **left sidebar** (Overview · Escrow signatures ·
Work queue · Site inspections) and **explicit inline colours** so the theme can
never wash it out. Everything is dark-on-light and legible.

## Fix — PMC officer can now actually SIGN (DocuSign embedded signing)
Previously "Open in DocuSign" used `create_console_view`, a view-only sender
console — so the PMC officer only saw the document and could never sign.
We switched to **embedded signing**:
- Envelope recipients are now created with a `client_user_id` (both PMC +
  institution officers).
- "Open in DocuSign" mints a one-time **recipient-view** signing URL
  (`create_recipient_view`) with a **return_url** back to the originating
  portal, and navigates there in the same tab. After signing, DocuSign
  redirects back to the portal (`/staff?signed=1`, `/escrow/me?signed=1`,
  `/admin?signed=1`) — not the DocuSign email login — and the portal
  reconciles the signature automatically.
- Legacy email-mode envelopes are auto-converted to embedded via
  `update_recipients` on first open; if a particular envelope can't be
  converted, re-issue it (Send DocuSign) to create an embedded one.

## On completion — signed PDF delivered to everyone
When both officers finish, the combined signed PDF is downloaded, stored on the
transaction and **emailed as an attachment** to both officers AND the admin who
issued the envelope. A **Download signed PDF** button appears on the dashboard.

## Artifacts
- Backend: `pmc-backend-v56g.zip`  ·  Frontend: `pmc-frontend-v56g-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. CloudFront `/*` invalidation. 4. Hard-refresh; footer should read v56g.

## Important
Embedded DocuSign signing could NOT be fully exercised in the preview
environment (DocuSign JWT is not configured there → the signing-URL call
returns 424 and the UI shows a graceful toast). The code follows DocuSign's
official embedded-signing pattern and must be validated on PRODUCTION, where
DocuSign is configured: open PMC-BID-2026-00060, re-issue the envelope so it is
embedded, then both officers sign in-portal and get returned to their
dashboards with the signed PDF emailed to all parties.
