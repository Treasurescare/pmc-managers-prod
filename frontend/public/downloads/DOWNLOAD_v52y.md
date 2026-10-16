# PMC Managers — Release v52y (frontend + backend)

## What changed since v52w

### 1. Submission-close cron REMOVED
The daily `submission-close-sweep` cron shipped in v52x has been fully
removed per request (no Emergent-platform dependencies for now). Deleted:
`routers/cron_submission_close.py`, the server.py import + mount, and the
entry in `.emergent/crons.yml`. The escrow-expiry cron is untouched.

**Verified:** `POST /api/v1/cron/submission-close-sweep` → 404.
`POST /api/v1/cron/escrow-expiry-watchdog` → still 401 (still there).

An AWS-side scheduler (EventBridge or similar) can be wired to this
endpoint later when you're ready — the handler code is gone, you'll want it
re-added in a new form if you re-adopt it.

### 2. Corrigenda ↔ Tender Maker date parity (closes a tender-restart gap)
Previously the Corrigenda form only exposed 3 dates (Submission deadline,
Pre-bid meeting, Clarifications close). A closed tender's full timeline
couldn't be restarted. v52y adds the **7 missing Tender Maker Critical
Dates** as amendable fields, with the same date-chain validation as the
Tender Builder — so a corrigendum can genuinely re-open and restart the
entire tender cycle.

**New amendable date fields (backend + frontend):**
- Publish Date
- Document Download / Sale Start
- Document Download / Sale End
- Clarification Start Date
- Bid Submission Start Date
- Bid Opening Date
- Bid Award Date

Plus the 3 pre-existing ones kept with Tender-Maker labels:
- Bid Submission End Date (was "Submission deadline" → `submission_deadline`)
- Clarification End Date (was "Clarifications close" → `clarification_deadline`)
- Pre-Bid Meeting Date (→ `pre_bid_meeting_date`)

**Validation (both sides) — mirrors `lib/dateRules.js` ↔ `routers/date_rules.py`:**
Pre-bid ≥ Publish · Doc-DL Start ≥ Pre-bid · Doc-DL End ≥ Doc-DL Start ·
Clarif Start ≥ Doc-DL End · Clarif End > Clarif Start · Sub Start ≥
Clarif End · Sub End ≥ Sub Start · Bid Award ≥ Sub End · Bid Opening ≥
Sub End. The corrigendum path skips the "cannot be in the past" check for
`publish_date` / `sub_end` because it edits a LIVE notice; only ordering
is enforced. The "new deadline cannot be in the past" guard still runs.

**Field-amendments table on the Corrigenda form now covers every notice
field in a sensible order:** text/money block first, then Critical Dates
block (matches Tender Maker order).

**Verified E2E in preview (curl):**
- out-of-order (doc_dl_start > doc_dl_end) → **400**
  "Document Download / Sale End must be on or after Document Download / Sale Start"
- in-order full timeline (10 dates) → **200**, corrigendum #2 published,
  10 amendments applied, every date on the notice updated to the new
  values, `amendment_base` captured 10 original values for rollback.

## Deploy

1. **Backend** — upload `pmc-backend-v52y.zip` to Elastic Beanstalk.
2. **Frontend** — unzip `pmc-frontend-v52y-prod-build.zip` to S3 bucket
   root; CloudFront invalidate `/*`.
3. Open any published notice → Corrigenda → New: all 10 date rows appear
   with chain validation live (toast fires on bad ordering).
