# PMC Managers — Frontend Production Build v51ar

**Release:** v51ar
**Build date:** 2026-10-07
**Bundle:** `pmc-frontend-v51ar-prod-build.zip`
**Contents:** React static build (`index.html` + `static/` assets), `downloads/` folder excluded.

## What's new in v51ar (on top of v51aq)

- **Escrow registration link on the login page**: the sign-in screen's
  subtitle and bottom registration button are now context-aware — selecting
  the "Escrow Institution" role shows "Register as an escrow institution —
  bank / trustee onboarding" linking to `/escrow/register` (previously the
  button was hardcoded to supplier registration, so banks had no visible
  self-registration path).
- Escrow Institution card subtitle updated: "Banks & trustees ·
  dual-signature sign-off".

Everything else is identical to v51aq (escrow duplicate guard, cancel row,
CSV export, ledger search, signatory auth, expiry watchdog, KPI tile,
audit trail, bulk notice routing, orphan-bid hardening).

## Deploy

Backend: reuse `pmc-backend-v51aq.zip` — no backend changes in v51ar.
Frontend: unzip `pmc-frontend-v51ar-prod-build.zip` into your S3 static
bucket (overwrite v51aq). CloudFront invalidation for `/*` recommended.
