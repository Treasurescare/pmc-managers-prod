# PMC v46s — Mobile & PWA Hotfix

## What v46s fixes

1. **Android — "no download/install option"**
   Chrome's native install banner fires unpredictably. v46s adds an explicit
   **"Install on your phone"** prompt (bottom of screen) that captures the
   browser's `beforeinstallprompt` event and triggers the native install
   dialog on tap. Dismissal remembers for 7 days. Hidden once installed.

2. **iPhone — hamburger menus trapped under the notch/status bar**
   Both the landing-page header (top-right hamburger) and the post-login
   Admin dashboard header (top-left hamburger) now apply iOS safe-area
   padding via `env(safe-area-inset-top)`. The mobile drawers get matching
   top/bottom safe-area padding, and the Admin hamburger tap target grew
   from 34 px to 44 px. With `viewport-fit=cover` already set in index.html,
   these insets resolve to real pixel values on notched iPhones.

   On iOS Safari, the install prompt shows guided steps instead:
   **Share → Add to Home Screen → Add**.

## New / changed files (frontend only — backend unchanged from v46r)

| File | Change |
|---|---|
| `src/components/PwaInstallPrompt.jsx` | **New** — Android install button + iOS instructions |
| `src/App.css` | **New utilities** `.pmc-safe-top` / `.pmc-safe-bottom` / `.pmc-safe-x` |
| `src/apps/shared/TopBar.jsx` | Header + drawer get safe-area padding |
| `src/apps/admin-console/AdminShell.jsx` | Sticky header gets safe-area padding; hamburger tap target enlarged |
| `src/App.js` | Mounts `<PwaInstallPrompt />` globally |

## Download

- **[pmc-frontend-v46s-prod-build.zip](./pmc-frontend-v46s-prod-build.zip)** — deploy this to S3/CloudFront (same commands as v46r in `DOWNLOAD_v46r.md`)
- Backend: **[pmc-backend-v46r.zip](./pmc-backend-v46r.zip)** — unchanged, still current

## Manual iPhone test after deploy

1. Open `https://pmcmanagers.com` in Safari on the iPhone.
2. Hamburger (top right) must sit below the clock/status bar — not under it.
3. The "Install on your phone" card appears after ~2.5 s → follow the
   Share → Add to Home Screen steps.
4. Once installed, open the app icon: standalone shell, no Safari chrome.
5. Log in → Admin hamburger (top left) must also clear the status bar.

## Manual Android test after deploy

1. Open the site in Chrome.
2. The "Install on your phone" card appears → tap **Install app**.
3. Chrome's native install sheet opens → Install.
4. App icon appears in the launcher; opens in standalone mode.
