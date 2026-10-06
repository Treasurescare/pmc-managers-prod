# PMC Managers v2 — PRD (as of 06 Oct 2026 / v51aa)

## Original problem statement
End-to-end procurement & tender management platform (public notice board,
vendor portal, staff portal, admin console) built as React (CRA + CRACO) +
FastAPI + MongoDB. Option E forest-green / navy / brass visual system.
User manages their own S3 + CloudFront frontend and Elastic Beanstalk
backend deployments.

## Latest release — v51aa (06 Oct 2026, this session)

Builds on v51z with three admin-vendor-flow improvements:

1. **Bulk-invite CSV template covering all 5 vendor registration sections.**
   New GET /api/v1/vendors/invite-bulk/template emits a ~45-column CSV
   spanning identity, contact, banking, business profile, declarations
   and signature. The invite-bulk parser coerces lists, booleans, ints,
   and floats, and stores everything under the vendor's `profile`
   sub-dict so the vendor sees their draft pre-filled at first login.

2. **Clearer 409 invite handling.** Admin invites with an email that is
   already an active vendor now receive a structured 409 detail with
   `vendor_ref` and `company_name`; the admin UI shows a Sonner toast
   with an inline "Edit full profile" action.

3. **Edit the whole vendor portal profile.** New route
   `/admin/vendors/:vendor_ref/edit` reuses the Sections A–E stepper
   pre-filled from the existing vendor record. Each tab has its own
   Save button; backend `PATCH /admin/{ref}/full` merge-patches the
   profile sub-doc and audit-logs with `profile_updated_at`,
   `profile_updated_by`. Every vendor row in the admin panel exposes
   an "Edit full profile" link.

## Earlier v51 fixes still live in this build
- Money / compliance panel crash (InfoDot button-in-button fix)
- Reverse-auction Invite panel + Resend auto-email + readiness badges
- Notice filter bar with URL memory + Draft/Awaiting approval status
- Notice submit-for-approval 422 (blank Contact Email coerced to None)

## Deployment artifacts
- `frontend/public/downloads/pmc-frontend-v51aa-prod-build.zip`
- `frontend/public/downloads/pmc-backend-v51aa.zip`
- `frontend/public/downloads/DOWNLOAD_v51aa.md`

## Architecture
React CRA + CRACO + Tailwind + Radix + shadcn-ui on the frontend;
FastAPI + Motor (async MongoDB) on the backend; Mongo config via
`MONGO_URL` + `DB_NAME`; frontend API base via `REACT_APP_BACKEND_URL`;
Admin/Vendor/Staff auth via JWT + CSRF.

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback).

## Known backlog
- Mobile-fix.css has grown large; defer refactor.
- Legacy and E routes coexist; verify which is live before changes.
- v51aa production rollout verification pending user action.
- Minor: invite-bulk silently drops malformed numeric cells; could
  surface per-cell parse warnings in the result table.
