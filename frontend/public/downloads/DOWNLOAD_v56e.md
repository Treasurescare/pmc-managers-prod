# PMC Managers — Release v56e (18 Jun 2026)

## Fix — escrow DocuSign completion now reflects on the dashboard
Previously, when both officers signed the escrow DocuSign envelope, the status
callback only updated bids/awards — it never touched the escrow **transaction**,
so the dashboard stayed "Awaiting signature" and Release never unlocked.

- `_apply_live_status` now reconciles `kind=escrow_tx` envelopes: mirrors the
  DocuSign status onto the transaction and, on **completed**, records both
  officer acknowledgements (signatures flip to Signed) + an audit entry.
- New **Refresh DocuSign** button on each sent-but-not-completed transaction
  (admin Escrow/EMD) pulls the live envelope status on demand and reconciles —
  works even if the DocuSign Connect webhook isn't configured in production.
  Endpoint: `POST /api/v1/escrow/transactions/{tid}/docusign/refresh`.

Note: the signed/combined PDF download into the dashboard, and the DocuSign
"completed" email to signers (an account-level DocuSign Connect/notification
setting), are tracked as the next items.

## Artifacts
- Backend: `pmc-backend-v56e.zip`  ·  Frontend: `pmc-frontend-v56e-prod-build.zip`

## Deploy
1. Backend zip → Elastic Beanstalk (wait green). 2. Frontend build → S3 root.
3. CloudFront `/*` invalidation. 4. Footer should read Frontend v56e · Backend v56e.

## How to use after signing
After both officers sign via DocuSign, click **Refresh DocuSign** on that
transaction (or wait for the webhook) → signatures flip to Signed and Release
unlocks once both signed the same action.
