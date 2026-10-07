# PMC Managers — Release v51ac (cumulative, supersedes v51ab)

## What's new in v51ac
1. **Edit sections for every non-approved registration.** In Admin →
   Market → Registrations each row for a Draft / Submitted / Needs
   clarification registration now shows an "Edit sections" link that
   opens the vendor's own 5-section flow in a new tab (admin can save
   on behalf of the vendor). Approved rows link to the full vendor
   profile editor at /admin/vendors/{ref}/edit (added in v51aa).
2. **Expires from / Expires to filters removed from panels that don't
   have an expiry concept** (Awards, Billing, Escrow/EMD, Evaluation,
   L1 comparison, DocuSign). Reverse auctions still exposes Expires
   from / to because reverse-auction rows carry an `end_at`.
3. All v51ab features retained: shared Money filter bar, reverse
   auction Edit per row, bulk Section A–E CSV template, 409 structured
   detail, Section A–E vendor-profile editor, auction readiness badge
   + Resend auto-send, notice filter URL memory, Money-pages crash fix.

Backend: new `GET /api/v1/registrations/admin/{rid}/resume-link` for
admins to open any non-approved registration in the vendor-facing
5-section flow (audit logged).

## Deploy
Upload pmc-frontend-v51ac-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51ac.zip to Elastic Beanstalk.
