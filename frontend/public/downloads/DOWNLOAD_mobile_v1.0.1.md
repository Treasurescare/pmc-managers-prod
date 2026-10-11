# PMC Managers — Android v1.0.1 (versionCode 2) — 11 Oct 2026

Updated Google Play bundle project with the latest web app (v52cb), including:

- Corrigenda second-search live feedback + withdraw dialog regression fix (v52ca)
- Registrations card layout fix — "Edit sections" attached to correct vendor (v52cb)
- "Back to Registrations" button in admin-opened registration tabs (v52cb)
- Evaluation tender picker — typing "18" surfaces PMC-NOT-2026-0018 (v52cb)
- Everything from v52bx/v52by/v52bz (session isolation, reverse auctions, BOQ
  exports, rubric persistence, withdraw dialog)

## What changed in the native project
- `android/app/src/main/assets/public/` refreshed with the v52cb production
  web build (verified: bundle contains the latest `main.*.js`).
- `android/app/build.gradle`: `versionCode 1 → 2`, `versionName "1.0.0" → "1.0.1"`
  (Google Play requires a higher versionCode for every update).
- Upload keystore + signing config unchanged (`pmc-upload-key.keystore`,
  alias `pmc-upload`) — same identity as v1.0.0, so this installs as an
  update, not a new app.

## Build the signed .aab (on your dev machine)
This environment has no Android SDK, so the final `.aab` is built locally:

```bash
tar -xzf pmc-mobile-android-v1.0.1.tar.gz
cd frontend/android
./gradlew bundleRelease
# output: app/build/outputs/bundle/release/app-release.aab
```

Then: Play Console → PMC Managers → Production → Create new release →
upload the new `.aab`. Play App Signing is already enabled, so the upload
key in the project is all you need.

Full walkthrough: `docs/store_submission/NATIVE_APP_BUILD_INSTRUCTIONS.md`
(step 5d).

File: `pmc-mobile-android-v1.0.1.tar.gz`
