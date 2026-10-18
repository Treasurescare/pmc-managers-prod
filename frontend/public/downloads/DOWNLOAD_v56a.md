# PMC Managers — Release v56a (18 Jun 2026)

Fixes stacked on top of the already-deployed **v56**. After deploying, the
site footer reads **Frontend v56a · Backend v56a** so you can confirm it's live.

## What changed since v56
1. **Escrow CSRF 403 fix** — saving a joint account ("Save institution & both
   signers") and **Backfill** no longer fail with "CSRF token missing or
   invalid". New `GET /api/v1/staff/auth/csrf` re-issues the csrf cookie for the
   live session; the app auto-refreshes and retries once on any CSRF 403.
   ⚠️ Needs BOTH zips deployed — the frontend retry calls the new backend endpoint.
2. **Backfill 404 fix** — `POST /api/v1/escrow/accounts/{id}/backfill-signers`
   is now implemented (it was missing). Matches the institution to an approved
   master, refreshes the PMC officer, swaps the escrow officer to a real
   signatory; unmatched institution returns a helpful "rebind" message.
3. **Footer shows live version** (was hard-coded / blank).
4. **Country scope = country-name dropdown** (flags + chips, search; blank =
   all) on staff and escrow-institution scope — no more ISO typing.
5. **Company Master** — City autocompletes from the cities master
   (country→state→city); ZIP validates against the country's postal format;
   the document-upload panel appears right after Create.

## Artifacts
- Backend: `pmc-backend-v56a.zip` (no .env / keys / tests)
- Frontend: `pmc-frontend-v56a-prod-build.zip`

## Deploy (one combined upload)
1. Backend zip → Elastic Beanstalk, wait green.
2. Frontend build contents → S3 root (overwrite).
3. CloudFront invalidation `/*`.
4. Footer should read **Frontend v56a · Backend v56a**; re-test escrow Save + Backfill.
