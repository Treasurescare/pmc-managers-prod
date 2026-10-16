# PMC Managers — Mobile Native Projects v1.0.0

**App ID:** `com.pmcmanagers.tenders`
**App Name:** PMC Tenders (shown on home screen)
**Store listing title:** PMC Managers
**Marketing version:** 1.0.0 • **Build / versionCode:** 1
**Capacitor:** 8.x • **Node required on dev machine:** ≥22 LTS

## Download bundles
- Android (Android Studio project): `pmc-mobile-android-v1.0.0.tar.gz`
- iOS (Xcode project): `pmc-mobile-ios-v1.0.0.tar.gz`

Each archive contains the Capacitor-generated native project plus the
`capacitor.config.ts` and `.capignore` you need to re-sync fresh web
builds.

## Build procedure (abridged — full guide: `NATIVE_APP_BUILD_INSTRUCTIONS.md`)

```bash
# 1. unpack next to the frontend/ folder of the PMC repo
tar -xzf pmc-mobile-android-v1.0.0.tar.gz
tar -xzf pmc-mobile-ios-v1.0.0.tar.gz        # macOS only

# 2. install Node 22 + yarn + Android Studio + Xcode

# 3. rebuild the React bundle and sync into the native projects
cd frontend
GENERATE_SOURCEMAP=false yarn build
npx cap sync

# 4a. Android → .aab for Google Play
npx cap open android
# In Android Studio: Build → Generate Signed Bundle/APK → Android App Bundle → Release
#     Output: android/app/build/outputs/bundle/release/app-release.aab

# 4b. iOS → .ipa for App Store Connect (macOS only)
npx cap open ios
# In Xcode: Any iOS Device (arm64) → Product → Archive → Distribute App → App Store Connect
```

## Pre-shipped settings
- **Android `applicationId`** `com.pmcmanagers.tenders` (`android/app/build.gradle`)
- **iOS `CFBundleDisplayName`** `PMC Tenders` (`ios/App/App/Info.plist`)
- **Splash & background colour** navy `#0b1e3f` with brass spinner `#ffcf76`
- **Push Notifications** plugin pre-registered (iOS APNs cert must be
  generated in your Apple Developer account before enabling at runtime).

## Required before each store submission
- 1024×1024 PNG app icon (not yet generated — add via Android Studio
  Image Asset Studio + Xcode Assets.xcassets).
- 4+ screenshots per device size.
- Privacy policy, Terms of Service, Account-Deletion URLs live under
  `pmcmanagers.com`.
- Working App Review demo credentials (Vendor + Buyer/Staff).
