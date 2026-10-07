# PMC Managers v2 — PRD (as of Feb 2026 — Mobile App Store Stream)

## Current Objective
Publish PMC Managers to the Apple App Store and Google Play under
**THE PMC MANAGERS LTD** (UK Co. 17031540, D-U-N-S **234578668**,
Chiswick Park, London W4 5YG), as a unified Capacitor app with
Public / Vendor / Buyer / Admin roles.

## Mobile stream — current status
| Milestone | Status |
|---|---|
| D-U-N-S Number acquired | ✅ 234578668 |
| Apple Developer Program enrollment | 🟡 user filling form now |
| Google Play Console enrollment | 🟡 Identity docs submitted, under Google review (few days). Phone verification (+447724545222) gated behind identity approval. App creation locked until all verifications complete. ⚠️ Public developer name currently "Harneet" (was "Shweta Vaswani") — recommend changing to "PMC Managers" |
| Capacitor 8 native projects scaffolded | ✅ `/app/frontend/android` + `/app/frontend/ios` |
| Native project archives for the dev machine | ✅ `pmc-mobile-android-v1.0.0.tar.gz`, `pmc-mobile-ios-v1.0.0.tar.gz` |
| App icon 1024×1024 | ✅ `mobile_assets/icon_1024.png` |
| iOS launch screen | ✅ `mobile_assets/splash_portrait.png` |
| Google Play feature graphic 1024×500 | ✅ `mobile_assets/android_feature_1024x500.png` |
| iOS 6.7" screenshots (Public / Vendor / Admin / Auction) | ✅ 4 shots |
| Android phone screenshots (Public / Vendor / Admin / Auction) | ✅ 4 shots |
| Website ownership verified (Search Console) | ✅ "Ownership verified" via HTML tag (07 Oct 2026) — the `google-site-verification` meta tag in `public/index.html` must NEVER be removed, or verification is revoked |
| Store asset bundle | ✅ `pmc-mobile-store-assets-v1.0.0.zip` (13 files: 3 brand assets + 10 store screenshots + README) |

## Account email
`managerspmc@gmail.com` (both Apple ID and Google Account owner).

## Mobile build identity
- `appId` / Bundle ID: `com.pmcmanagers.tenders`
- Device name: `PMC Tenders`
- Store listing title: `PMC Managers`
- Marketing version: `1.0.0` • build / versionCode: `1`
- Palette: forest green `#0b3d2e`, navy `#0b1e3f`, brass `#d4af37`

## Store-submission docs (`/app/docs/store_submission/`)
- `PMC_APP_STORE_PLAY_STORE_MASTER_GUIDE.md`
- `GOOGLE_PLAY_ACCOUNT_SETUP_WALKTHROUGH.md`
- `GOOGLE_PLAY_SIGNUP_CHEATSHEET.md` (field-by-field for in-form filling)
- `APPLE_DEVELOPER_ACCOUNT_SETUP_WALKTHROUGH.md`
- `NATIVE_APP_BUILD_INSTRUCTIONS.md`
- `/app/scripts/scaffold_native_apps.sh`
- `/app/scripts/generate_app_icons.py`

## Downloadable deliverables (preview-hosted)
- `/downloads/pmc-mobile-android-v1.0.0.tar.gz`
- `/downloads/pmc-mobile-ios-v1.0.0.tar.gz`
- `/downloads/pmc-mobile-store-assets-v1.0.0.zip`
- `/downloads/MOBILE_STORE_ASSETS_README.md`
- `/downloads/DOWNLOAD_mobile_v1.0.0.md`

## Latest web releases
- **v51ag** — Vendor requests + Profile changes gain search/date-range filters;
  BOQ, Bidding ops, Escrow filters now actually hide non-matching rows (DOM
  row tags: `data-row`, `data-status`, `data-created-at`); Work packages
  Kanban switched to horizontal-scroll with 280 px cards; package View modal
  lists attached documents with View/Download links; MoneyFilterBar enforces
  Created-to ≥ Created-from and Expires-to ≥ Expires-from on every panel; each
  pending Escrow transaction shows an "Officer identity hint" explaining which
  side the signed-in admin will sign as (or that they're neither officer, so
  the sign call will be rejected and both officers must log in separately).
  Frontend-only ZIP: `pmc-frontend-v51ag-prod-build.zip`.
- **v51af** — Fix: Registrations "Edit sections" button (verified in preview:
  editable form opens + saves on a submitted registration). Bundles built:
  `pmc-frontend-v51af-prod-build.zip` + `pmc-backend-v51af.zip` +
  `DOWNLOAD_v51af.md`. Google verification meta tag carried forward.
  Root cause: 11/74 registrations (legacy rows) have no `magic_token`, so the
  resume link was built with `token=` empty and RegistrationResume bounced to
  `/register`. Backend `admin_resume_link` now mints+persists a token when
  missing; new admin-only `PATCH /api/v1/registrations/admin/{rid}` lets admins
  save edits on submitted/under_review registrations (public token PATCH only
  allows draft/needs_clarification); RegistrationResume uses the admin path
  when opened with `?from=admin&rid=...`.
- **v51ae** — Google Search Console verification meta tag added to
  `index.html` (`t7scPgT9ZxpjYxkyRAyB8cCvfrCh04IAO6XcvAvS4r0`) so Play
  Console "Verify your organization's website" resolves on pmcmanagers.com.
  Frontend-only ZIP: `pmc-frontend-v51ae-prod-build.zip`.
- **v51ad** — Corrigenda full workflow & saved filter presets
- **v51ac** — Vendor registration per-row edit links; expires-filter cleanup
- **v51aa-ab** — Full 5-section bulk CSV, full vendor editor, MoneyFilterBar,
  reverse auction edits

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key, Gemini 3.1 Flash (image generation for brand assets),
Capacitor 8 native bridge (iOS + Android).

## Up next
- User completes Apple + Google Play enrollments and ships us the two
  approval emails.
- Once approved, build `.aab` on dev machine, upload to Google Play
  Internal Testing track.
- Once Apple Account Holder is live, archive in Xcode and upload to
  TestFlight.
- Carry-forward from v51ad: vendor-side corrigenda banner + 412
  bid-submit pre-check wiring on `POST /api/v1/bids`.
