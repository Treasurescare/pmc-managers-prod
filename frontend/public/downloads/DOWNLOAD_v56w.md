# PMC Managers — v56w (27 Jun 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v56w.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56w-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v56w · Backend v56w"

## What's new / fixed in v56w — responsive remediation batch
1. **Staff & Escrow portals now use the Admin shell** — `/staff` and `/escrow/me`
   adopt the shared Admin-E portal shell: desktop sidebar, mobile off-canvas
   drawer with a working tap-to-close scrim, a unified header and exactly ONE
   hamburger control (no duplicate chrome).
2. **Mobile portal context** — a title/breadcrumb (e.g. "Staff / Overview",
   "Escrow / All transactions") is now visible on mobile and updates with the tab.
3. **Escrow transaction mobile cards** — each transaction row renders as a labeled
   card (Bid, Notice, Amount, Status, Signatures) with no blank cells; empty Notice
   shows a "—" dash and the Signatures cell now reads "PMC pending · Us pending"
   instead of ambiguous dots.
4. **SignInE 820px** — collapses to a single clean column with no overflow.
5. **/privacy on mobile** — the first legal sub-nav pill ("Privacy notice") is no
   longer clipped under the fixed mobile topbar.
6. **Signature chips** — escrow transaction signature status now shows as small
   colour-coded chips (emerald "signed" / amber "pending" with a status dot) so
   signed vs pending reads at a glance, on desktop and mobile cards.

## Contract-type duplicate cleanup (do this once after deploy)
Admin console → Masters → Contract types → **Remove duplicates**. This calls the
idempotent `/api/v1/masters/dedupe-taxonomy` endpoint and is safe to run repeatedly.
(The preview DB was already clean — 0 duplicates — in this build's verification.)

Preview-verified: testing_agent iteration 113 confirmed all 6 iteration-112
responsive defects + both polish items fixed (~98%, frontend acceptance gates
passing); the two remaining LOW cosmetic items (privacy pill clip + signatures
glyph) were fixed and screenshot-verified in this build. Awaiting your deploy +
confirmation.
