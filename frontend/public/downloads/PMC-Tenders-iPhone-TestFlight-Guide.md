# PMC Tenders — iPhone test app (TestFlight)

The iPhone app opens https://pmcmanagers.com inside a native app, the same as the Android app.
Apple only accepts apps built on a Mac with Xcode, so this last step happens on a Mac.

## What you need
1. An Apple Developer account in the company's name — https://developer.apple.com/programs/ (USD 99 a year; company enrolment needs a D-U-N-S number).
2. A Mac with the latest Xcode (free from the Mac App Store).

## Steps (about 1 hour the first time)
1. Download `PMC-Tenders-iOS-project.zip` and unzip it on the Mac.
2. In Terminal, inside the unzipped folder: `npm install` then `npx cap open ios` (Xcode opens).
3. In Xcode select the **App** target → **Signing & Capabilities** → tick *Automatically manage signing* → choose your team.
   Bundle identifier: `com.pmcmanagers.tenders`.
4. In App Store Connect (https://appstoreconnect.apple.com) → **Apps** → **+** → New App → same bundle ID, name "PMC Tenders".
5. Back in Xcode: choose *Any iOS Device* → **Product → Archive** → **Distribute App → App Store Connect → Upload**.
6. In App Store Connect → your app → **TestFlight**:
   - Add up to 100 people from your team as *internal testers* straight away, or
   - Create an *external* group (up to 10,000 people). The first build gets a short Apple review (usually 1–2 days), then you share a public invite link.
7. Testers install the free **TestFlight** app from the App Store and open your link.

Each TestFlight build works for 90 days. Because the app shows the live website, website updates appear without a new build.
