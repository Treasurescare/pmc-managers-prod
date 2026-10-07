# PMC MANAGERS — NATIVE MOBILE APP BUILD INSTRUCTIONS
**For:** THE PMC MANAGERS LTD (D-U-N-S 234578668)  
**Bundle ID (iOS & Android):** `com.pmcmanagers.tenders`  
**App Name:** `PMC Managers`

This document shows exactly how to turn the current PMC web app into the `.aab`
(Google Play) and `.ipa` (Apple App Store) bundles the review teams need.

Capacitor **8.x CLI requires Node ≥ 22 LTS**. Install it on your dev machine
first — the Emergent preview container runs Node 20, so the actual
scaffolding and native builds must happen on your own macOS laptop or
Windows/Linux workstation.

---

## STEP 0 — INSTALL PREREQUISITES (ONE-TIME)

### On macOS (recommended — iOS requires macOS)
```bash
# 1. Node 22 LTS
brew install node@22
echo 'export PATH="/opt/homebrew/opt/node@22/bin:$PATH"' >> ~/.zshrc

# 2. Xcode (latest from the Mac App Store) → open once and accept the licence
sudo xcodebuild -license accept

# 3. Android Studio → https://developer.android.com/studio (also installs the SDK + Gradle)

# 4. Yarn
npm i -g yarn
```

### On Windows / Linux (Android only — iOS needs macOS)
```bash
# Node 22 LTS from https://nodejs.org/en/download/current
# Android Studio from https://developer.android.com/studio
npm i -g yarn
```

---

## STEP 1 — PULL THE PMC REPO AND INSTALL DEPS
```bash
git clone <your PMC Managers repo URL> pmc-managers
cd pmc-managers/frontend
yarn install
```

---

## STEP 2 — BUILD THE REACT WEB BUNDLE (SAME ONE SHIPPED TO AWS)
```bash
GENERATE_SOURCEMAP=false yarn build
```
This creates `/frontend/build/` — the exact production bundle Capacitor
wraps into the native app shells.

---

## STEP 3 — SCAFFOLD THE NATIVE PROJECTS (ONLY FIRST TIME)
```bash
cd frontend
npx cap add android   # creates frontend/android/
npx cap add ios       # creates frontend/ios/     (macOS only)
```

Both commands read `capacitor.config.ts` (already shipped in the repo):
```ts
appId   : 'com.pmcmanagers.tenders'
appName : 'PMC Tenders'
webDir  : 'build'
```

Commit the new `android/` and `ios/` folders to git so your team shares one
canonical native project.

---

## STEP 4 — SYNC THE WEB BUILD INTO NATIVE PROJECTS
Run this every time you change the React code or bump the version:
```bash
npx cap sync
```
`cap sync` copies `build/` into both `android/` and `ios/` and installs any
new Capacitor plugins.

---

## STEP 5 — ANDROID: PRODUCTION `.aab` FOR GOOGLE PLAY

### 5a. Open the project in Android Studio
```bash
npx cap open android
```
First launch takes ~5 min while Gradle downloads dependencies.

### 5b. Create a release keystore (one-time, keep it SAFE)
```bash
keytool -genkey -v \
  -keystore ~/pmc-release-key.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias pmc-release
```
Save the keystore password and the alias password in **1Password / Bitwarden
company vault**. If you lose this file you will *never* be able to update
PMC Managers on Google Play — only publish a new app with a different
Bundle ID.

> 🔐 **Enable Google Play App Signing** when you upload the first `.aab`
> (Play Console → Setup → App integrity). Google then stores your signing
> key on their side and you only need to protect an *upload* key.

### 5c. Register the keystore in `android/app/build.gradle`
Add inside `android { ... }`:
```gradle
signingConfigs {
    release {
        storeFile file(System.getenv("PMC_KEYSTORE_FILE") ?: "/absolute/path/to/pmc-release-key.jks")
        storePassword System.getenv("PMC_KEYSTORE_PASSWORD")
        keyAlias "pmc-release"
        keyPassword System.getenv("PMC_KEY_PASSWORD")
    }
}
buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled true
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
    }
}
defaultConfig {
    applicationId "com.pmcmanagers.tenders"
    minSdkVersion 23
    targetSdkVersion 34
    versionCode 1          // bump every upload (1, 2, 3 ...)
    versionName "1.0.0"    // human-readable
}
```

### 5d. Build the signed Android App Bundle
Android Studio menu → **Build → Generate Signed Bundle / APK → Android App
Bundle → Release**. Output lands at:
```
frontend/android/app/build/outputs/bundle/release/app-release.aab
```
This is the file you upload to Google Play Console → **Internal Testing
→ Create new release → Upload `.aab`**.

---

## STEP 6 — iOS: PRODUCTION `.ipa` FOR APP STORE CONNECT (macOS only)

### 6a. Open the project in Xcode
```bash
npx cap open ios
```

### 6b. Signing & Capabilities
1. In Xcode left pane select **App** target.
2. **Signing & Capabilities** tab:
   - Team: **THE PMC MANAGERS LTD** *(appears after your Apple Developer
     account is approved and your Mac is signed into Xcode)*.
   - Bundle Identifier: `com.pmcmanagers.tenders`
   - Automatically manage signing: ✅
3. Under **Capabilities** add anything the app uses later (Push
   Notifications, Associated Domains, etc. — not required for v1).

### 6c. Version & build
In the **General** tab:
- Marketing version: `1.0.0`
- Build: `1` *(bump every upload — 1, 2, 3 ...)*

### 6d. Archive and upload
1. Device selector (top bar): **Any iOS Device (arm64)**.
2. Menu → **Product → Archive**. Takes ~5 min on first archive.
3. When Organizer opens: **Distribute App → App Store Connect → Upload →
   Automatically manage signing → Upload**.
4. Within ~30 min App Store Connect emails you *"Build 1 is ready to
   test"* — move it to TestFlight for beta testers, then submit for App
   Store review.

---

## STEP 7 — VERSION BUMPS GOING FORWARD

Every time you ship a new mobile release:

| File | Change |
|---|---|
| `frontend/android/app/build.gradle` | `versionCode` += 1, `versionName` to the new semver |
| iOS Xcode → General | `Build` += 1, `Marketing Version` to the new semver |
| `frontend/package.json` | optional — keeps the web + mobile versions aligned |

Then:
```bash
cd frontend
GENERATE_SOURCEMAP=false yarn build
npx cap sync
```
…and rebuild / rearchive from Android Studio and Xcode as in Steps 5–6.

---

## STEP 8 — FIRST-RELEASE CHECKLIST (TICK BEFORE SUBMITTING)

- [ ] `pmcmanagers.com/privacy` live and accessible (required by both stores).
- [ ] `pmcmanagers.com/terms` live.
- [ ] `pmcmanagers.com/account/delete-request` reachable (required by both
      stores so users can request deletion).
- [ ] App icon 1024×1024 PNG uploaded.
- [ ] 4+ store screenshots per device size.
- [ ] App review demo credentials prepared (one Vendor login + one
      Buyer/Staff login).
- [ ] `applinks:pmcmanagers.com` entry on your website if you want deep
      links to open the installed app (optional for v1).
