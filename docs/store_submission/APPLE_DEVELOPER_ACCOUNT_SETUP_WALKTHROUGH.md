# APPLE DEVELOPER PROGRAM — ORGANIZATION ACCOUNT SETUP (STEP-BY-STEP)
**For:** THE PMC MANAGERS LTD  
**Account email:** managerspmc@gmail.com  
**D-U-N-S:** 234578668  
**UK Company No.:** 17031540  
**Registered Office:** Chiswick Park, London, England, W4 5YG

---

## 📋 BEFORE YOU START — HAVE THESE READY

1. **Apple ID** for `managerspmc@gmail.com` (same email as Google — fine).
2. **Two-Factor Authentication (2FA) enabled** on that Apple ID — Apple rejects enrolment otherwise. See https://support.apple.com/en-gb/HT204915.
3. **A trusted iPhone / iPad / Mac** signed into that Apple ID *(2FA codes land there or via SMS)*.
4. **Payment method:** Visa / Mastercard / Amex. Fee is **$99 USD / year** (≈ £79) and auto-renews.
5. **Companies House docs** for 17031540 — same PDF used for Google.
6. **Legal binding authority** — a Director, or a signed authorisation letter from one. Apple **will phone-verify**.
7. **Corporate phone number** for THE PMC MANAGERS LTD — Apple's enrolment team calls this number.
8. **Website:** `https://pmcmanagers.com` live over HTTPS.

---

## STEP 1 — CREATE / CONFIRM YOUR APPLE ID

1. Go to **https://appleid.apple.com** → sign in with `managerspmc@gmail.com`.  
   *(If it's never been used as an Apple ID, click "Create your Apple ID" first and verify the email + phone.)*
2. Under **Sign-In and Security** → **Two-Factor Authentication = On**.
3. Under **Personal Information** → set the name to the authorised representative's **real legal name as it appears on their passport** — Apple matches this against Companies House.

---

## STEP 2 — START THE ENROLMENT

1. Open Safari or Chrome: **https://developer.apple.com/programs/enroll/**
2. Click **Start Your Enrollment** at the bottom.
3. Sign in with `managerspmc@gmail.com` + 2FA.
4. Entity Type → ✅ **Company / Organization** *(not Individual, Government, or Non-profit)* → **Continue**.

---

## STEP 3 — AUTHORISED REPRESENTATIVE DETAILS

| Field | Value |
|---|---|
| Legal first name | *(as on passport)* |
| Legal last name | *(as on passport)* |
| Work email | `managerspmc@gmail.com` *(or `admin@pmcmanagers.com` once live)* |
| Country / Region | **United Kingdom** |
| Signing authority | **Yes — I have the legal authority to bind my company** *(if you're a Director; otherwise select **No** and nominate a Director — Apple routes it to them for signature.)* |

Click **Continue**.

---

## STEP 4 — ORGANIZATION DETAILS

| Field | Value |
|---|---|
| Legal entity name | `THE PMC MANAGERS LTD` *(exact D&B casing, no "Limited")* |
| D-U-N-S Number | `234578668` |
| HQ Street | Chiswick Park |
| City | London |
| State / Province | England |
| Postal code | W4 5YG |
| Country | United Kingdom |
| HQ phone | *(official PMC number with `+44`)* |
| Website URL | `https://pmcmanagers.com` |

Click **Continue**.

> Apple queries D&B instantly. If it says *"we can't find your organization"*:
> - Check spelling: `THE PMC MANAGERS LTD` all caps, no "Limited".
> - Verify at **https://developer.apple.com/enroll/duns-lookup/** with the same name & address.
> - Freshly-issued D-U-N-S? Wait 24–48 h for D&B → Apple sync, then retry.

---

## STEP 5 — AGREEMENTS

- Tick ✅ Apple Developer Agreement.
- Tick ✅ Representative is authorised to bind the organization.
- **Continue**.

---

## STEP 6 — APPLE REVIEW CALL (NORMAL)

Within **1–3 business days** Apple's enrolment team will:
1. Email `managerspmc@gmail.com` a case number.
2. **Phone the corporate number** from Step 4 and ask for the signing authority.
3. Confirm:
   - You are a legal representative of THE PMC MANAGERS LTD.
   - You personally authorised the enrolment.
   - D-U-N-S, address, website all match.
4. They may request the Certificate of Incorporation PDF.

> 📞 **Pro-tip:** Apple's call appears from a US number. Pick up every unknown call for 3–4 business days — miss them and the case silently closes after ~2 weeks.

---

## STEP 7 — PAY THE $99 ANNUAL FEE

After identity approval:
1. Email arrives: *"You can now purchase your Apple Developer Program membership."*
2. Click **Complete Your Enrollment**.
3. Pay **$99 USD / year** (auto-renews).
4. Within ~24 h you'll see **App Store Connect** (https://appstoreconnect.apple.com) with **Account Holder = THE PMC MANAGERS LTD**.

---

## STEP 8 — INITIAL APP STORE CONNECT SETUP

1. Sign in: **https://appstoreconnect.apple.com**.
2. **Users and Access** → add teammates with scoped roles (Developer, App Manager, Marketing). `managerspmc@gmail.com` stays Account Holder.
3. **Agreements, Tax, and Banking**:
   - Accept the **Free Apps Agreement** (required to publish *any* app, even free).
   - **Tax forms** → **W-8BEN-E** for UK Ltd.
   - **Banking** — only needed for paid / IAP apps; safer to fill now.
4. **My Apps → ➕ New App**:
   - Platform: **iOS**
   - Name: `PMC Managers`
   - Primary language: English (U.K.)
   - Bundle ID: `com.pmcmanagers.tenders` *(registered via Xcode once the native build is ready)*
   - SKU: `pmc-tenders-ios-001`
   - User Access: Full Access

---

## ⚠️ COMMON ENROLMENT PITFALLS

1. **No 2FA on Apple ID** → enrolment refuses to start. Fix at appleid.apple.com first.
2. **Entity name typo** → "PMC Managers Ltd" ≠ "THE PMC MANAGERS LTD". Match D&B casing.
3. **Missed verification call** → case closes after ~2 weeks. Re-open via https://developer.apple.com/contact/.
4. **No signing authority** → nominate a Director; Apple routes to them.
5. **Personal name mismatch** → the Apple ID's legal name must match your passport. Rename at appleid.apple.com first.
6. **Parking-page website** → `https://pmcmanagers.com` must load real PMC content.

---

## ✅ WHEN APPROVAL LANDS

Email `managerspmc@gmail.com` with *"Welcome to Apple Developer Program"*. Ping me and I'll:
1. Register the App ID `com.pmcmanagers.tenders` in your account.
2. Generate the Distribution Certificate + Provisioning Profile.
3. Walk you through Archive → TestFlight → App Store review.
