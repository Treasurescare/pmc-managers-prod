# PMC Managers — v58b (30 Oct 2026)

- Backend  → `pmc-backend-v58b.zip` → Elastic Beanstalk
- Frontend → `pmc-frontend-v58b-prod-build.zip` → S3 root (delete old index.html + static/ first) → CloudFront invalidation `/*`
- Footer must read "Frontend v58b · Backend v58b"

## New since v58a
- Homepage "Get tender alerts" box (double opt-in: visitor confirms by email before any alert is sent).
- New-tender alerts: choose "one email per tender" or "weekly digest"; "Send this week's digest now" button.

## AWS: weekly digest schedule
EventBridge Scheduler → cron(0 8 ? * MON *) Europe/London → POST https://www.pmcmanagers.com/api/v1/cron/marketing-weekly-digest
Header: Authorization: Bearer <value of /pmc/prod/WEBHOOK_CRON_SECRET>
