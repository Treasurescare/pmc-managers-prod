#!/usr/bin/env bash
# PMC v51i — DocuSign console regression fix + mobile global guards
#
# DocuSign fixes:
#   - frontend/src/lib/api.js: added reassignEnvelope / archiveEnvelope /
#     unarchiveEnvelope (missing in v51b -> silent dead buttons).
#   - frontend/src/lib/api.js: showApiError now imports sonner at module
#     scope so error toasts actually render (require("sonner") hit the CJS
#     store that was never mounted -> every API error was silent app-wide).
#   - backend/routers/docusign.py: resend embedded branch now passes
#     client_user_id + return_url to _recipient_view (was 4/6 args -> 502).
#   - backend/routers/docusign.py: archive-pdf switched to current_admin
#     Bearer auth (was require_role -> cookie CSRF 403 inside the iframe).
#   - backend/routers/docusign.py: admin combined-pdf now serves the PMC
#     storage copy first when archived_file_key is present.
#   - backend/routers/docusign.py: upstream DocuSign failures now return
#     HTTP 424 with an explicit JSON reason so the gateway stops rewriting
#     the body into a generic 502 HTML page.
#   - DocuSignPanel.jsx: duplicate "Archive" removed - amber button is
#     "Save PDF" (mirror signed PDF into PMC storage); slate "Archive" is
#     hide-from-vendors. Archived rows render as light warm-grey with a
#     dark ARCHIVED chip and ⟲ Restore button.
#   - DocuSignPanel.jsx / VendorSignaturesE.jsx: blob download handlers
#     now unwrap JSON error bodies so toasts show the real reason.
#
# Mobile guards (frontend/src/mobile-fix.css, ≤767px):
#   - inputs / selects / textareas can never extend past the viewport
#     (vendor login, landing, hero, any form).
#   - mobile topbar frozen (position:fixed) with body padding-top:60px.
#   - bottom tab-bar clearance (104px) applied to every page root, not
#     just vendor dashboards -> last buttons no longer hidden.
#   - tender listing + .pmc-wrap grids get 12px side padding on mobile
#     (two older rules were forcing zero horizontal padding).
set -eu
VER="v51i"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -3
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' -x 'backend/**/*.pyc' \
    -x 'backend/.env' -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' -x 'backend/tests/*' -x 'backend/keys/*' 2>/dev/null || true
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers — Release v51i (cumulative v50m → v51i)

## Fixes in this build (over v51b)

### DocuSign admin console — the five "dead button" bugs
- **Reassign & save** now works end-to-end (the API client was missing
  reassignEnvelope / archiveEnvelope / unarchiveEnvelope in v51b, so every
  click threw a silent TypeError in the browser).
- **Error toasts render again app-wide** — showApiError had been using
  require("sonner") which loaded a second CJS copy of the toast store that
  was never mounted; every API failure was silent. Fixed with an ESM
  top-level import.
- **Resend** no longer 502s on embedded envelopes — the backend was calling
  _recipient_view with 4 of 6 required args. Fixed, with a one-off repair
  pass that stamps client_user_id onto older envelopes.
- **Duplicate "Archive"** removed — the amber button is now "Save PDF"
  (mirror signed PDF into PMC storage); the slate "Archive" hides the
  envelope from vendor Signatures pages. Archived rows show as a light
  warm-grey band with a dark ARCHIVED chip and a ⟲ Restore button.
- **Save PDF 403 "CSRF token missing or invalid"** fixed — archive-pdf is
  now Bearer-auth like the rest of the router (cookie CSRF was blocked
  inside the preview iframe / SameSite=Lax contexts).
- **Print / Download fragility** — admin combined-pdf now serves the
  PMC-storage copy first when one exists, so once you have "Save PDF"'d
  an envelope its signed PDF stays downloadable even if DocuSign is
  unreachable.

### Upstream error visibility
- All DocuSign upstream failures now return HTTP 424 with an explicit
  JSON reason. (The AWS gateway rewrites every 5xx response body into a
  generic HTML error page, which is why on-screen toasts previously only
  showed a bare "Request failed with status code 502".)
- Blob download handlers unwrap JSON error bodies so toasts show the
  real server message, not "Something went wrong".

### Mobile global guards (every page, ≤767px)
- Login, landing and hero inputs can never extend past the viewport.
- Mobile hamburger header is **frozen** (position:fixed) with body
  padding so content doesn't slide underneath.
- Fixed bottom tab-bar clearance applied to every page (not just vendor
  dashboards) — the last buttons are no longer hidden behind the menu.
- Tender listing + content wraps get 12px side padding so cards don't
  sit flush with the screen edge.

## Deploy
- Backend: `pmc-backend-v51i.zip` → Elastic Beanstalk
  (contains the resend, archive-pdf, combined-pdf and 424 error fixes).
- Frontend: `pmc-frontend-v51i-prod-build.zip` → S3, then CloudFront
  invalidate `/*` (contains the API-client, toast, DocuSign UI and mobile
  CSS fixes).

## Preview-only note
The preview pod's DocuSign sandbox key is expired (`invalid_grant /
issuer_not_found`), so live-DocuSign actions can only fully succeed on
production. On production the fixes themselves are environment-independent.
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
