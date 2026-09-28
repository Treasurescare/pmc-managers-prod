# PMC Managers Limited — Release v49o

## What's new in v49o

### 1 · Public notice-detail gates now land on the LOGIN page
Guest clicks on **Download**, **Follow** and **Ask a question** previously
went to `/register`. They now go to `/login` — the unified sign-in page
carries a *"New supplier? Register in about 15 minutes"* link, so both new
and existing vendors are served from one screen.

### 2 · Notice-detail tabs actually switch sections
Overview / Eligibility / Documents / Clarifications / Corrigenda were
cosmetic-only. Clicking a tab now shows the matching section
(Overview→Scope, Eligibility→Who can bid, Documents→Documents, etc.) and
hides the rest, with a smooth scroll back to the tab row. On load, only
the Overview section is visible. If a tab has no matching section (e.g.
Corrigenda on notices whose corrigenda only live in the Key-dates
timeline), the page keeps the Overview visible and shows a small
dashed-border note instead of a blank screen.

### 3 · Start bid regression fixed (found in verification)
`extractNoticeRef` only looked at descendants of the clicked element, so
the plain `<a href="/notices/…">Start bid</a>` anchors produced a null ref
and fell through to a no-op. Now walks up to the nearest card/row and, as
a last resort, parses the ref from the anchor's own href. Verified:
`/vendor/tenders` → Start bid → `/vendor/bid/new/<ref>` with the real bid
form (`bid-form` / `bid-price` / `bid-submit-btn` testids present).

### 4 · Bid-submit page heading contrast
"Submit a bid" + notice ref were dark-on-dark under the Option E theme
overrides; now explicitly `text-slate-900` / `text-slate-600`.

### 5 · Vendor Account page React warnings silenced
Static `checked` checkboxes switched to `defaultChecked` (11×).

## Verified (testing agent, iteration 37)
- Guest Download / Follow / Ask a question → `/login` ✓
- Tab switching: Eligibility / Documents / Clarifications / Overview ✓
- Pay EMD → Stripe checkout ✓
- Signatures empty state + hidden mockup card ✓
- Change-password modal ✓ · Identity pill menu + Sign out ✓
- Start bid → bid form (after tester fix, confirmed in-browser) ✓

## Bundles
- **Frontend:** `pmc-frontend-v49o-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49o.zip` (419 KB — no backend change vs v49n)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.
- Backend: skip if v49n is already deployed.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49n` if needed.
