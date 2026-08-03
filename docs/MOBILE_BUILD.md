# PMC Managers — Mobile Build Guide (PWA + Capacitor)

This document is the **single source of truth** for turning the existing
React frontend into installable mobile apps on both **iOS** and **Android**.

The mobile experience ships in two layers:

1. **PWA** — already live. Any modern phone/tablet can visit the URL and
   choose *Add to Home Screen* to get an icon, splash, offline shell, and
   push-capable install. No app store required.
2. **Capacitor native shell** — wraps the same React build inside real
   Google Play `.aab` and App Store `.ipa` binaries. Adds native camera,
   biometrics, and push out of the box.

The unified mobile entry point is `/m` — one login screen that auto-detects
Admin / Staff / Vendor and jumps to the correct dashboard.

---

## 0. What's already done

- ✅ `public/manifest.json` with icons, shortcuts, standalone display
- ✅ `public/service-worker.js` with offline app-shell cache + push handler
- ✅ Meta tags in `public/index.html` for iOS (`apple-mobile-web-app-capable`, splash)
- ✅ Service-worker registration in `src/index.js` (production only)
- ✅ Capacitor config at `frontend/capacitor.config.ts`
- ✅ Native plugin wrappers at `src/lib/mobileBridge.js` (camera, biometric, push, secure storage)
- ✅ Unified mobile login at `src/apps/mobile/MobileLogin.jsx` (route `/m`)

## 1. Install Capacitor + native plugins

```bash
cd /app/frontend
yarn add @capacitor/core @capacitor/cli
yarn add @capacitor/ios @capacitor/android
yarn add @capacitor/camera @capacitor/preferences @capacitor/push-notifications
yarn add @capacitor/splash-screen @capacitor/status-bar
yarn add @aparajita/capacitor-biometric-auth
```

## 2. Initialize + add platforms (one-time)

```bash
cd /app/frontend
npx cap init "PMC Tenders" com.pmcmanagers.tenders --web-dir build
yarn build                # produce the /build folder
npx cap add ios           # requires a Mac with Xcode installed
npx cap add android       # requires Android Studio installed
npx cap sync              # copies /build into ios/App and android/app
```

> **Note:** Emergent's cloud pod does NOT have Xcode or Android Studio.
> Run steps 2 and 3 on your local machine (Mac for iOS; any OS for Android).

## 3. Every code change

```bash
cd /app/frontend
yarn build && npx cap sync
```

Then either:

- **iOS:** `npx cap open ios` → Xcode → select signing team → Product ▸ Archive → Distribute App
- **Android:** `npx cap open android` → Android Studio → Build ▸ Generate Signed Bundle → `.aab` for Play Store

## 4. Store submission checklist

### Apple App Store
1. Apple Developer Program membership ($99/year)
2. Create App ID `com.pmcmanagers.tenders` in developer.apple.com
3. In Xcode set the same bundle ID + signing team
4. App Store Connect → New App → fill Privacy Nutrition Labels
5. Product ▸ Archive → Distribute App → App Store Connect
6. Wait for review (~1–3 days)

### Google Play Store
1. Google Play Developer account ($25 one-time)
2. Play Console → Create App → package `com.pmcmanagers.tenders`
3. Upload the signed `.aab` from Android Studio (Build ▸ Generate Signed Bundle)
4. Fill Data Safety form + content rating
5. Roll out to Production track

## 5. Push notifications setup

### Android (Firebase Cloud Messaging)
1. Create a Firebase project → Add Android app with package `com.pmcmanagers.tenders`
2. Download `google-services.json` → drop into `android/app/`
3. Server-side: use FCM Admin SDK with the token registered by `mobileBridge.registerPush`

### iOS (APNs)
1. In developer.apple.com → Keys → create an APNs Auth Key (.p8)
2. Upload key ID + team ID to Firebase Cloud Messaging OR use your backend directly
3. In Xcode: Capabilities → enable **Push Notifications** + **Background Modes** (Remote notifications)

Backend hook is already in place — `notifications.py` records the token; a
future `notify.py` upgrade will send via FCM/APNs when keys are present.

## 6. Biometric login (production hardening)

The current wrapper (`biometricAuthenticate`) only *verifies device presence*.
For real biometric SSO you need a **device-bound refresh token**:

- On first successful login, backend issues a long-lived refresh token
- Store it via `saveSecure("pmc.deviceToken", ...)` (uses iOS Keychain / Android EncryptedSharedPreferences)
- On biometric success, exchange the device token for a fresh session cookie
- Bake this into `staffApi.login` / `vendorApi.login` server-side

## 7. Camera capture (Certifier inspections)

Already wired — `takePicture()` uses the native camera on iOS/Android and
falls back to the browser file-picker on web/PWA. Certifier's inspection
upload flow (`StaffDashboard.jsx` line ~180) will auto-pick the native path
once Capacitor is installed.

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Blank screen after `cap sync` | `yarn build` wasn't run — build then re-sync |
| iOS build fails "no signing team" | Xcode → Signing & Capabilities → pick your team |
| Android SDK not found | `sdkmanager` or Android Studio SDK Manager → install SDK 34 |
| Push token never arrives on iOS | Enable Push Notifications capability in Xcode |
| Login works on web but not native | Backend cookie SameSite must be `None` + `Secure` for cross-origin native webview |

## 9. Cookie compatibility (native webviews)

Because Capacitor loads the app from `capacitor://localhost` (iOS) or
`https://localhost` (Android) while the API is on `emergentagent.com`, the
cookie must allow cross-site.

Backend already sets:
```python
set_cookie(secure=True, httponly=True, samesite="none")
```

**If cookies stop working on native**, verify the backend is HTTPS (Emergent
preview is) and that the frontend `capacitor.config.ts` uses the correct
`server.url` (only for dev).

## 10. Test matrix (post-install checklist)

- [ ] `/m` mobile login page renders
- [ ] Sign in as `adminsupport@pmcmanagers.com` → routes to `/admin`
- [ ] Sign in as `escrow@pmcmanagers.com` → routes to `/staff`
- [ ] Vendor sign-in routes to `/vendor`
- [ ] "Add to Home Screen" from Chrome/Safari installs with correct icon
- [ ] Offline: airplane mode → app shell still loads
- [ ] Camera capture works in Certifier inspection
- [ ] Biometric prompt appears on returning user
- [ ] Push token arrives at the backend
