# PMC Managers — Mobile Store Assets v1.0.0

**Legal entity:** THE PMC MANAGERS LTD (D-U-N-S 234578668)
**App ID:** `com.pmcmanagers.tenders`
**Bundle:** `pmc-mobile-store-assets-v1.0.0.zip` (download below)
**Palette:** Forest green `#0b3d2e` • Navy `#0b1e3f` • Brass gold `#d4af37` • Warm white `#f6e8c8`

Direct URL (preview-hosted):
`https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-mobile-store-assets-v1.0.0.zip`

---

## 🎨 Brand Assets

| File | Dimensions | Where to use |
|---|---|---|
| `icon_1024.png` | 1024×1024 PNG | iOS App Store icon slot; Google Play **high-res icon** slot (both stores round the corners automatically — do not pre-round). |
| `splash_portrait.png` | 1290×2796 PNG | iOS Launch Screen (`Assets.xcassets/Splash.imageset`); Android splash screen (`res/drawable/splash.png`). |
| `android_feature_1024x500.png` | 1024×500 PNG | Google Play **Feature Graphic** (mandatory). |

> If any asset needs a tweak (different wordmark, replace monogram, etc.) rerun `python3 /app/scripts/generate_app_icons.py` after editing the prompt in that script.

---

## 📱 Store Screenshots (4 flows × 2 device sizes = 8 shots)

### iPhone 6.7" — upload to **App Store Connect → App Information → iOS 6.7-Inch Display**
Resolution 1290×2796 (iPhone 15 Pro Max / 16 Pro Max portrait).

1. `ios_6_7_public_tenders.png` — Public tender notice board with filters & indicative budgets.
2. `ios_6_7_vendor_dashboard.png` — Supplier portal "Good morning, Manual Preview Vendor Ltd" with KYC-verified status and 5 active bids.
3. `ios_6_7_admin_dashboard.png` — Procurement overview with pipeline, EMD collected, approvals queue, audit stream.
4. `ios_6_7_reverse_auction.png` — Reverse auction console with saved views, draft readiness badges (0/2, 1/2), live auction CTA.

Optional 5th screenshot already captured for marketing contrast:
`ios_6_7_home.png` — "Tenders you can prove" marketing hero + live board.

### Android Phone — upload to **Play Console → Store listing → Phone screenshots**
Resolution 1080×2400 (Pixel 6-class portrait).

1. `android_phone_public_tenders.png`
2. `android_phone_vendor_dashboard.png`
3. `android_phone_admin_dashboard.png`
4. `android_phone_reverse_auction.png`

Optional marketing shot:
`android_phone_for_suppliers.png` — "Win work on a board that plays fair" + 4-step walkthrough.

---

## ⬆️ Upload Order for each store

### Apple App Store Connect
1. **App Information** → add Name `PMC Managers`, Subtitle `Tenders, Bidding & Escrow Portal`.
2. **App Store** tab → "iPhone 6.7-Inch Display" slot → drag the 4 `ios_6_7_*.png` files in the order listed above.
3. **App Icon** inside Xcode build (Assets.xcassets → AppIcon → 1024×1024 slot) → use `icon_1024.png`.
4. **Launch Screen** inside Xcode (Assets.xcassets → Splash) → use `splash_portrait.png`.

### Google Play Console
1. **Main store listing**
   - App icon: `icon_1024.png`
   - Feature graphic: `android_feature_1024x500.png`
   - Phone screenshots: drag the 4 `android_phone_*.png`.
2. **Grow → Store presence → Store listing experiments** can run A/B tests on these later.

---

## 🖼️ Preview thumbnails (what each shot looks like)

### Brand marks
- `icon_1024.png` → brass PM monogram with thin gold ring on a navy→forest radial gradient.
- `splash_portrait.png` → centred PM seal, "PMC MANAGERS" wordmark, "GLOBAL PROCUREMENT" small caps.
- `android_feature_1024x500.png` → "PMC MANAGERS" brass wordmark with Procurement • Tenders • Reverse Auctions • Escrow strapline + floating seal.

### UI screens all captured against live preview data
(see individual files for pixel-perfect previews).

---

## 🔁 How to regenerate everything

```bash
# React build (if the UI has changed since last capture)
cd /app/frontend
GENERATE_SOURCEMAP=false yarn build

# Brand icons
python3 /app/scripts/generate_app_icons.py

# Screenshots — rerun each mcp_screenshot_tool script in /app/docs/store_submission/
# or ask the dev agent to recapture a specific screen.
```
