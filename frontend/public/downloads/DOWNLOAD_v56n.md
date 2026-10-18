# PMC Managers — Release v56n

Builds on v56m (public-site navigation wiring) with four upgrades + a Sign-in fix.

## What changed
- **Live Verify (Trust & Security):** the "Verify a record" box now calls the ledger
  and recomputes a record's SHA-256 link, showing **Record intact** or a **chain break**
  with the event #, target, prev and current hash. Works by reference (e.g.
  `PMC-AWD-2026-00025`) or ledger event number (e.g. `1745`).
  New public endpoint: `GET /api/v1/audit-events/verify-record?ref=…`.
- **Tender deep-links:** clicking a homepage live-board row or a tender card now opens
  that notice's full detail page (`/notices/<ref>`) instead of the register gate.
- **Contact form delivery:** the Contact "Send message" form posts a real enquiry,
  returns a tracked reference (`ENQ-2026-#####`), logs it to the audit ledger, and
  emails the PMC desk plus an acknowledgement to the sender.
  New public endpoint: `POST /api/v1/meta/public/contact`.
- **Status filter links:** the "Closing this week" chip → `/tenders/live?status=closing`;
  the Awards page "Awarded in 2026" tile → `/tenders/live?status=awarded` (the tenders
  list now reads `?status=`).
- **Sign in** now opens the Option-E unified sign-in at `/login` (Supplier / PMC staff /
  Administrator / Escrow chooser) instead of the legacy navy vendor-login page.

## Deploy order
1. Upload `pmc-backend-v56n.zip` to Elastic Beanstalk; wait for green/healthy.
2. Upload the **contents** of `pmc-frontend-v56n-prod-build.zip` to the S3 bucket root.
3. CloudFront → invalidate `/*`.
4. Confirm the footer shows **Frontend v56n · Backend v56n**.

## Files
- Backend:  `pmc-backend-v56n.zip`
- Frontend: `pmc-frontend-v56n-prod-build.zip`
