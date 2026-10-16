# PMC Managers — Release v51ab (cumulative, supersedes v51aa)

## What's new in v51ab
1. **Reverse auctions** — new per-row **Edit** button on every draft auction
   that opens an inline form to change title, start/floor/decrement prices,
   duration, currency, anti-snipe seconds (backend PATCH /reverse-auctions/{aid}
   with validations).
2. **Working Money & compliance search bar on every panel**:
   - Reverse auctions, Bidding ops, Awards, Billing, Escrow / EMD,
     Evaluation, L1 comparison, DocuSign.
   - Shared `MoneyFilterBar` component: search tender/title, created-by,
     created from→to date, expires from→to date, status dropdown, Clear.
   - Reverse auctions filters its React state array (true client-side filter);
     Bidding ops and legacy panels filter their rendered rows via a
     MutationObserver so even DOM-rendered tables respond.
3. All v51aa fixes carried forward: Money crash fix, auction invites + Resend
   auto-send + readiness badge, Notices filter URL memory, blank Contact Email
   422 coercion, bulk-invite Sections A–E CSV, 409 "already active" structured
   detail, full vendor-profile editor at /admin/vendors/:ref/edit.

## Deploy
Upload pmc-frontend-v51ab-prod-build.zip to S3, invalidate CloudFront /*,
push pmc-backend-v51ab.zip to Elastic Beanstalk. No new secrets.

## Up next (post-v51ab, from the user's roadmap)
Corrigenda module (edit live tenders with amendment trail + vendor re-ack).
