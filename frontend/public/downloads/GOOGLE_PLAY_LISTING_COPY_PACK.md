# PMC Managers — Google Play Store Listing Copy Pack v1.0.0
**Paste-ready copy for every field in Play Console. Date: 2026-10-09**

---

## 1. CREATE APP (first dialog)

| Field | Paste this |
|---|---|
| App name | `PMC Managers — Tender & EMD Escrow` |
| Default language | English (United States) |
| App or game | App |
| Free or paid | Free |
| Declarations | ✅ Play App Signing (accept) · ✅ Developer Program Policies · ✅ US export laws |

---

## 2. MAIN STORE LISTING (Grow → Store presence → Main store listing)

**Short description** (max 80 chars):
```
Government-grade tender bidding with dual-signature EMD escrow protection
```
(79 chars ✓)

**Full description** (max 4000 chars):
```
PMC Managers is the sovereign procurement platform where government project managers publish tenders and suppliers bid with legally binding, escrow-protected EMD (Earnest Money Deposit) handling.

FOR SUPPLIERS
• Browse live public tenders across infrastructure, services and works
• Purchase tender packs and download official NIT documents instantly
• Submit two-envelope digital bids (technical + commercial) with document verification
• Pay EMD securely through Stripe — funds are held in regulated joint escrow accounts, never touched by either party alone
• Join live reverse auctions when invited
• Sign contracts digitally via DocuSign
• Track bid status end-to-end: submission → EMD clearance → technical evaluation → financial opening → award

FOR PROJECT MANAGEMENT TEAMS
• Publish tender notices with configurable deadlines, categories and corrigenda
• Automatic bid-level EMD reconciliation against escrow bank statements
• Committee-based technical evaluation with weighted scoring rubrics
• One-click L1 comparison reports for award decisions
• Dual-signature escrow release — PMC officer AND escrow institution must both sign before any EMD moves
• Full audit trail on every action, exportable for compliance reviews

FOR ESCROW INSTITUTIONS (BANKS & TRUSTEES)
• Dedicated institution portal with KYC registration
• Joint-account dashboard showing every pending EMD transaction
• Digital sign-off workflow with release/refund/forfeit controls
• Automated licence-expiry compliance reminders

SECURITY & COMPLIANCE
• Every payment held in dual-control escrow — no unilateral withdrawals
• Immutable audit ledger on bids, payments, signatures and releases
• Role-based access: public, supplier, staff, admin, escrow institution
• OTP-verified contact details and document-checked vendor onboarding

Built for transparency. Built for trust. Built for public procurement that stands up to audit.

Questions? Contact support@pmcmanagers.com
```

**App icon**: `mobile_assets/icon_1024.png` (from the assets zip)

**Feature graphic** (1024×500): `mobile_assets/android_feature_1024x500.png`

**Phone screenshots** (upload in this order — order matters, it's the story):
1. `android_phone_public_tenders.jpg`
2. `android_phone_for_suppliers.jpg`
3. `android_phone_vendor_dashboard.jpg`
4. `android_phone_reverse_auction.jpg`
5. `android_phone_admin_dashboard.jpg`

**Category**: Business
**Tags**: procurement, tenders, escrow, bidding
**Contact email**: `support@pmcmanagers.com`
**Website**: `https://pmcmanagers.com`
**Privacy policy URL** (required): `https://pmcmanagers.com/privacy`

---

## 3. APP CONTENT (Policy → App content)

**Privacy policy**: URL above → Save

**Ads**: ❌ "No, my app does not contain ads"

**App access** (critical — reviewers reject without this):
- Select: "All or some functionality is restricted"
- Add instructions:
```
Demo supplier login:
Email: manualvendor@pmcmanagers.com
Password: Vendor@12345
(see /app/memory/test_credentials.md for the current values — confirm before submitting)

Demo admin login:
Email: kannan@emeraldcorporates.com
Password: Owner@123

Steps: Open app → tap Supplier → sign in with demo credentials →
browse tenders → open any published tender → view bid workspace.
Admin flows: sign in via Admin role on the same login screen.
```

**Content ratings** (questionnaire):
- Category: Utility, Productivity, Communication → Business
- Violence: None
- Sexual content: None
- Profanity: None
- Controlled substances: None
- User-generated content: ❌ No (bids are structured form data, not UGC)
- Result: Everyone / PEGI 3 equivalent

**Target audience**: Adults 18+ (it's a B2B financial app — do NOT select under-18; that triggers extra policy review)
- "App is directed at children": ❌ No

**Data safety** (Policy → App content → Data safety):
| Question | Answer |
|---|---|
| Collect or share user data? | Yes, collect only |
| Email address | Collected · Required · App functionality, account management · Encrypted in transit · Users can't request deletion (financial record retention) — mark as "not deletable" with reason "legal/audit retention" |
| Name | Collected · Required · Same as above |
| Phone number | Collected · Optional · Account verification (OTP) |
| Financial info → Payment info | Collected · "Payments are processed by Stripe; the app stores only transaction references, never card numbers" |
| Photos/files | Collected · Optional · "Bid and KYC documents uploaded by the user" |
| Data shared with third parties? | Yes — Stripe (payments), DocuSign (contracts), Resend (email) |
| Encrypted in transit? | ✅ Yes |
| Deletable? | "Data cannot be deleted — financial audit retention" |

**News app**: ❌ No · **COVID app**: ❌ No

**Government app**: Select **"No, not a government app"** (unless PMC is a statutory body — if it IS government-affiliated, select Yes and provide the ministry letter)

---

## 4. SELECT COUNTRIES
All countries (or start with Kazakhstan + India + UAE where your suppliers are — you can expand later without resubmission).

---

## 5. RELEASE
**First submission path**: Production → Create new release → upload `app-release.aab`
- Release name: `1.0.0 initial`
- Release notes:
```
Initial release. Public tender browsing, two-envelope digital bidding,
escrow-protected EMD payments, live reverse auctions, DocuSign contract
signing and dual-signature escrow releases.
```
- Review → Send for review

---

## Signing note
When Play Console asks about **app signing**: choose **"Use Google-generated key"** (Play App Signing). Your local upload key signs the AAB; Google re-signs with the distribution key. If you ever lose your upload key, Google lets you reset it — this is the safe option.
