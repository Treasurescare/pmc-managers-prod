# PMC Managers — iPhone App: from zero to the App Store

Account: THE PMC MANAGERS LIMITED · App name: **PMC Managers** · Bundle ID: **com.pmcmanagers.tenders** · Version 1.0.0 (build 1)

The app opens the live website www.pmcmanagers.com inside a native iPhone shell, and adds phone-only features:
new-tender push alerts, Face ID lock, native share, an offline screen, and in-app account deletion.
Every website release reaches the app automatically — you only re-upload the app when the native parts change.

**Before you start:** the website must be running release **v60i** or later (it contains the app features and the
account-deletion screen Apple checks). Upload v60i to AWS first.

---

## Part A — Apple Developer website (about 10 minutes)

You are already on developer.apple.com/account.

### A1. Register the app's ID
1. Under **Certificates, IDs & Profiles** click **Identifiers**.
2. If `com.pmcmanagers.tenders` is already in the list, click it and go to step 6.
3. Click the blue **+** → choose **App IDs** → **Continue** → choose **App** → **Continue**.
4. Description: `PMC Managers`. Bundle ID: **Explicit** → `com.pmcmanagers.tenders`.
5. Scroll the Capabilities list and tick **Push Notifications**. Click **Continue** → **Register**.
6. (If it already existed) make sure **Push Notifications** is ticked, then **Save**.

### A2. Create the push-notification key (for new-tender alerts)
1. Click **Keys** (left menu, or Account → Keys) → blue **+**.
2. Key name: `PMC Push`. Tick **Apple Push Notifications service (APNs)** → **Configure** →
   Environment **Sandbox & Production**, Key restriction **Team Scoped (All Topics)** → **Save** → **Continue** → **Register**.
3. Click **Download**. A file `AuthKey_XXXXXXXXXX.p8` is saved. **Apple lets you download it only once** — keep it safe
   (do not email it or post it in chat).
4. Write down the **Key ID** (10 characters, shown on the page).
5. Click **Membership details** (Account page) and write down your **Team ID** (10 characters).

### A3. Create the App Store listing
1. Go to **App Store Connect → Apps** (appstoreconnect.apple.com/apps) → blue **+** → **New App**.
2. Platforms: **iOS** · Name: `PMC Managers` · Primary language: **English (U.S.)** ·
   Bundle ID: pick **com.pmcmanagers.tenders** · SKU: `PMCMANAGERS001` · User access: **Full Access** → **Create**.
   (If "PMC Managers" is already taken by someone else, use `PMC Managers – Tenders`.)

---

## Part B — Your MacBook Air (about 1 hour, mostly downloads)

### B1. Check macOS and install Xcode
1. Apple menu  → **About This Mac**. You need **macOS Sequoia 15.6 or newer** (Tahoe 26 is best).
   If older: Apple menu → **System Settings → General → Software Update** and update first.
2. Open the **App Store** app on the Mac, search **Xcode**, click **Get / Install** (about 15 GB; keep 40 GB free).
   Apple only accepts apps built with **Xcode 26 or newer**.
3. Open Xcode once. Accept the licence. When it asks which platforms to download, tick **iOS** and click **Download & Install**.
4. Xcode menu → **Settings… → Accounts** → **+** → **Apple Account** → sign in with your developer Apple ID.
   You should see team **THE PMC MANAGERS LIMITED**.

### B2. Open the PMC Managers project
1. Download `PMC-Managers-iOS.zip` (link from PMC) and double-click it. A folder `PMC-Managers-iOS` appears.
   Move it to your **Documents** folder.
2. Open `Documents › PMC-Managers-iOS › ios › App` and double-click **App.xcodeproj**.
3. Wait until the top bar stops saying *Resolving Package Graph / Fetching…* (2–5 minutes the first time; needs internet).

### B3. Signing (one time)
1. In the left column click the blue **App** icon at the top. In the middle, under **TARGETS**, click **App**.
2. Open the **Signing & Capabilities** tab.
3. Tick **Automatically manage signing**. Team: choose **THE PMC MANAGERS LIMITED**.
4. Bundle Identifier must read `com.pmcmanagers.tenders`.
5. You should see a **Push Notifications** box below. If not: click **+ Capability** → double-click **Push Notifications**.
6. Red errors here usually disappear after 10 seconds; if one stays, click **Try Again**.

### B4. (Recommended) Try it on your own iPhone
1. Connect the iPhone with its cable. On the iPhone tap **Trust** and enter the passcode.
2. iPhone: **Settings → Privacy & Security → Developer Mode → On** (the phone restarts).
3. In Xcode's top bar, click the device name next to "App" and choose your iPhone. Press the **▶ (Run)** button.
4. The PMC Managers app opens on the phone. Try: sign in as a supplier, the ⚙ button (Face ID lock, alerts),
   the ⇪ share button, and turning on Airplane Mode (offline screen).

### B5. Upload to Apple
1. In the top bar device menu choose **Any iOS Device (arm64)**.
2. Menu **Product → Archive**. Wait 2–5 minutes; the **Organizer** window opens.
3. Select the new archive → **Distribute App** → **App Store Connect** → **Distribute** (keep all defaults; Xcode signs it).
4. When it says *Uploaded*, you are done on the Mac. Apple emails you within 10–30 minutes that the build is processed.

For the next version: in Signing & Capabilities' neighbour tab **General**, raise **Build** (2, 3, …) and, for bigger
changes, **Version** (1.0.1 …), then repeat B5.

---

## Part C — App Store Connect: test, fill in, submit

### C1. Quick test with TestFlight (same day, no review)
1. App Store Connect → **PMC Managers → TestFlight**. Your build appears (answer "None of the algorithms" if asked about
   encryption — the app already declares it uses no custom encryption).
2. **Internal Testing → +** → group `PMC team` → add yourself and colleagues (they must be users in **Users and Access**).
3. Install the **TestFlight** app from the App Store on the iPhone, open the invite, tap **Install**.
4. If everything works, submit to the public straight away (C2–C4). There is no need to wait longer.

### C2. App information (left menu **App Information**)
- Subtitle: `Global tenders, sealed & proven`
- Category: **Business** · Secondary: **Productivity**
- Content Rights: **Does not contain third-party content** (tenders from public sources show their source) → choose as appropriate.
- Age rating → **Edit** → answer **None / No** to everything → result 4+.

### C3. Pricing, privacy
- **Pricing and Availability**: Price **Free** (USD 0), all countries.
- **App Privacy** → Privacy Policy URL: `https://www.pmcmanagers.com/privacy` → **Get Started** → *Yes, we collect data*:
  - Contact Info: **Name, Email Address, Phone Number** — App Functionality — Linked to user — Not used for tracking.
  - User Content: **Other User Content** (bids, documents) — App Functionality — Linked — No tracking.
  - Identifiers: **User ID** — App Functionality — Linked — No tracking.
  - Financial Info: **Payment Info** only if suppliers pay fees in the app (payments run through Stripe on the website) — App Functionality — Linked — No tracking.
  - Publish.

### C4. Version page (**iOS App → 1.0 Prepare for Submission**)
- **Screenshots → iPhone 6.9" Display**: drag in the 6 PNG files from `appstore/screenshots` in the zip (1290 × 2796).
- Promotional text, Description, Keywords: copy from `appstore/listing.txt` in the zip.
- Support URL `https://www.pmcmanagers.com/contact` · Marketing URL `https://www.pmcmanagers.com`
- Copyright: `2026 THE PMC MANAGERS LIMITED`
- **Build**: click **+** and choose build 1.0.0 (1).
- **App Review Information**: tick **Sign-in required** and give Apple a working **supplier** test account on the live site
  (create one yourself, e.g. `appreview@pmcmanagers.com`, complete its registration and approve it in the admin console).
  Paste the review notes from `appstore/listing.txt`. Contact: your name, phone, email.
- **Version Release**: *Automatically release this version*.
- Click **Add for Review** → **Submit for Review**. Apple usually answers in 1–3 days by email.

If Apple asks a question or rejects something, forward the message to PMC's developer — most fixes are on the website and
need no new upload.

---

## Part D — Turn on new-tender push alerts on the server

Push alerts stay switched off until the server has the key from A2. In **AWS Elastic Beanstalk → your backend environment →
Configuration → Updates, monitoring and logging → Environment properties**, add:

| Name | Value |
|---|---|
| `APNS_KEY_ID` | Key ID from A2 |
| `APNS_TEAM_ID` | Team ID from A2 |
| `APNS_BUNDLE_ID` | `com.pmcmanagers.tenders` |
| `APNS_KEY_P8` | open the `.p8` file in TextEdit and paste the whole text, including the BEGIN/END lines |
| `APNS_ENV` | `production` |

Click **Apply**. From then on, a supplier who signs in on the iPhone and allows notifications gets an alert every time a
new tender matches one of their saved alerts (tapping it opens the alert list).
(Builds you run from Xcode straight onto your own phone use Apple's test server; set `APNS_ENV` to `sandbox` only while
testing that way. TestFlight and App Store installs use `production`.)
