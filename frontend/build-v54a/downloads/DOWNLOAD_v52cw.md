# PMC Managers · v52cw Frontend Hotfix

**Date:** 13 Feb 2026
**Backend:** unchanged from v52cu — no EB redeploy needed.
**Frontend only:** `pmc-frontend-v52cw-prod-build.zip` (3.1 MB)
**Supersedes:** v52cv (do not deploy v52cv; v52cw contains everything it has).

## What changed

Everything in v52cv, plus:

4. **Download pack no longer 401s.** The v52cv fix pointed the button at the real URL, but a plain browser navigation drops the auth session (httpOnly cookie / SameSite partitioning), so protected files answered `{"detail":"Sign in to download tender documents"}`. The button now fetches the file through the authenticated axios client (same pattern as every other working download in the app) and saves the blob with the server-provided filename. Clear toasts for expired session (401), unlinked template (404), and "no documents published".

## Deploy (frontend only, ~5 min)

1. Download https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cw-prod-build.zip
2. Unzip into the S3 origin bucket (replace `index.html`, `static/*`, etc.).
3. CloudFront → distribution → **Create invalidation** → path `/*`.
4. Hard-refresh and verify:
   - Tender Builder page: avatar (top right) opens menu with Change photo / Change password / **Sign out**.
   - Home page cards show **Indicative budget · EMD · Delivery · Category**.
   - Any published notice page → **Download pack** downloads a .zip (or the primary PDF) with no JSON error page.

## Verified on preview before shipping

- Signed in as admin, opened `/notices/PMC-NOT-2026-0020`, clicked Download pack → browser download fired with the correct filename.
- Public ZIP endpoint returns HTTP 200 with a valid archive (composed PDF + annexures + README).
- Home page cards render EMD ("No EMD" for zero-EMD tenders) in the correct position.

## Backend bundle

Unchanged — `pmc-backend-v52cu.zip` remains current. Only upload it if you haven't deployed v52cu yet.
