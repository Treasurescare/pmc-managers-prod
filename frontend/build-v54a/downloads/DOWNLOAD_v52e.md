# PMC Managers — Release v52e

**Date:** 15 Feb 2026
**Scope (cumulative since v52cz rev9):**
- **v52d — Account-first escrow registration** (gate screen · verify link · persistent login · session-authed 5-step wizard · shared dashboard header with bell + avatar menu · in-app + email notifications)
- **v52e — Full-flow completion** (admin "Account" column + Notify-owner · real pending-signatures / transactions wiring · suggested-banks admin curation screen)

Deploy this bundle to replace v52cz rev9.

---

## What's new in v52e (on top of v52d)

### 1. Admin pipeline — Account column + Notify owner
- `/admin/e/escrow-institutions` list rows now display `owner · <email> (<status>)` under the primary contact line so reviewers see which escrow account owns each registration.
- The institution detail panel has a new **Notify owner** button (next to Approve / Clarify / Reject). Opens a title + body prompt and pushes a notification to the owner's bell + email in one shot.
- Backend: `GET /api/v1/escrow-institutions` hydrates `owner_account`; new `POST /api/v1/escrow-institutions/{iid}/notify-owner` writes an in-app notification (kind=`admin_message`) and emails via `notify_account()`. Returns 400 for legacy magic-link drafts without an owner account.

### 2. Dashboard data wiring — real pending signatures + transactions
- `GET /api/v1/escrow-accounts/me/dashboard` resolves the signed-in account → institution → signatory emails → joint escrow accounts → every transaction on those accounts. Returns separate buckets `pending_signatures`, `transactions`, `joint_accounts` with balances.
- Signed-in `/escrow/me` dashboard body (post-approval) now shows real KPI counts, a transactions table, and joint-account cards. Sidebar tabs display live badges when counts > 0. Empty states are status-aware (submitted → "with review team"; approved + 0 accounts → "waiting for PMC to open the first joint account").

### 3. Suggested banks curation — admin screen
- New admin page at `/admin/e/suggested-banks` (new sidebar entry under Masters) reviews banks that registrants add via the "+ Add bank" affordance.
- Approve → promote to `source=curated` with optional swift_prefix / currencies / aliases enrichment.
- Merge → fold into an existing same-country bank (adds suggestion name to target aliases, deletes source, audited in `masters_banks_merge_log`). Cross-country merges rejected with 422.
- Reject → hard-delete the suggestion, audited.
- Endpoints: `GET/POST/DELETE /api/v1/masters/banks-admin/...` (admin-only).

## What's new in v52d (recap)

- `/escrow/register` is now a single-screen gate (email + legal name + phone + password). Verify link emailed; account persists on verification.
- `/escrow/login` tries `escrow_accounts` first (new primary-contact login), falls back to `escrow_signatories` for approved signatories.
- `/escrow/me` renders the 5-step wizard while institution status is `draft`/`needs_clarification`; dashboard body otherwise. All wizard writes are session-authed — no magic token in the URL.
- Legacy `POST /api/v1/escrow-institutions/register` returns **HTTP 410 Gone** pointing new users at `/escrow/register`. Admin-invited magic-link drafts still resume at `/escrow/resume/:token`.
- Dashboard header: bell left of avatar (unread badge + mark-all-read dropdown); avatar menu: **Change profile · Change password · Sign out → /escrow/login**.
- Toaster offset={{top:72, right:16}} so success toasts never cover the avatar/bell; single Toaster mount in App.js (duplicate in index.js removed).
- Status-change hook: approve / needs_clarification / reject / submit all push an in-app notification + email automatically.
- Owner-scoped read endpoint `GET /api/v1/escrow-institutions/{iid}/admin-view-public` so the wizard can preload the owned draft on sign-in.

## Tests
- `backend/tests/test_v52cz_rev9.py` — 5/5 (prior release regressions)
- `backend/tests/test_v52d_escrow_accounts.py` — 8/8 (account lifecycle)
- `backend/tests/test_v52e.py` — 6/6 (admin + dashboard + bank curation)
- **Total: 19/19 green**

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52e.zip`](./pmc-backend-v52e.zip) | Elastic Beanstalk backend package (Dockerfile at ZIP root, no docker-compose.yml) |
| [`pmc-frontend-v52e-prod-build.zip`](./pmc-frontend-v52e-prod-build.zip) | S3 / CloudFront static assets |

---

## Deployment

### Backend → AWS Elastic Beanstalk
1. Upload `pmc-backend-v52e.zip` as a new application version → **Deploy**.
2. On first boot the bank roster auto-upserts (146 banks, all countries including GB neobanks). Masters bootstrap also seeds country formats + banks + signatory indexes.
3. Smoke-test on the live URL:
   ```bash
   # New account-first endpoints
   curl -i https://www.pmcmanagers.com/api/v1/escrow-institutions/register \
     -X POST -H "Content-Type: application/json" -d '{}'
   # → HTTP 410 with {detail.error:"endpoint_deprecated"}

   curl -s https://www.pmcmanagers.com/api/v1/masters/banks?country_code=GB&q=Revolut
   # → [{"name":"Revolut",...}]
   ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront `/*` invalidation.

### Browser smoke test
1. `/escrow/register` → fill gate → "Check your inbox" screen.
2. Click emailed verify link → "Email verified" → **Sign in**.
3. `/escrow/me` → wizard renders with your details prefilled; save-as-draft at any step.
4. Submit → success state + bell shows **"Registration submitted for review"** notification.
5. Admin: `/admin/e/escrow-institutions` → see the new row with `owner · <email>`; click **Notify owner** → owner's bell + email receive your message.
6. Admin: `/admin/e/suggested-banks` → curate any banks registrants have added via "+ Add bank".
7. From the signed-in dashboard: avatar top-right → **Change profile / Change password / Sign out**.

### Rollback
Re-deploy `pmc-backend-v52cz-rev9.zip` + `pmc-frontend-v52cz-rev9-prod-build.zip`. All new collections (`escrow_accounts`, `escrow_notifications`, `masters_banks_merge_log`) and all new fields (`escrow_institutions.account_id`, `masters_banks.source`) are additive — rolling back the code does not touch stored data.

### Important compatibility note
`POST /api/v1/escrow-institutions/register` now returns 410. Any client (mobile app, API consumer) that still points at the legacy endpoint must be updated to `POST /api/v1/escrow-accounts/register`. Admin-invited magic-link drafts (via `/admin-invite`) still work unchanged.
