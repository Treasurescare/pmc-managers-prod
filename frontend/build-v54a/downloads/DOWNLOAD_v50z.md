# PMC Managers — Release v50z (cumulative v50m → v50z)

## Fixes in this build
- **Vendor password/activation emails now open the new login page**:
  the "Sign in" button in invite, activation and registration-approved
  emails pointed to the legacy `/vendor/login` (old split-screen page).
  All three now link to the unified `/login`.
- **DocuSign envelope scoping fixed**: `/api/v1/docusign/mine` matched
  envelopes purely by email, so a re-registered vendor reusing an email
  address inherited every envelope from the previous registration
  (the "new vendor sees 3 documents to sign" bug). Now scoped by the
  current vendor record's bid ownership, and signer_email matches only
  count for envelopes created after this registration.

## Deploy (backend REQUIRED — both fixes are backend-side)
1. `pmc-backend-v50z.zip` → Elastic Beanstalk
2. `pmc-frontend-v50z-prod-build.zip` → S3 + CloudFront `/*`
   (identical to v50y frontend; safe to skip if v50y already deployed)
