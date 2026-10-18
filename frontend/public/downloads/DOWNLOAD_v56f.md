# PMC Managers — Release v56f (18 Jun 2026)

## New — PMC officer can see & sign the escrow document inside the staff portal
The staff portal now shows the PMC officer their own escrow signing work.

- Staff dashboard has an **"Escrow documents — your signature"** section listing
  every escrow transaction where the logged-in staff member is the named PMC
  officer (pending ones highlighted). Per row:
  - **Open in DocuSign to sign** (Safari-safe: tab opened synchronously).
  - **Refresh DocuSign** — pulls live envelope status + reconciles on demand.
  - **Download signed PDF** — appears once the executed document is available.
- Scoped endpoints (only the officer's own transactions; 403 otherwise):
  - `GET /api/v1/staff/escrow/signatures`
  - `GET /api/v1/staff/escrow/transactions/{tid}`
  - `GET /api/v1/staff/escrow/transactions/{tid}/docusign-url`
  - `POST /api/v1/staff/escrow/transactions/{tid}/docusign/refresh`
  - `GET /api/v1/staff/escrow/transactions/{tid}/signed-document`

## Fix — the signed PDF now actually reaches the signers
On DocuSign **completion**, `_deliver_escrow_signed_document()` downloads the
COMBINED signed PDF, stores it on the transaction (`signed_document`) and
EMAILS it as an attachment to BOTH officers — including the escrow institution
officer (e.g. Sakina). Previously only the status flag was updated, so the
executed document never reached the inbox or the dashboard. Idempotent +
best-effort; fires via the Connect webhook OR the manual Refresh DocuSign.

## Fix — staff portal readability
Staff dashboard forced to a solid light background (#eef2f7) with dark text;
contrast strengthened on bid refs, signature chips and secondary buttons.

## Artifacts
- Backend: `pmc-backend-v56f.zip`  ·  Frontend: `pmc-frontend-v56f-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. CloudFront `/*` invalidation. 4. Footer should read Frontend v56f · Backend v56f.

## How to confirm the signed-PDF fix in production
On the real EMD bid (e.g. PMC-BID-2026-00060), after both officers sign via
DocuSign, open the transaction and click **Refresh DocuSign** → status flips to
completed, both signatures show Signed, the signed PDF is emailed to both
officers, and a **Download signed PDF** button appears on the dashboard.
