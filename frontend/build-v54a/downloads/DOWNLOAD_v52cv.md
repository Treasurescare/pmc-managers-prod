# PMC Managers · v52cv Frontend Hotfix

**Date:** 13 Feb 2026
**Backend:** unchanged from v52cu — no EB redeploy needed.
**Frontend only:** `pmc-frontend-v52cv-prod-build.zip` (3.1 MB)

## What changed

1. **Tender Builder page — working avatar & sign-out.** The page header was rendering a static placeholder letter instead of the real menu. Now mounts `AdminAvatarMenu` (profile photo, change password, sign out) like every other admin page.
2. **EMD now visible on every tender list.** Home page cards and the Tenders list rows each gained an EMD cell, fed from the flat `emd_amount` / `emd_percentage` the public API emits. Zero-EMD tenders show "No EMD" instead of a blank.
3. **Download pack works.** On a notice detail page the button now downloads the real bundle: the composed Tender Builder ZIP (PDF + all annexures + README) when the notice is template-linked, otherwise the primary uploaded document. Notices with no documents show a clear toast instead of a dead click.

## Deploy (frontend only, ~5 min)

1. Download https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cv-prod-build.zip
2. Unzip into the S3 origin bucket (replace `index.html`, `static/*`, etc.).
3. CloudFront → distribution → **Create invalidation** → path `/*`.
4. Hard-refresh and verify:
   - Tender Builder page: avatar (top right) opens a menu with Change photo / Change password / **Sign out**; sign out returns to /login.
   - Home page "Open for bids this week" cards show **Indicative budget · EMD · Delivery · Category**.
   - Any published notice page → **Download pack** downloads a .zip (or the primary PDF when no template is linked).

## Notes

- Backend bundle from v52cu is still current — only re-upload `pmc-backend-v52cu.zip` if you haven't deployed it yet.
- Preview test residue (3 auto-created "v52ct work title" notices) was cleaned from the preview DB; the regression test now cleans up after itself.
