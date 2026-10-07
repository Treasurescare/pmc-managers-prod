# GOOGLE PLAY CONSOLE — ORGANIZATION ACCOUNT SETUP (STEP-BY-STEP)
**For:** THE PMC MANAGERS LTD  
**Account email:** managerspmc@gmail.com  
**D-U-N-S:** 234578668  
**UK Company No.:** 17031540  
**Registered Office:** Chiswick Park, London, England, W4 5YG

---

## 📋 BEFORE YOU START — HAVE THESE READY

1. **Google Account** signed in as `managerspmc@gmail.com` with 2-Step Verification **ON** (https://myaccount.google.com/security). Google *will* enforce this.
2. **Payment method** — international debit/credit card (Visa / Mastercard / Amex). Fee is **$25 USD one-time**.
3. **Government-issued photo ID** of the authorised representative (passport or UK driving licence — PNG/JPG, both sides if licence).
4. **Companies House Certificate of Incorporation** PDF for 17031540 (download it at https://find-and-update.company-information.service.gov.uk/company/17031540 → Filing history → "Incorporation").
5. **Business proof-of-address** dated within the last 12 months showing THE PMC MANAGERS LTD at Chiswick Park, W4 5YG (utility bill, bank statement, lease, or HMRC letter).
6. **Phone number** for THE PMC MANAGERS LTD that can receive SMS or voice calls.
7. **Public support email** — recommended `support@pmcmanagers.com`; falls back to `managerspmc@gmail.com` for now.
8. **Website:** `https://pmcmanagers.com` live over HTTPS.

---

## STEP 1 — SIGN IN

1. Open **Chrome** in **Incognito** (prevents conflicts with personal Google accounts).
2. Go to: **https://play.google.com/console/signup**
3. Click **Sign in** → use `managerspmc@gmail.com` → enter password → complete 2-Step Verification challenge.

> 💡 Later, share access via **"Users and permissions"** inside Play Console — never share the raw password.

---

## STEP 2 — CHOOSE ACCOUNT TYPE

Two cards appear:

| ❌ **An individual — for yourself** | ✅ **An organization — for business, company, partnership** |
|---|---|

Click **"An organization"** → **Get started**.

---

## STEP 3 — DEVELOPER ACCOUNT DETAILS

### 3a. About you
| Field | Value |
|---|---|
| Public developer name | `PMC Managers` *(shown under every app — keep it clean)* |
| Contact email | `support@pmcmanagers.com` *(or `managerspmc@gmail.com` if not yet live — Google verifies this)* |
| Contact phone | *(official PMC number with `+44`)* |
| Preferred language | English (United Kingdom) |

### 3b. About your organization
| Field | Value |
|---|---|
| Organization name | `THE PMC MANAGERS LTD` *(match Companies House letter-for-letter)* |
| Organization type | **Business / Commercial** |
| Organization size | 1–10 employees *(or current)* |
| Street 1 | Chiswick Park |
| City | London |
| State / Region | England |
| Postal code | W4 5YG |
| Country | United Kingdom |
| Organization phone | *(same official PMC number)* |
| Website | `https://pmcmanagers.com` |
| D-U-N-S number | `234578668` |

Click **Next**.

> ⚠️ Google immediately queries D&B. If it says *"we could not verify your organization"*: wait 24–48 h for D&B → Google sync, then retry. **Do not** alter the entity name to force a match.

---

## STEP 4 — HOW YOU PLAN TO USE PLAY CONSOLE

| Question | Answer |
|---|---|
| Will you sell apps or in-app products? | **No** *(PMC Managers is free — this skips Merchant setup; you can enable it later)* |
| Apps aimed mainly at children under 13? | **No** |
| Will your apps use ads? | **No** |
| Published Android apps before? | **No** |

Click **Next**.

---

## STEP 5 — AGREE TO DEVELOPER DISTRIBUTION AGREEMENT

- Tick ✅ Developer Distribution Agreement.
- Tick ✅ US export laws acknowledgment.
- Click **Create account and pay**.

---

## STEP 6 — PAY $25 ONE-TIME REGISTRATION FEE

- Billing name: **THE PMC MANAGERS LTD** (or the authorised representative).
- Billing address: Chiswick Park, London, England, W4 5YG, UK.
- Google charges **$25 USD** (≈ £19) once — non-refundable, lifetime of the account.
- Save the receipt email for accounting.

---

## STEP 7 — IDENTITY VERIFICATION (2023+ requirement)

Immediately after payment Google asks for documents. Upload each as PDF/PNG < 10 MB:

| Document | File |
|---|---|
| Proof of business registration | Companies House Certificate of Incorporation (17031540) |
| Proof of business address | Utility bill / bank statement / HMRC letter dated within 12 months, in the name of THE PMC MANAGERS LTD at Chiswick Park W4 5YG |
| Photo ID of authorised rep | Passport data page **or** UK driving licence (front + back) |
| Business email of authorised rep | `managerspmc@gmail.com` — Google emails a verification code |

Submit.

> ⏳ Review: **2–4 business days** (sometimes same-day). You can prepare the draft listing while waiting; publishing is blocked until verification completes.

---

## STEP 8 — WHILE WAITING: PRE-CREATE THE APP DRAFT

In Play Console → **All apps → Create app**:

| Field | Value |
|---|---|
| App name | `PMC Managers` |
| Default language | English (United Kingdom) – en-GB |
| App or game | **App** |
| Free or paid | **Free** |
| Declarations | Tick both: Program Policies + US export laws |

Then under **Policy → App content** prefill:
- **Privacy policy URL:** `https://pmcmanagers.com/privacy`
- **Target audience:** 18+
- **Content rating** → Business category; declare no violence, sexual content, drugs, gambling.
- **Data safety** → Collects: Email, Phone, Full Name, Government ID (vendor KYC), Payment info (handled by Stripe — not stored by the app), App activity. All transmitted via HTTPS/TLS. Users can request deletion via `https://pmcmanagers.com/account/delete-request`.
- **News app:** No
- **Government app:** No *(unless you want to flag it)*

Save each section — "Submit for review" stays greyed-out until every item is green.

---

## STEP 9 — INVITE TEAM (OPTIONAL)

**Users and permissions → Invite new users**. Grant minimum-permissions roles (*Release manager* for engineers, *Marketing* for store listing editors). Keep `managerspmc@gmail.com` as the root Owner so nobody else sees billing or legal.

---

## ⚠️ COMMON REJECTION REASONS

1. **D&B record mismatch** — must be `THE PMC MANAGERS LTD` exactly, not "PMC Managers" or "PMC Managers Limited".
2. **Address mismatch** — use the Chiswick Park, London, England, W4 5YG as registered with D&B.
3. **No 2-Step Verification** on the Gmail account → turn it on before signing up.
4. **Non-company proof of address** — a director's personal utility bill is rejected; the document must name THE PMC MANAGERS LTD.
5. **Blurry ID scan** — all four corners visible, no glare.
6. **Website not live** — `https://pmcmanagers.com` must open without errors or redirect to a parking page.

---

## ✅ WHEN VERIFICATION PASSES

Google emails `managerspmc@gmail.com`: *"Your Google Play developer account is verified."* Ping me and I'll:
1. Build the production `.aab` from Capacitor.
2. Walk you through Internal Testing → Closed Testing → Production rollout.
