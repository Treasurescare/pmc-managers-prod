# PMC Managers v2 — PRD (as of Feb 2026 — Mobile App Store Stream)

## Current Objective & Strategic Direction
1. **Mobile App Store & Play Store Launch**:
   - Publishing under UK Organization: **THE PMC MANAGERS LTD** (Company No. 17031540)
   - D-U-N-S Number acquired: **234578668** (Chiswick Park, London W4 5YG)
   - Unified multi-role mobile app (Public, Vendor, Buyer/Staff, Admin) powered by Capacitor.
   - Account email: `managerspmc@gmail.com`
   - Both developer accounts (Apple + Google) being created in parallel.

## Mobile App — Build Artifacts (v1.0.0)
- **App ID:** `com.pmcmanagers.tenders`
- **App Name (device):** `PMC Tenders`
- **Store listing title:** `PMC Managers`
- **Marketing version:** 1.0.0 • **versionCode / Build:** 1
- Native Android project: `/app/frontend/android/`
- Native iOS project: `/app/frontend/ios/`
- Capacitor 8.x configured (`capacitor.config.ts`)
- `.capignore` added to exclude 1.5GB of legacy `/downloads/` from mobile bundles

### Downloadable deliverables (preview-hosted)
- `/downloads/pmc-mobile-android-v1.0.0.tar.gz` — Android Studio project
- `/downloads/pmc-mobile-ios-v1.0.0.tar.gz` — Xcode project (macOS build)
- `/downloads/DOWNLOAD_mobile_v1.0.0.md` — download & build instructions

### Store-submission guides
- `/app/docs/store_submission/PMC_APP_STORE_PLAY_STORE_MASTER_GUIDE.md`
- `/app/docs/store_submission/GOOGLE_PLAY_ACCOUNT_SETUP_WALKTHROUGH.md`
- `/app/docs/store_submission/APPLE_DEVELOPER_ACCOUNT_SETUP_WALKTHROUGH.md`
- `/app/docs/store_submission/NATIVE_APP_BUILD_INSTRUCTIONS.md`
- `/app/scripts/scaffold_native_apps.sh`

## Latest web releases (unchanged)
- **v51ad** — Corrigenda full workflow & saved filter presets
- **v51ac** — Vendor registration per-row edit links; expires-filter cleanup
- **v51aa–ab** — Full 5-section bulk CSV template, full vendor editor, MoneyFilterBar, reverse auction edits

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback), Capacitor native bridge (iOS + Android).

## Up next
- Complete Apple & Google Play developer account enrollments (user action).
- Generate 1024×1024 PMC Managers app icon + splash screens.
- Capture iOS 6.7" and Android phone store screenshots from the live platform.
- Carry-forward from v51ad: vendor-side corrigenda banner + 412 bid-submit
  pre-check wiring on `/api/v1/bids`.

## Store Enrollment Status
- ✅ D-U-N-S Number: 234578668
- 🟡 Apple Developer Program ($99/yr, Organization) — user filling form now
- 🟡 Google Play Console ($25 one-time, Organization) — user filling form now
- 🟡 Native bundles ready to compile once accounts are approved
