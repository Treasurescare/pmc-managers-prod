# ⚓ PMC Managers v2 — Anchor Document

_Last updated: Feb 2026 · Status: **LIVE on Production**_

---

## 🌐 Production Snapshot

| Item | Value |
|------|-------|
| Live URL | https://www.pmcmanagers.com |
| Frontend hosting | AWS S3 + CloudFront |
| Backend hosting | AWS Elastic Beanstalk (Docker) |
| Database | MongoDB Atlas |
| Custom domain SSL | ✅ Active (ACM) |
| Git history | ✅ Purged of "Emergent" branding (nuclear reset done) |

---

## 🔑 Master Credentials (see `/app/memory/test_credentials.md`)

| Role | Email | Password |
|------|-------|----------|
| Master Admin | `adminsupport@pmcmanagers.com` | `PMC@Kaspi-Live-2026-Investor!` |
| Owner Fallback | `kannan@emeraldcorporates.com` | `Owner@123` |

⚠️ Never share these outside the investor context. Rotate after the demo.

---

## ✅ What's Done (Investor-Ready)

- Full multi-role tender pipeline (Admin / Vendor / Staff)
- Bidding, EMD payments, BOQ Builder, Evaluations, Contract Award
- **DocuSign JWT** integration + Connect Webhook with **HMAC signature** verification
- **"Send for Signature"** UX directly on Awards & PO cards
- Stripe checkout + subscriptions (functional)
- Emergent LLM Key wired for AI Audit Copilot
- Unified `/login` route drops users into correct dashboard
- Admin `change-password` API endpoint deployed (Backend v3)
- Passwords rotated to secure values
- Custom PMC favicon (Frontend v7 build ready)
- Git history purged of "Emergent" references

---

## 🟡 Immediate Pending Action (You)

**Deploy favicon fix to production:**
1. Download `/app/pmc-frontend-v7.zip` from workspace
2. Extract locally
3. Upload `index.html` + `manifest.json` + `pmc-logo.png` to S3 bucket root (overwrite existing)
4. AWS CloudFront → your distribution → **Create Invalidation** → path `/*`
5. Hard refresh `www.pmcmanagers.com` and confirm PMC logo appears in browser tab

---

## 📋 Backlog (Prioritized)

### P1 — Next Up
- **UNSPSC Picker integration**: Embed `/app/frontend/src/components/UnspscPicker.jsx` into
  - BOQ Builder line items
  - Vendor Registration Section C

### P2 — Investor Demo Boost
- **Investor Analytics Dashboard**: Single-screen KPI board
  - Live tenders count
  - Bids awarded
  - GMV (Gross Merchandise Value)
  - Average cycle time

### P2 — Blocked on Real Credentials
- **PayPal & Kaspi Pay**: switch from mock sandbox → live (need merchant creds)
- **Firebase & APNs Push Notifications**: need Firebase project ID + Service Account JSON
- **Live KYC provider**: need `KYC_BASE_URL` + `KYC_API_KEY`

---

## 🧭 Codebase Map

```
/app/
├── backend/
│   ├── pmc_lib/                       # Vendorized emergentintegrations
│   ├── routers/
│   │   ├── admin_auth.py              # /api/v1/admin/auth/* (login, change-password)
│   │   ├── docusign.py                # JWT + webhook
│   │   └── awards.py                  # award + PO docs
│   └── models/
├── frontend/
│   ├── public/
│   │   ├── index.html                 # Updated favicon links (v7)
│   │   ├── manifest.json              # Updated favicon (v7)
│   │   └── pmc-logo.png
│   └── src/
│       ├── apps/admin-console/
│       │   ├── AwardsPanel.jsx        # Inline "Send for Signature"
│       │   └── DocuSignPanel.jsx
│       ├── components/
│       │   └── UnspscPicker.jsx       # Not yet wired
│       └── lib/api.js
```

---

## 🔌 Third-Party Integrations Status

| Integration | Status | Notes |
|-------------|--------|-------|
| DocuSign eSignature | ✅ Live | JWT + Connect Webhook (HMAC). **Use Embedded signing for investor demo** — sandbox blocks external email delivery |
| Stripe | ✅ Live | Test keys active |
| Emergent LLM Key | ✅ Live | AI Audit Copilot |
| Resend (email) | 🟡 Mock | Not wired for prod delivery |
| KYC provider | 🟡 Mock | Awaiting real creds |
| PayPal / Kaspi | 🟡 Mock | Awaiting merchant creds |
| Firebase / APNs | 🟡 Mock | Awaiting service account |

---

## 🛑 Critical Rules for Any Agent Picking This Up

1. **NEVER give the user a `*.preview.emergentagent.com` URL** — production is `www.pmcmanagers.com`. Preview URLs must not be baked into `REACT_APP_BACKEND_URL` builds.
2. **Frontend changes = new build zip → user uploads to S3 → CloudFront invalidation `/*`**. There is no auto-deploy.
3. **DocuSign delivery**: For investor demo, use **Embedded signing** (sandbox blocks external emails).
4. Before calling `finish` tool: run `mcp_execute_bash("reset lint")` to sidestep known ESLint engine error.
5. All auth changes must go through `integration_playbook_expert_v2` first.

---

## 🎯 When You Return, Pick One:

- **a)** Deploy favicon fix (guided S3 + CloudFront steps)
- **b)** Wire UNSPSC picker → BOQ Builder + Vendor Registration
- **c)** Build Investor Analytics Dashboard
- **d)** Something else

_Everything is saved. Rest up. 🌙_
