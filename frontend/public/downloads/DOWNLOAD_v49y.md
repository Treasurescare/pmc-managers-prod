# PMC Managers Limited — Release v49y (backend) — deploy with frontend v49x

## What this fixes
### DocuSign completion confirmation never reached the admin panel
User report: signer completes the ceremony (email mode AND embedded
mode), but the admin panel never shows the signing as complete.

Root cause: the only path that learned about completion was the
DocuSign Connect webhook (`POST /api/v1/docusign/webhook`). Connect is
configured inside the DocuSign account, not in code — it was never
firing. The admin list endpoint only read our Mongo rows, so envelopes
stayed "sent" forever.

Fixes (`backend/routers/docusign.py`):
1. **Polling sync** — `_sync_recent_statuses()` pulls DocuSign
   `list_status_changes` (one API call, last 30 days) and applies
   updates. It runs automatically on:
   - Admin DocuSign panel load (`GET /docusign/envelopes`)
   - Vendor signatures list (`GET /docusign/mine`)
   No webhook dependency. If DocuSign is unreachable the lists still
   return (sync is best-effort).
2. **Completion side effects** — `_on_envelope_completed()` fires the
   moment an envelope transitions to `completed` (via sync OR webhook):
   - In-app + email notification to all admin users ("Signed: <ref>")
   - Confirmation email to the signer with a portal download link
   - Audit-ledger entry `docusign.envelope_completed`
   - Bid stamped with `<po|sla|contract>_signed_at`
3. Webhook handler now routes through the same `_apply_live_status()`
   so Connect (if you ever enable it) triggers the same side effects.

## Current signing flow (as built)
Single signer = the vendor/customer. On completion the signed PDF is
downloadable by admin (`/docusign/envelopes/{id}/combined-pdf`) and by
the vendor in their portal. There is no PMC countersignature step
inside DocuSign today — tell us if you want the two-party flow
(vendor signs → PMC countersigns → completed copy auto-emailed back).

## Bundles to deploy (you have NOT deployed v49w/x yet — skip them)
* **Frontend: `pmc-frontend-v49x-prod-build.zip`** → S3 + CloudFront,
  invalidate `/*`. (Sidebar fixed, Help Centre navigation, downloads,
  dashboard counts, notifications, sign-in⇄register links, Safari
  popup fix — everything frontend to date.)
* **Backend: `pmc-backend-v49y.zip`** → Elastic Beanstalk. (DocuSign:
  resend actually resends, embedded envelopes email the signer via
  Resend, completion confirmations + status sync.) Includes the
  Dockerfile, Dockerrun.aws.json and .platform/ at the zip root.

## Verify after deploy
1. Sign a test envelope to completion (either delivery mode).
2. Open Admin → DocuSign: envelope shows **completed** (no manual
   refresh of each envelope needed).
3. Admin gets a notification + email "Signed: <ref>"; signer gets a
   confirmation email with the portal link.
4. Audit ledger shows `docusign.envelope_completed`.

## Rollback
Backend v49q. No schema changes.
