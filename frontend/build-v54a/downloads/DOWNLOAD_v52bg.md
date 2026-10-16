# PMC Managers — Release v52bg (10 Oct 2026)

Frontend-only modal UX fix on top of v52bf.

## Downloads
- Frontend: `/downloads/pmc-frontend-v52bg-prod-build.zip`
- Backend : unchanged — stay on v52bf (`/downloads/pmc-backend-v52bf.zip`
  is mirrored as `pmc-backend-v52bg.zip` for convenience).

## What changed
- `apps/admin-console/VendorIntelPanel.jsx`
    * Whitelist success now **closes the manage modal** and returns the
      admin to the triage list (previously the blacklist window stayed
      open and had to be dismissed manually). Same for the "Approve +
      whitelist" path in the appeal decision form.
    * Added a visible **✕ close button** in the modal header (top-right).
    * Restyled the bottom **Close** action from a faint underline link to
      a full-width bordered button so it can't be missed.

## Verification (preview)
- Opened Vendor Intel → Manage: header ✕ and the bordered bottom Close
  button both render and dismiss the modal.
- Whitelist + approve-and-whitelist flows close the modal automatically.

## Deploy
Frontend only: unzip into S3 (overwrite), CloudFront `/*` invalidation.
Backend stays on v52bf/v52bg (identical content).
