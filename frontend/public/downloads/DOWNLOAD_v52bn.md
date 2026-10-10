# PMC Managers — Release v52bn (10 Oct 2026)

Frontend-only update (backend unchanged from v52bl).

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bn-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bn-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: keep [`/downloads/pmc-backend-v52bl.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bl.zip) — unchanged

## 🎯 What's in v52bn

1. **Public corrigendum diff table** — the public notice page (`/notices/:ref`) now renders every active corrigendum with its date, overall change description, and the full **Field · Before · After · Reason** table, so bidders see exactly what changed and why. Issuing admin emails are NOT shown (they stay in the internal audit ledger). Works on both the E-variant hero page and the legacy notice page; the "Corrigenda" tab scrolls to the section and shows the live count.

2. **Live-notice Edit → Corrigendum workspace** — on Admin → Notices, the per-row Edit button is now context-aware:
   - **Draft** notice → opens the inline edit modal (unchanged).
   - **Live** notice → routes to `/admin/e/corrigenda?notice=<ref>` with the notice preselected and the create form open. After publishing, you land on the public notice page to see the corrigendum exactly as bidders will.
   - Safety net: if the edit modal is opened for a live notice through any other path, it shows a "Live notice — issue a corrigendum" lock screen instead of editable fields.

3. **Attachments through corrigendum only (live notices)** — document Delete is locked on live notices in the View modal (with a hint), and each published corrigendum now has an **Attach document** action (revised BOQ, drawings, etc.) so every document change carries a date + reason in the audit trail.

4. Includes v52bm: create-notice validation stays on the same page (no redirect to Tender builder) + the 14-field corrigendum current/new/reason editor.

## 🚀 Deploy

```bash
aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```
Backend: no redeploy needed (keep v52bl).
