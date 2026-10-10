# PMC Managers — v51ay (Bidding Ops usability fixes)

**Build date:** 2026-10-10
**Frontend bundle:** `pmc-frontend-v51ay-prod-build.zip`
**Backend:** no changes — keep `pmc-backend-v51ax.zip`

## 🐞 Fixed (Bidding Ops)

- **"Waiting on Supplier" rows couldn't be opened**: supplier-side rows
  rendered only "Send link" as the sole action — there was no way to
  inspect the bid at all. Every supplier row now shows **Review**
  alongside Send link / Resend link.
- **Notice not viewable from the detail panel**: the clearance-path panel
  rendered the notice ref as plain text. It is now a link to the public
  notice page (`/notices/{ref}`) opening in a new tab.
- **"Unable to load the documents"**: the panel never listed the bid's
  envelope files at all. A new **Envelope documents** block lists every
  uploaded PDF (filename · kind · size) with a direct download link that
  opens in a new tab.
- **Duplicate panel re-opens**: after Hold/Resume/Reject the panel was
  force-refreshed twice (900ms + 1800ms), which made it feel like the app
  "opened in multiple places". Now a single 1.2s refresh.

## Deploy

Frontend only: unzip into S3 (overwrite v51ax), CloudFront `/*`
invalidation. Backend unchanged.
