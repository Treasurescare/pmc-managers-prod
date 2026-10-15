# PMC Managers — Release v52f

**Date:** 15 Feb 2026
**Scope (on top of v52e):** Dashboard charts (institution + admin cross-filter) · Post-approval signatory invites · Downloadable + emailable PDF statements per joint account.

Deploy this bundle to replace v52e (which replaced v52cz rev9).

## What's new in v52f

### 1. Dashboard transaction chart
- **Institution view** on `/escrow/me` → Overview tab: 12-month line chart (volume per currency) + currency breakdown pie, with a filter to view **All joint accounts** or a specific one.
- **Admin view** on `/admin/e/escrow-institutions`: same chart with a **multi-select institution filter** at the top (click to toggle any approved institution; empty = all). Lets you compare one bank against the whole book.
- Backend: `GET /api/v1/escrow-accounts/me/chart?account_id=all|<id>&months=12` and `GET /api/v1/escrow/admin/chart?institution_ids=<ids>`. Clamps months to 3–24. Empty-state copy on dashboards when no transactions exist yet.
- Chart lib: recharts 3.6 (already in `package.json`).

### 2. Signatory invites — unlocked after approval
- Primary contact invites a teammate from the dashboard's **Profile** tab. Form is **disabled with status copy while institution is draft/submitted/under_review**, enabled once PMC approves.
- Submit → `POST /api/v1/escrow-accounts/me/signatories/invite` → appends to the institution's `signatories[]`, mints/reuses a `magic_token`, fires the standard password-claim email so the new signatory can set their password and start co-signing EMD releases.
- Duplicates on the same email are rejected 409.

### 3. PDF statements per joint account
- **Download statement** and **Download + email me** buttons on every joint-account card.
- Backend: `GET /api/v1/escrow-accounts/me/joint-accounts/{aid}/statement.pdf?email_me=1`. Rejects foreign accounts (403). PDF rendered with reportlab 5.0: PMC branding, account coordinates, transaction table (date / bid / vendor / amount / currency / status / PMC+Us signatures), totals, hash-chain footer.
- `email_me=1` also sends the PDF as an attachment to the primary contact (Resend/relay via existing `send_email` helper).

## Tests
- `backend/tests/test_v52f.py` — 8 tests (chart shape + clamping, invite blocked pre-approval, invite + duplicate 409 post-approval, statement foreign-rejection + PDF content signature, admin chart with and without institution filter).
- Cumulative suite: `test_v52cz_rev9` + `test_v52d_escrow_accounts` + `test_v52e` + `test_v52f` — all green.

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52f.zip`](./pmc-backend-v52f.zip) | Elastic Beanstalk backend package (Dockerfile at ZIP root, no docker-compose.yml, `.ebextensions/`, `.dockerignore` included) |
| [`pmc-frontend-v52f-prod-build.zip`](./pmc-frontend-v52f-prod-build.zip) | S3 / CloudFront static assets |

## Deployment
Standard EB redeploy + S3 sync + CloudFront `/*` invalidation. No DB migrations required — all new behaviour reads existing collections. Rollback: redeploy any earlier v52cz/d/e bundle.

## Browser smoke
1. Signed-in dashboard → Overview tab → chart renders (empty-state copy if no joint accounts).
2. Joint accounts tab (post-approval) → each card has **Download statement** + **Download + email me**.
3. Profile tab (post-approval) → invite teammate form unlocks and sends claim email.
4. Admin → Escrow institutions → chart with institution picker up top.
