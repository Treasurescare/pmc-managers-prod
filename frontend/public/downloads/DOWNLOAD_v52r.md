# PMC Managers — Release v52r (frontend-only)

## What changed since v52p
- **Corrigenda form dedupe:** the duplicated top-level **Title** and
  **Overall change description** inputs are removed from the New
  Corrigendum form. The Title / Description now live only in the
  field-amendment table.
- On publish, the corrigendum headline is auto-derived as
  `Corrigendum N — <notice title>` and the summary is built from the
  per-field reasons you enter (deadline-only corrigenda get a default
  sentence). Backend validation stays intact; no backend change required.
- Everything else from v52p ships unchanged (bid lockout, category chip
  picker, admin resync, hover fixes, corrigendum→notice sync).

## Deploy

Backend: **no change** — the v52p backend bundle already running in
production is fine. If you're redeploying anyway, use
`pmc-backend-v52p.zip`.

Frontend:
1. Unzip `pmc-frontend-v52r-prod-build.zip`.
2. Upload the extracted contents to your S3 bucket root (overwrite).
3. CloudFront → create invalidation `/*`.
4. Hard-reload the Corrigenda page to confirm the new slim form (just
   Corrigendum date + optional new deadline + field table).
