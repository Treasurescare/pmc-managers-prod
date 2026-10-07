# PMC Managers — Mobile Store Upload Bundle v1.0.0

**One-shot bundle for everything you need to upload PMC Managers to the Apple App Store and Google Play — iOS native project, Android native project, store assets (icons + screenshots) and the step-by-step walk-through PDFs.**

> ⚠️ **Note on "AWS":** Apple App Store Connect and Google Play Console both upload directly from your local machine over HTTPS — **no AWS is involved**. "Upload to AWS" is not a step in this workflow. Download the bundle, open the native projects in Android Studio / Xcode on your laptop, and submit from there. (If you later want to host beta `.apk` or `.ipa` files on S3 for internal testers, that's a separate optional step — ping me and I'll wire it up.)

---

## 📦 Direct download links (preview-hosted, HTTPS)

### ⭐ Everything in one bundle
`https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-mobile-store-upload-bundle-v1.0.0.zip`

### Individual files (same content, uncompressed per platform)
| Artifact | Direct URL |
|---|---|
| Android Studio project (`.tar.gz`) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-mobile-android-v1.0.0.tar.gz |
| iOS Xcode project (`.tar.gz`) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-mobile-ios-v1.0.0.tar.gz |
| Store assets (icon + splash + screenshots `.zip`) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-mobile-store-assets-v1.0.0.zip |

### Docs (also included in the bundle)
| Doc | Direct URL |
|---|---|
| Master guide (reads first) | https://pmc-forest-green.preview.emergentagent.com/downloads/MOBILE_STORE_ASSETS_README.md |
| Build instructions | https://pmc-forest-green.preview.emergentagent.com/downloads/DOWNLOAD_mobile_v1.0.0.md |

---

## 🧭 What's inside the bundle (`pmc-mobile-store-upload-bundle-v1.0.0.zip`)

```
pmc_v1/
├── pmc-mobile-android-v1.0.0.tar.gz          ← Android Studio project
├── pmc-mobile-ios-v1.0.0.tar.gz              ← Xcode project (macOS)
├── pmc-mobile-store-assets-v1.0.0.zip        ← icon_1024.png, splash, 8 screenshots, feature graphic
├── README-mobile.md                          ← build + sync instructions
├── README-assets.md                          ← per-slot upload order
├── NATIVE_APP_BUILD_INSTRUCTIONS.md          ← long form build walk-through
├── APPLE_DEVELOPER_ACCOUNT_SETUP_WALKTHROUGH.md
├── GOOGLE_PLAY_ACCOUNT_SETUP_WALKTHROUGH.md
└── PMC_APP_STORE_PLAY_STORE_MASTER_GUIDE.md  ← the one-page master checklist
```

---

## 🚀 Shortest path to live apps

1. **Download the master bundle** (link above). Unzip somewhere on your laptop.
2. **Enroll** (if not already):
   - Apple Developer Program → https://developer.apple.com/programs/enroll — $99/yr. Allow 24–48h for the identity verification call-back.
   - Google Play Console → https://play.google.com/console/signup — one-time $25. Allow a few hours for the ID verification email.
3. **Build native binaries on your laptop:**
   - macOS: `tar -xzf pmc-mobile-ios-v1.0.0.tar.gz` → open `ios/App/App.xcworkspace` in Xcode → Any iOS Device (arm64) → **Product → Archive → Distribute App → App Store Connect**.
   - Any OS: `tar -xzf pmc-mobile-android-v1.0.0.tar.gz` → open `android/` in Android Studio → **Build → Generate Signed Bundle/APK → Android App Bundle → Release** → output file `app-release.aab`.
4. **Upload to the stores:**
   - **Apple**: App Store Connect → My Apps → + → New App → fill metadata → TestFlight tab receives the archive from Xcode automatically.
   - **Google**: Play Console → Create app → Internal testing track → upload `app-release.aab`.
5. **Store listing assets** (from `pmc-mobile-store-assets-v1.0.0.zip`):
   - Apple: 1024×1024 icon in Xcode, four 1290×2796 iPhone screenshots in App Store Connect.
   - Google: 1024×1024 icon, 1024×500 feature graphic, four 1080×2400 phone screenshots in Play Console.
6. **Review credentials** for Apple reviewers (go in App Store Connect → App Information → App Review Information):
   - Demo vendor login + demo admin login — pull the two Owner@/Vendor@ pairs from `/app/memory/test_credentials.md`.
7. **Submit for review.** Expect ~24–48h at Apple, ~2–3h at Google.

---

## ❓ If you literally need an S3 bucket (optional)

If you want me to:
- Push these artifacts into an S3 bucket you own and give you presigned links, OR
- Set up a `beta.pmcmanagers.com/downloads/` CloudFront distribution so testers can grab builds directly,

just reply with:
- The AWS account ID (or IAM access key / secret for the target bucket), and
- Which region + bucket name you'd like them in.

I'll wire the backend to re-publish each build straight to S3 going forward.
