# GOOGLE PLAY CONSOLE SIGN-UP — FIELD-BY-FIELD CHEAT SHEET
**Walk through this with the signup page open side-by-side.**  
URL: **https://play.google.com/console/signup**  
Signed in as: `managerspmc@gmail.com`

---

## BEFORE YOU START (5 min)

Open 4 tabs in Chrome:

1. **https://myaccount.google.com/security** → confirm **2-Step Verification = On**. If it says Off, click → **Phone number** → add your mobile → verify SMS → **Turn on**. Google will refuse your Play signup without this.
2. **https://find-and-update.company-information.service.gov.uk/company/17031540** → click **Filing history** tab → find the "Incorporation" row → **View PDF** → download it. Rename to `PMC_Companies_House_Incorporation.pdf`.
3. **Business proof-of-address document** — any one of:
   - Utility bill (gas, electricity, water, internet) addressed to **THE PMC MANAGERS LTD** at **Chiswick Park, London, W4 5YG**, dated within the last 12 months.
   - Bank statement / HMRC letter / commercial lease to the same company+address.
   - Save as `PMC_Proof_of_Address.pdf`.
4. **Photo ID** of the person signing up — passport data page **or** UK driving licence (front + back). Clear picture, all 4 corners visible, no glare. Save as `Representative_PhotoID.jpg`.

Put all three files on your Desktop in a folder called `PMC_PlayStore_Docs/`.

---

## PAGE 1 — "Account type"

| Choice | Click |
|---|---|
| **An organization / business** card | ✅ **Get started** |

---

## PAGE 2 — "Public developer profile"

Google will show you *"How you'll appear to users on Google Play"*.

| Field | Enter |
|---|---|
| Developer name | `PMC Managers` |
| Email address | `managerspmc@gmail.com` *(Google will send a verification email with a 6-digit code — paste that back in)* |
| Phone number | Your official PMC phone with country code, e.g. `+44 20 XXXX XXXX` *(Google will send a verification SMS)* |
| Website | `https://pmcmanagers.com` *(must open without redirect — test it)* |

Click **Next**.

---

## PAGE 3 — "Organization details"

| Field | Enter |
|---|---|
| Organization name | `THE PMC MANAGERS LTD` *(exact letter-for-letter — the D&B record is in all caps)* |
| Organization type | **Business / Commercial** |
| Organization size | 1 – 10 employees |
| Country / region | United Kingdom |
| Street address line 1 | Chiswick Park |
| Street address line 2 | *(leave blank)* |
| City | London |
| State / province / region | England |
| Postal code | W4 5YG |
| Phone number | Same official PMC phone as Page 2 |
| D-U-N-S number | `234578668` |

> ⚠️ Google calls Dun & Bradstreet in real time. If you see **"We couldn't verify your organization"**:
> - Make sure the organization name is *exactly* `THE PMC MANAGERS LTD` (all caps, no "Limited").
> - If the D-U-N-S was issued in the last 48 hours, wait a day and retry — D&B hasn't synced to Google yet.

Click **Next**.

---

## PAGE 4 — "How you plan to use your account"

| Question | Answer |
|---|---|
| Have you published Android apps before? | **No** |
| Will you charge for apps or offer in-app purchases? | **No** |
| Are your apps mainly intended for children under 13? | **No** |
| Will your apps show ads? | **No** |

Click **Next**.

---

## PAGE 5 — "Confirm and accept"

- Scroll to the bottom of the **Google Play Developer Distribution Agreement**.
- Tick ✅ *"I agree and I confirm that my use of the Google Play Developer Console..."*
- Tick ✅ *"I confirm that I am over the age of 18 and acknowledge..."*
- Tick ✅ *"I accept the US export laws."*
- Click **Create account and pay**.

---

## PAGE 6 — Payment ($25 one-time, non-refundable)

Google re-directs to Google Pay. If this is the first time this Gmail account is paying for anything on Google:

| Field | Enter |
|---|---|
| Country | United Kingdom |
| Account type | **Business** |
| Legal name & address | THE PMC MANAGERS LTD, Chiswick Park, London, W4 5YG |
| Primary contact | *(authorised rep's name and the official PMC phone)* |
| Card | Visa / Mastercard / Amex — company card preferred, personal card also accepted |

Click **Save** → **Pay $25.00**.

A confirmation email lands in `managerspmc@gmail.com` with the receipt — keep it for accounting.

---

## PAGE 7 — Identity verification

Immediately after payment Google shows **"Verify your identity"** with 3 upload boxes:

| Box | File to upload |
|---|---|
| **Proof of your organization** | `PMC_Companies_House_Incorporation.pdf` |
| **Proof of your business address** | `PMC_Proof_of_Address.pdf` |
| **Government-issued photo ID of the authorised representative** | `Representative_PhotoID.jpg` |

Each file must be < 10 MB, clear, un-cropped, and in the name of either the organization or the authorised rep.

Click **Submit**.

---

## WHAT HAPPENS NEXT

- **Immediate:** Google shows *"We're reviewing your account — this usually takes 2 working days."* and emails `managerspmc@gmail.com`.
- **1–2 days:** Google may email you asking for one additional document (e.g., a clearer address proof). Reply inside their portal, do not reply from the normal inbox.
- **2–4 days:** You receive *"Your Google Play developer account is verified."* 🎉
- **Same day:** You can start creating the PMC Managers app listing in Play Console.

> 💡 **While waiting**, you can already open **https://play.google.com/console → All apps → Create app** and prefill the metadata (app name, default language, Free app, declarations). The system lets you save drafts; "Submit for review" simply stays greyed out until verification completes.

---

## IF IDENTITY VERIFICATION FAILS

Common reasons & fixes:

| Reason | Fix |
|---|---|
| Blurry ID scan | Re-shoot in bright daylight, show all 4 corners |
| Address proof > 12 months old | Request a fresh HMRC letter or recent utility bill |
| Address proof shows personal name only | Google needs the document to show "THE PMC MANAGERS LTD" — ask the utility provider to re-issue with company name, or use the lease agreement |
| D&B record mismatch | Ensure organization name matches 234578668's D&B record *exactly* |
| Website redirects to a parking page | Point `pmcmanagers.com` to the live PMC site before resubmitting |

You can resubmit documents directly from the Play Console email link — Google re-reviews within 1–2 days.

---

## WHEN APPROVED — PING ME

The moment Google emails `managerspmc@gmail.com` with *"verified"*:
1. I'll finalise the `.aab` build process and give you the exact Play Console upload path (Internal testing → Closed testing → Production).
2. We'll complete the Data Safety questionnaire, the Content Rating survey, and the Privacy Policy / Account Deletion links together.
3. First production release target: ~1 week after account approval.
