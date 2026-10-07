# PMC MANAGERS — APP STORE & GOOGLE PLAY STORE PUBLISHING MASTER BLUEPRINT
**Target Entity:** THE PMC MANAGERS LTD (UK Company No. 17031540)  
**Registered Office:** Office Gold, Building 7, Floor 5 Chiswick Park, 566 Chiswick High Road, London, UK, W4 5YG  
**App Type:** Full Unified Procurement SaaS (Public Tenders, Vendor Portal, Buyer/Staff Console, Admin Panel)

---

## EXECUTIVE SUMMARY & ROADMAP OVERVIEW

This blueprint takes you from **zero to live in production** across both the **Apple App Store (iOS)** and **Google Play Store (Android)** under your verified corporate entity: **THE PMC MANAGERS LTD**.

Publishing as an **Organization** gives PMC Managers:
- High institutional credibility with government and corporate buyers.
- Verified company name displayed under the app title (*"THE PMC MANAGERS LTD"*).
- Multi-user team management without sharing root passwords.
- Exemption from Google Play’s 20-tester personal testing gate.

---

## PHASE 1: ACQUIRING THE D-U-N-S NUMBER (PREREQUISITE FOR BOTH APPLE & GOOGLE)

Both Apple and Google require a **D-U-N-S (Data Universal Numbering System) Number** from Dun & Bradstreet (D&B) to verify UK corporate entities.

### Step 1.1: Check if PMC Managers Already Has a D-U-N-S Number
1. Visit Apple's D-U-N-S Lookup portal: **https://developer.apple.com/enroll/duns-lookup/** (or D&B UK: **https://www.dnb.co.uk/**).
2. Enter your company information:
   - **Legal Entity Name:** `THE PMC MANAGERS LTD`
   - **Company Registration Number:** `17031540`
   - **Registered Address:** `Office Gold, Building 7, Floor 5 Chiswick Park, 566 Chiswick High Road, London, W4 5YG, United Kingdom`
3. If a D-U-N-S Number is returned, save the 9-digit number.

### Step 1.2: If No D-U-N-S Number Exists, Request One (Free)
1. Complete the request form on the Apple D-U-N-S lookup page or directly via D&B UK.
2. D&B will email you within 24–48 hours requesting proof of company formation (your UK Companies House Certificate of Incorporation for `17031540`).
3. D&B will issue your 9-digit D-U-N-S Number within 1–5 business days (at no cost).
4. *Note:* Allow 24–48 hours after issuance before enrolling with Apple/Google so their automated databases sync with D&B.

---

## PHASE 2: APPLE DEVELOPER PROGRAM ENROLLMENT ($99/YEAR)

### Step 2.1: Prepare Apple Requirements
1. **Apple ID:** Create or use an Apple ID associated with an official corporate domain email (e.g., `admin@pmcmanagers.com` or `dev@pmcmanagers.com`, avoid personal @gmail.com).
2. **Two-Factor Authentication (2FA):** Must be enabled on the Apple ID via an Apple device (iPhone/iPad/Mac) or web.
3. **Legal Authority:** The person enrolling must be an owner/founder or have legal binding authority for THE PMC MANAGERS LTD.
4. **Corporate Website:** `https://pmcmanagers.com` must be live and accessible with HTTPS.

### Step 2.2: Enrollment Steps
1. Navigate to: **https://developer.apple.com/programs/enroll/**
2. Sign in with the Corporate Apple ID.
3. Select **"Organization"** as the Entity Type.
4. Fill in Corporate Information:
   - **Legal Entity Name:** `THE PMC MANAGERS LTD` (must match Companies House & D&B exactly).
   - **D-U-N-S Number:** Enter your 9-digit D-U-N-S number.
   - **Website:** `https://pmcmanagers.com`
   - **Headquarters Phone & Address:** UK Chiswick Park address.
5. Provide Signing Authority verification details.
6. Submit enrollment. Apple will review and may call the corporate phone number to verify identity.
7. Once approved (usually 2–3 business days), complete the **$99/year subscription payment** in Apple Developer / App Store Connect.

---

## PHASE 3: GOOGLE PLAY CONSOLE ENROLLMENT ($25 ONE-TIME FEE)

### Step 3.1: Prepare Google Requirements
1. **Google Account:** Create or use a Google Workspace/Gmail account dedicated to the organization (e.g., `google-play@pmcmanagers.com` or `admin@pmcmanagers.com`).
2. **Payment Card:** International credit/debit card for the one-time $25 fee.
3. **Official Documents:** PDF of UK Certificate of Incorporation (17031540) and proof of address (utility bill, bank statement, or official lease under THE PMC MANAGERS LTD).

### Step 3.2: Enrollment Steps
1. Navigate to: **https://play.google.com/console/signup**
2. Choose **"An Organization or Business"** account.
3. Provide Developer Name: `THE PMC MANAGERS LTD` (or `PMC Managers Ltd`).
4. Enter your 9-digit D-U-N-S number and business registration number (`17031540`).
5. Enter contact details:
   - Public Developer Email (e.g., `support@pmcmanagers.com`)
   - Official Phone Number (with SMS/call verification)
6. Pay the $25 one-time registration fee.
7. Complete **Organization Identity Verification**: Upload the Companies House document and ID of the authorized representative. Google approves within 2–4 business days.

---

## PHASE 4: STORE ASSETS, COMPLIANCE & METADATA PREPARATION

### 4.1 Store Listing Metadata
- **App Name (Title):** `PMC Managers - Procurement SaaS` (Max 30 chars on iOS, 30 chars on Android)
- **Subtitle (iOS):** `Tenders, Bidding & Escrow Portal` (Max 30 chars)
- **Short Description (Android):** `Global procurement, tender management, reverse auctions, and secure escrow.` (Max 80 chars)
- **Full Description:**
  ```text
  PMC Managers is a comprehensive, institutional-grade procurement and tender management platform designed for public and private sector projects.

  Key Features:
  • Live Notice & Tender Exploration: Discover active RFPs, EOIs, and procurement notices.
  • Five-Section Vendor Registration & Compliance: Instant vendor profiles, verification, and category matching.
  • Real-Time Reverse Auctions: Dynamic multi-vendor competitive bidding with instant price decrement validation.
  • Secure Escrow & EMD Tracking: Joint signing, EMD payments, and milestone fund releases.
  • Corrigenda & Addenda System: Real-time notices, document diffs, and mandatory acknowledgment before bid submission.
  • Multi-Role Access: Dedicated experiences for Public Observers, Vendors/Contractors, Evaluators/Staff, and Procurement Admins.
  ```

- **Category:** Business / Productivity
- **Content Rating:** Everyone / PEGI 3 / General

### 4.2 Required Legal & Support URLs (Mandatory for Store Approval)
1. **Privacy Policy URL:** `https://pmcmanagers.com/privacy`
2. **Terms of Service URL:** `https://pmcmanagers.com/terms`
3. **Support URL:** `https://pmcmanagers.com/support` or `mailto:support@pmcmanagers.com`
4. **Account Deletion Link (App Store Guideline 5.1.1(v) & Play Store Data Safety):**
   - In-app Account Settings -> "Delete Account" button + web link `https://pmcmanagers.com/account/delete-request`.

### 4.3 Visual Assets Specifications
1. **App Icon:** `1024 x 1024 px` PNG (32-bit, no alpha/transparency for iOS; rounded automatically by OS).
2. **Android Feature Graphic:** `1024 x 500 px` JPG/PNG.
3. **iOS Screenshots:**
   - 6.7" Super Retina (iPhone 16 Pro Max / 15 Pro Max): `1290 x 2796 px` (min 3 screenshots)
   - 6.5" Display (iPhone 11 Pro Max / XS Max): `1242 x 2688 px`
   - 12.9" iPad Pro (Optional/Recommended): `2048 x 2732 px`
4. **Android Screenshots:**
   - Phone: Minimum 4 screenshots (`1080 x 2400 px` or `1080 x 1920 px`).

### 4.4 App Review Credentials (Demo Accounts)
App reviewers require working credentials to test authenticated features:
- **Role 1 (Vendor):** Provide a pre-verified test vendor login.
- **Role 2 (Buyer/Staff):** Provide a demo staff login with access to notice browsing and evaluation demo data.

---

## PHASE 5: TECHNICAL PACKAGING (CAPACITOR NATIVE BUILD PIPELINE)

The PMC platform uses **Capacitor** to wrap the production React frontend into native iOS and Android projects.

### Step 5.1: Build Production Web Bundle
```bash
cd /app/frontend
yarn build
```

### Step 5.2: Sync with Native Projects
```bash
# Add native platforms (done once)
npx cap add ios
npx cap add android

# Sync latest web build and plugins into iOS and Android shells
npx cap sync
```

### Step 5.3: Android Production Release (`.aab` / Android App Bundle)
1. Open Android project in Android Studio: `npx cap open android`
2. Configure `build.gradle` (Application ID: `com.pmcmanagers.tenders`, Version Code: `1`, Version Name: `1.0.0`).
3. Generate Signed Bundle:
   - Menu -> **Build** -> **Generate Signed Bundle / APK** -> **Android App Bundle (.aab)**.
   - Create a new production Keystore file (`pmc-release-key.jks`) and record the password securely.
4. Upload `app-release.aab` to Google Play Console under **Production** or **Internal Testing**.

### Step 5.4: iOS Production Release (`.ipa` / TestFlight & App Store)
1. Open iOS project in Xcode on macOS: `npx cap open ios`
2. In Signing & Capabilities:
   - Team: Select **THE PMC MANAGERS LTD**.
   - Bundle Identifier: `com.pmcmanagers.tenders`
3. Set target build version (e.g. `1.0.0`, Build `1`).
4. Select **Any iOS Device (arm64)** as destination.
5. Menu -> **Product** -> **Archive**.
6. When Organizer opens, click **Distribute App** -> **App Store Connect** -> **Upload**.
7. App will appear in **App Store Connect** within 15–30 minutes for TestFlight beta testing and App Store submission.

---

## PHASE 6: STORE SUBMISSION & REVIEW BEST PRACTICES

1. **TestFlight (iOS Beta):** Invite internal stakeholders and client testers instantly via public link or email before general App Store release.
2. **Google Play Internal Testing:** Test the `.aab` instantly on Android devices with zero delay.
3. **App Store Review Submission:**
   - Fill in App Information, Pricing (Free), App Privacy nutrition label (Storage, Contact Info, User ID).
   - Provide Demo account in App Review Notes.
   - Typical review time: **24 to 48 hours**.
4. **Google Play Review Submission:**
   - Complete Data Safety questionnaire (encryption in transit, personal/financial data usage for procurement and identity verification).
   - Typical review time: **1 to 3 business days**.

---

## DIRECT ACTION CHECKLIST FOR PMC MANAGERS TEAM

- [ ] **Step 1:** Look up or request D-U-N-S number for THE PMC MANAGERS LTD (Free via Apple D-U-N-S portal).
- [ ] **Step 2:** Enroll in Apple Developer Program ($99/yr) under Organization with D-U-N-S.
- [ ] **Step 3:** Enroll in Google Play Console ($25 one-time) under Organization with D-U-N-S.
- [ ] **Step 4:** Confirm store contact email (`support@pmcmanagers.com`) and legal URLs (`/privacy`, `/terms`).
- [ ] **Step 5:** Generate app icons and store screenshots from the live platform.
- [ ] **Step 6:** Compile final native bundles (`.aab` for Play Store, `.ipa` via Xcode for App Store Connect).
