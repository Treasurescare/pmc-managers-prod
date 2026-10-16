# PMC Managers — Release v53j (frontend + backend)

## What changed since v53i

Four follow-up enhancements shipped in one bundle. Preview-verified; prod
needs the standard EB + S3/CloudFront deploy.

### 1. Resend invite (admin, one click)
`POST /api/v1/reverse-auctions/{aid}/invite/{token}/resend`

Admin → Reverse auctions → row → **Pending invite links** now shows a
**Resend** button next to **Copy** on every row that has not yet joined
or declined. Reuses the stored token (same join URL stays valid), the
default template, and sends a "Reminder — …" prefixed email via Resend.
`resent_at`, `resent_by`, `resent_count` are persisted so you can see how
many nudges a given invitee has had. Audit event
`reverse_auction.invite_resend`.

### 2. Decline-with-reason (vendor soft-no)
`POST /api/v1/reverse-auctions/invite/decline/{token}`

In the vendor auction room, an invited vendor who has not yet registered
can click **Decline with reason**, enter a short free-text reason, and
submit. The invitation moves to `status: "declined"` with
`decline_reason` + `declined_at`, and the admin console shows:
- a red `declined` badge next to that invitee row;
- a "Decline reasons" summary block under the invite list.

An admin notification is fired on decline so the reason surfaces in
real time rather than sitting on a report.

### 3. Awarded auctions panel (admin)
New sidebar entry **Awarded auctions** → `/admin/e/awarded-auctions`.

`GET /api/v1/reverse-auctions/awarded/list` returns every awarded reverse
auction with:
- auction title + notice ref + derived bid ref;
- winner company and email;
- starting price → final price;
- **saving %** (highlighted in emerald when ≥ 10 %);
- current pipeline stage of the derived bid (EMD paid → escrow →
  certifier → legal → accounting → final award);
- awarded-on date.

### 4. Weekly opportunity digest (cron)
`.emergent/crons.yml` now has a second entry running
**every Monday 09:00 UTC**:

```yaml
- name: vendor-opportunity-digest
  cron: "0 9 * * 1"
  endpoint: "{{BASE_URL}}/api/v1/cron/vendor-opportunity-digest"
  method: POST
  enabled: true
```

`POST /api/v1/cron/vendor-opportunity-digest`
- bearer-auth against `WEBHOOK_CRON_SECRET`;
- idempotent via `cron_runs` (`run_id` keyed by `X-Webhook-Id`);
- enqueues `_do_digest` as `asyncio.create_task` so the HTTP ACK is
  immediate (≤ 5 s dispatcher budget);
- for every invitation row with status NOT in {`accepted`, `declined`}
  whose auction is still `draft` or `live`, groups by vendor email and
  sends one email per vendor listing all still-open opportunities with
  deep links to each `/vendor/auction/invite/{token}`.

Preview smoke:
- cron endpoint 200 with correct bearer, 401 without.
- Awarded list / resend / decline endpoints return 401 unauthenticated
  as expected (admin / vendor gates intact).

## Deploy

1. **Backend** — `pmc-backend-v53j.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53j-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. The new cron entry is synced automatically from the deployed app's
   `.emergent/crons.yml`. No manual cron registration needed.

## Files touched

- Backend
  - `routers/auction_live.py` — resend/decline/awarded endpoints; invite
    token exposed on `state-mine` so vendor room can wire Decline UI.
  - `routers/cron_vendor_digest.py` — new weekly digest cron handler.
  - `server.py` — register the new cron router.
- Frontend
  - `lib/api.js` — three new reverseAuctionApi methods.
  - `apps/admin-console-e/AdminAuctionsE.jsx` — Resend button + declined
    badge + reasons summary.
  - `apps/admin-console-e/AdminAwardedAuctionsE.jsx` — new panel.
  - `apps/admin-console-e/AdminSideNavE.jsx` — new sidebar entry.
  - `App.js` — new route.
  - `apps/vendor-portal/AuctionRoom.jsx` — Decline-with-reason modal.
- Config
  - `.emergent/crons.yml` — second cron entry for the weekly digest.
