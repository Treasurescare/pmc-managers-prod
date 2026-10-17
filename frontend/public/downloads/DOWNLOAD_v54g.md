# PMC Managers v54g — Prod URL fix + visible build stamp

Release target: 17 Feb 2026

**Contains everything from v54a → v54f, plus the two items below. Deploy
this pair and skip earlier bundles.**

## The thing we've been chasing all day

Your backend `.env` was shipping with:

```
FRONTEND_URL="https://pmc-forest-green.preview.emergentagent.com"
```

That's the Emergent preview environment — not `pmcmanagers.com`. Every
Resume-registration email built its link against that URL, so clicking
the emailed link took you to a **different environment** where your
production draft, documents and account did not exist. Hence:

- "upload works but I can't view/download" — you uploaded in production,
  then opened preview, where the file never existed.
- "email field empty" — preview has no draft under your email.
- "same in another browser" — the broken link is in the email, nothing to
  do with cookies / cache.

**Fix**: `.env` default is now `https://pmcmanagers.com`. If your EB
environment variables already override this (recommended), nothing
changes. If not, future emails will finally point to production.

## Visible build stamp (no more guessing)

Every page footer now reads:

```
Frontend v54g · 2026-02-17 · Backend v54g
```

And `GET /api/v1/_version` returns `{"version": "v54g", ...}` publicly —
no auth required. We can now **confirm from any browser** which bundles
are live before testing anything, instead of inferring from UI symptoms.

### Deployment smoke-test (90 seconds)

1. Open `https://pmcmanagers.com/api/v1/_version` → should return
   `{"version": "v54g", "component": "backend"}`. If it returns 404 or
   an older version, the backend bundle hasn't landed yet.
2. Open `https://pmcmanagers.com/` → scroll to the footer → confirm it
   reads **Frontend v54g · Backend v54g**. If the frontend says anything
   else, CloudFront is still serving stale JS — re-invalidate `/*`.
3. **Only then** retry the resume-registration flow.

## Everything from earlier bundles still included

v54a (escrow EMD pack) · v54b (registration unblocked) · v54c (signature
whitelist + upload persistence) · v54d (searchable country picker) ·
v54e (country-format regex, phone ISD, bank autofill, UNSPSC click fix,
numeric turnover) · v54f (resume-link `token=undefined` fix + legacy
magic-token mint).

## Artifacts

* Backend: `pmc-backend-v54g.zip`
* Frontend: `pmc-frontend-v54g-prod-build.zip`
