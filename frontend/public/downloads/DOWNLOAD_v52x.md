# PMC Managers — Release v52x (backend only)

## What changed since v52w

### Daily "submissions closed" sweep — closes the notification gap
Previously, when a tender's submission deadline passed, **nobody was
notified** — the portal simply started blocking new bids and an admin had to
notice on their own. v52x adds a daily cron that closes the loop.

**New endpoint:** `POST /api/v1/cron/submission-close-sweep`
(`routers/cron_submission_close.py`), same contract as the escrow watchdog:
bearer-authenticated (`WEBHOOK_CRON_SECRET`), acks 2xx immediately and does
the real work in a background task, idempotent per run (`cron_runs`) AND per
tender (`submission_close_notified_at` flag on the notice).

**Sweep logic:** notices whose `submission_deadline` fell in the last 24h
and haven't been swept yet.

**Who gets notified per closed tender:**
| Audience | What they receive |
|---|---|
| Admin role | Per-tender summary: bid count, EMD paid/pending counts, tech-cleared count, per-bid table, next-step checklist (Bidding Ops → EMD → technical → legal/accounting → L1/Rubric → award). In-app + email. |
| Committee members | Same summary + link to the Evaluation panel. In-app + email. |
| Each bidder | "Submissions closed" email showing their **current pipeline stage** and the full chain: 1. EMD verification → 2. Technical evaluation → 3. Legal & accounting → 4. Committee decision → 5. Award & contract. Bids with unpaid EMD get an explicit action-needed warning. |
| Escrow agents | **One** summary email per day (not per tender) listing every bid whose EMD is still pending across all just-closed tenders. |

**Schedule (.emergent/crons.yml):** daily 09:00 Europe/London, same slot as
the escrow-expiry watchdog.

**Verified in preview (curl):** seeded test tender with 2 bids (1 EMD paid,
1 pending) → run 1: `tenders:1, vendor_emails:2`, 3 admin + 6 committee
in-app notifications, 1 escrow summary email, notice flagged. Run 2 (new
run id): `tenders:0` — per-notice flag prevents re-notification. Same run
id: `{duplicate: true}`. Test data cleaned up.

## Deploy

1. **Backend** — upload `pmc-backend-v52x.zip` to Elastic Beanstalk
   (Dockerfile at root; `.env` and `docker-compose.yml` excluded).
2. **Frontend** — no changes; `pmc-frontend-v52x-prod-build.zip` is
   identical to v52w (rebuild not needed unless you want matching labels).
3. **Production scheduling — important:** `.emergent/crons.yml` is executed
   by the Emergent platform scheduler, which only covers the Emergent
   deployment. On your AWS EB production you need an external scheduler
   (AWS EventBridge, or a service like cron-job.org) that POSTs daily at
   09:00 Europe/London to:
   `https://<your-prod-host>/api/v1/cron/submission-close-sweep`
   with header `Authorization: Bearer <WEBHOOK_CRON_SECRET>`
   (the same secret the escrow watchdog already uses — if that one fires in
   prod today, reuse the identical mechanism).
