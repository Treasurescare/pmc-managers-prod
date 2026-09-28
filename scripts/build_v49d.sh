#!/usr/bin/env bash
# PMC v49d — Login form + Register route made functional. Rebuild.
set -eu

VER="v49d"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"

echo ">>> Building frontend ($VER) with same-origin backend URL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build

echo ">>> Zipping frontend build (excluding downloads/)"
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
echo "     -> $DL/pmc-frontend-${VER}-prod-build.zip"

echo ">>> Zipping backend (includes Dockerfile, Dockerrun.aws.json, .platform at zip root)"
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' \
    -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' \
    -x 'backend/**/*.pyc' \
    -x 'backend/.env' \
    -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' \
    -x 'backend/tests/*' \
    -x 'backend/keys/*'
echo "     -> $DL/pmc-backend-${VER}.zip"

echo ">>> Writing release notes"
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
# PMC Managers Limited — Release v49d

## Fix in this release
* **Unified `/login` (Option E) sign-in is now functional.**
  The Option E `SignInE.jsx` shipped as a pure static template — no state, no
  onSubmit, and the password field held a hardcoded value. Users could not
  actually sign in from `/login`; portal-specific routes (`/vendor/login`,
  `/admin/login`, `/staff/login`) worked because they use the legacy forms.
  `SignInE.jsx` has been rewritten as a real form:
  - Working role selector (Supplier / PMC staff / Administrator).
  - Real `useState` inputs, no hardcoded placeholder value.
  - Real API calls: `vendorApi.login`, `staffApi.login` (with role fallback),
    `adminApi.login` (final fallback for admin card).
  - Redirects to `/vendor/change-password` if the vendor's account has
    `must_change_password=true`.
  - Existing visual chrome preserved (forest-green rail, brass CTA).
* **`/register` now serves the working `RegistrationStart` flow directly.**
  Previously `RegistrationE` — a static "Step 4 of 5 KYC" mockup — was the
  route target; new suppliers hit a decorative page with no data collection.
  The route now points to the real `RegistrationStart` component (PDF
  download, resume link, real submission).

## Everything from v49c still applies
* Option E is the sole UI (55 pages, 52 branded email templates, live-data
  wiring, `PmcLinkPatcher` SPA navigation, admin email preview endpoints).

## Bundles
* Frontend: `pmc-frontend-v49d-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront)
* Backend:  `pmc-backend-v49d.zip` (unchanged from v49c; identical contents
  so you can reuse the v49c EB deployment if it's already live).

## Deploy
* **Frontend** — unzip into your S3 bucket, invalidate CloudFront `/*`.
* **CloudFront SPA rule (must be set once)** — Custom error responses:
  both `403` and `404` → `/index.html` with HTTP `200`.
* **Backend** — no code changes vs v49c. Redeploy only if you skipped v49c.

## Rollback
* Roll back to `v49c` or `v48c` if needed.
EOF
echo "     -> $DL/DOWNLOAD_${VER}.md"

echo ">>> Sizes"
ls -lh "$DL"/pmc-*"${VER}"*.zip "$DL/DOWNLOAD_${VER}.md"

echo ">>> Done."
