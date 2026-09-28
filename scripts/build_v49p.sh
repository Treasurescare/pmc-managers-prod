#!/usr/bin/env bash
# PMC v49p — Site-wide mobile responsive fix + persistent PWA install entry.
set -eu

VER="v49p"
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

echo ">>> Zipping backend (Dockerfile + Dockerrun.aws.json + .platform at zip root)"
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
# PMC Managers Limited — Release v49p

## What's new in this release
### 1. Site-wide mobile responsive fix
The app now behaves like a native mobile experience on phones and tablets,
matching the two supplied mobile reference templates (`01-Mobile-Supplier.html`
and `02-Mobile-Public.html`):

* **No horizontal scrolling at any width down to 320 px**, on every public,
  vendor and admin page (`document.documentElement.scrollWidth <=
  window.innerWidth`).
* **Public pages** — compact sticky top bar with brand and a hamburger drawer
  containing every top-level nav item plus Sign in / Register CTAs.
* **Vendor portal** — fixed bottom tab bar (Home / Tenders / Bids / Alerts /
  Account) replaces the desktop sidebar on phones. Content gets extra bottom
  padding so it never sits under the tab bar. The active tab lights up.
* Grids that were `repeat(4,1fr)`, `repeat(6,1fr)`, `repeat(7,1fr)` collapse
  to single-column, tables become block-stacked cards, and every heading
  wraps cleanly.
* All the existing action wiring is untouched — Pay EMD still opens Stripe,
  Start Bid still opens the bid form, Review & sign still opens DocuSign,
  downloads still work, etc.
* Every new interactive element has `data-testid` (`pmc-mobile-topbar`,
  `pmc-mobile-menu-{open,close,scrim,drawer,link-*,signin,register,install}`,
  `pmc-mobile-tabbar`, `mnav-{home,tenders,bids,alerts,account}`).

### 2. PWA install: permanent access from the mobile menu
* New "Install app" button in the mobile hamburger drawer that ALWAYS
  triggers the install flow, even after the auto banner has been dismissed.
  * Android: replays the captured `beforeinstallprompt` event.
  * iOS Safari: shows the Share → Add to Home Screen instructions inline.
* Service worker cache version bumped to `pmc-shell-v49p-rev1` so the next
  page load activates the new SW, dropping any previously cached bundles.
* Manifest, apple-touch-icon and theme-color are unchanged from v49o.

### 3. Zoom meetings (already configured in v48c)
* The backend already supports both **Jitsi** (default) and real **Zoom**
  provider via Server-to-Server OAuth. To create a Zoom meeting, admin picks
  `provider: "zoom"` when scheduling; invite emails contain a magic-link
  `/meet/{token}` that lands on the meeting page and, for Zoom, exposes a
  primary "Open Zoom Meeting" button that jumps to the real Zoom URL.
* Backend env vars required (already set in prod):
  `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_HOST_EMAIL`.
* No code changes in this release for meetings — flagged for clarity.

## Bundles
* Frontend: `pmc-frontend-v49p-prod-build.zip`
  (built with `REACT_APP_BACKEND_URL=""` — same-origin S3/CloudFront)
* Backend: `pmc-backend-v49p.zip` (Dockerfile + `.platform/` at zip root)

## Deploy
### Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v49p-prod-build.zip` into your S3 bucket root
   (`aws s3 sync --delete` recommended).
2. Invalidate CloudFront: paths `/*`.
3. CloudFront SPA rule (must be set once): custom error responses — both
   `403` and `404` respond with `/index.html` and HTTP `200`.
4. Verify: open the site on your phone → hamburger menu → "Install app"
   should be visible above Sign in / Register.

### Backend (Elastic Beanstalk)
No code changes in the backend since v49o — you can reuse the existing
deployment. If you must redeploy, upload `pmc-backend-v49p.zip` as usual.

## Rollback
* Roll back to `v49o` or earlier if needed. Nothing in v49p changes routes,
  APIs or the database schema.

## Verified
* `test_reports/iteration_38.json` — 100% pass on mobile-fix scope
  (390×844, 320×568, and 1440×900 desktop regression).
* Manual: Pay EMD on `/vendor` (mobile) redirects to a real Stripe checkout
  URL. Manifest and service-worker are 200 OK and the SW registers with
  scope `/` and reaches state `activated`.
EOF
echo "     -> $DL/DOWNLOAD_${VER}.md"

echo ">>> Bundle sizes"
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
echo ">>> Done: $VER"
