# PMC Managers — Release v51af (frontend + backend)

## What's fixed
**Registrations → "Edit sections" did nothing / bounced to /register.**
Three gates were stacked against the admin:

1. **Missing magic tokens** — 11 legacy registrations (created before magic
   links existed) had no `magic_token`, so the resume URL was built with
   `token=` empty and the resume page silently redirected to `/register`.
   → `GET /api/v1/registrations/admin/{rid}/resume-link` now mints and
   persists a token on demand. Heals lazily per click; no migration needed.
2. **Read-only status screen** — the resume page rendered a static
   "Submitted — under review" card for any non-draft registration.
   → When opened with `?from=admin` it now renders the full editable
   5-section stepper for any non-approved / non-rejected registration.
3. **Save blocked for submitted rows** — the public token PATCH only allows
   `draft` / `needs_clarification`.
   → New admin-only `PATCH /api/v1/registrations/admin/{rid}` (admin or
   reviewer role, CSRF-protected, audit-logged) saves section edits on
   submitted / under_review registrations. Protected fields
   (status, vendor_ref, magic_token, ids, timestamps) are stripped
   server-side.

## Verified
- Preview E2E: Edit sections on a `submitted` registration opens the editable
  form, Save draft returns success, no error toasts.
- API: resume-link returns a real token; admin PATCH preserves status and
  updates fields.

## Deploy
Upload pmc-frontend-v51af-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51af.zip to Elastic Beanstalk.
