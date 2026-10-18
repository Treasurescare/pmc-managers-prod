# PMC Managers — Release v56k (18 Jun 2026)

## Hard governance gate — release to contractor only AFTER full clearance
EMD can now only be **released to the contractor** once the bid has cleared the
full evaluation chain — escrow acceptance → certifier → legal → accounting →
committee award (bid status = `awarded`). The gate is enforced in TWO places:

- **Signing** a `release_to_contractor` action (`/transactions/{tid}/sign`) is
  refused unless the bid is awarded.
- **Release** (`/transactions/{tid}/release`) is refused unless the bid is awarded.

If the bid isn't awarded yet, the API returns a clear 409 naming the pending
stage, e.g. *"Release to contractor is blocked — bid PMC-BID-… is
'accounting_cleared', not awarded yet … (pending: committee award / admin
sign-off)."*

**Not gated:** `release_to_vendor` (refund to a losing vendor) and `forfeit` —
these can legitimately happen before/without an award.

Verified: non-awarded bid blocks both sign and release (409); an awarded bid
signs and releases successfully (status → `released_to_contractor`).

## Artifacts
- Backend: `pmc-backend-v56k.zip`  ·  Frontend: `pmc-frontend-v56k-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. **CloudFront `/*` invalidation**. 4. Hard refresh → footer v56k / v56k.
(Frontend is unchanged in logic this release — only the version stamp — but ship
both so the footer and cache version stay in sync.)
