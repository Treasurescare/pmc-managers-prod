# ⚓ PMC Managers v2 — Anchor Document

_Last updated: Feb 17, 2026 · Status: **LIVE on Production, v4b/v8c**_

---

## 🌐 Production Snapshot

| Item | Value |
|------|-------|
| Live URL | https://www.pmcmanagers.com |
| Frontend | AWS S3 (`pmc-managers-frontend-prod`) + CloudFront |
| Backend | AWS Elastic Beanstalk env `pmc-backend-prod` (Docker, EU-West-2) |
| Database | MongoDB Atlas |
| Currently deployed | Backend **v4b-docker-fix** · Frontend **v8c-header-cleanup** |
| Custom domain SSL | ✅ Active |
| Git history | ✅ Purged of Emergent branding |

---

## 🔑 Master Credentials (see `/app/memory/test_credentials.md`)

| Role | Email | Password |
|------|-------|----------|
| Master Admin | `adminsupport@pmcmanagers.com` | **`Admin@12345`** (temp — rotate after final demo) |
| Owner Fallback | `kannan@emeraldcorporates.com` | `Owner@123` |

⚠️ Rotate `Admin@12345` before real go-live — it's a testing-only password.

---

## ✅ Session Feb 17, 2026 — What was shipped

### 🔧 New self-service features (deployed end-to-end)
- **Personal avatar upload** — admin + vendor. Data-URL, client-side resized to 256×256, ≤350 KB. New API: `/api/v1/{admin|vendor}/auth/avatar` (POST + DELETE).
- **Change password modal** — reused existing backend endpoints. Photo + Password tabs.
- **Tenant portal logo upload** — new admin tab **Portal Branding**. Replaces PMC "P" mark in the top-left with tenant logo. API: `/api/v1/tenants/{id}/logo` (POST + DELETE).
- **Forgot username** — public modal with two tabs:
  1. **Look me up** by phone or company → returns MASKED email hint.
  2. **Ask an admin** → creates a Help Request ticket.
  - Backend: `POST /api/v1/auth/username-lookup`, `POST /api/v1/auth/help-request`.
- **Help Requests admin tab** — see + resolve all incoming help tickets.

### 🎨 UI hygiene
- **Language switcher** → globe-icon dropdown (English / Русский / Қазақша) instead of 3 crammed buttons.
- **TopBar cleanup** — hides public-nav links AND removes duplicate "Sign out" when inside `/admin`, `/staff` or `/vendor` routes.

### 🔐 Ops
- Admin password rotated to `Admin@12345` on both LOCAL and PROD.
- Backend v4 initial deploy failed (missing Dockerfile) → **v4b** rebuilt with Dockerfile + Dockerrun.aws.json at zip root → deploys cleanly.
- Frontend v8 initial deploy pointed at wrong URL (preview URL baked in) → **v8b** rebuilt with `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com` override → **v8c** finalised with header cleanup.
- Emergency download route (`/api/v1/_dl/<token>`) built to bypass Emergent's plan-paywall for zip downloads — **REMOVED from codebase after deploy**.

---

## 📚 Deliverables produced this session

Location: `/app/deliverables/`

| File | Size | Purpose |
|------|------|---------|
| `PMC_Investor_Deck.docx` | 613 KB | 12-section investor deck (Word) |
| `PMC_Investor_Deck.pdf` | 553 KB | Same, PDF |
| `PMC_Trainee_Manual.docx` | 1.6 MB | 25-chapter illustrated handbook with real screenshots |
| `PMC_Trainee_Manual.pdf` | 2.0 MB | Same, PDF |

---

## 📋 Backlog for tomorrow

### 🟡 P1 — Next Up
- **UNSPSC picker integration** — wire `/app/frontend/src/components/UnspscPicker.jsx` into BOQ Builder line items + Vendor Registration Section C.
- **Investor Analytics Dashboard** — KPI board (live tenders, bids awarded, GMV, avg cycle time) for max demo impact.
- **Wire Resend email delivery** — enables real forgot-password flow (currently only forgot-username works).

### 🔵 P2 — Blocked on External Creds
- PayPal & Kaspi Pay live activation
- Firebase / APNs push notifications
- Live KYC provider

### 🎨 Optional polish
- Rotate `Admin@12345` back to a strong password
- Vendor-facing training manual (mirror of trainee manual from vendor's perspective)
- Screen-recording narration script (chapter by chapter, for a Loom walkthrough)

---

## 🧭 Codebase Map

```
/app/
├── backend/
│   ├── routers/
│   │   ├── admin_auth.py          # /me now returns avatar_data_url
│   │   ├── vendor_auth.py         # /me now returns avatar_data_url
│   │   ├── profile_ops.py         # NEW — avatars, tenant logos, help requests, username-lookup
│   │   ├── tenants.py             # public endpoints now return logo_data_url
│   │   ├── docusign.py            # JWT + Connect Webhook (HMAC)
│   │   └── awards.py              # Send-for-signature UX
│   ├── models/
│   └── server.py                  # profile_ops router registered
├── frontend/
│   ├── public/                    # index.html + pmc-logo.png favicon
│   └── src/apps/
│       ├── shared/
│       │   ├── ProfileModal.jsx           # NEW — avatar + change password
│       │   ├── ForgotUsernameModal.jsx    # NEW — lookup + help request
│       │   ├── LangSwitcher.jsx           # rewritten as dropdown
│       │   ├── TopBar.jsx                 # hides duplicates on dashboards
│       │   └── PmcLogo.jsx                # accepts tenant logo src
│       ├── admin-console/
│       │   ├── AdminDashboard.jsx         # + Help + Branding tabs, avatar chip, ProfileModal
│       │   ├── HelpRequestsPanel.jsx      # NEW
│       │   └── BrandingPanel.jsx          # NEW
│       └── vendor-portal/
│           └── VendorDashboard.jsx        # + avatar chip + ProfileModal
```

---

## 🔒 Critical Rules for the Next Agent

1. **NEVER expose `*.preview.emergentagent.com` URLs to the user.** Production is `www.pmcmanagers.com`.
2. **Frontend deploys are manual** — build zip → S3 → CloudFront `/*` invalidation.
3. **Always build with `REACT_APP_BACKEND_URL=https://www.pmcmanagers.com yarn build`** (the `.env` value is for local preview only).
4. **Backend zip MUST have `Dockerfile` + `Dockerrun.aws.json` at ZIP root**, with `backend/` as a subfolder. Otherwise EB deployment fails with "missing Dockerfile".
5. **Before final zip, verify with `unzip -l` that no `_temp_downloads.py` or dev routers ship to prod.**
6. **DocuSign delivery**: use **Embedded** signing for investor demo (sandbox blocks external emails).
7. Before calling `finish`: `mcp_execute_bash("reset lint")` if the JavaScript linter error appears.
8. Auth changes must go through `integration_playbook_expert_v2` first.

---

## 🎯 When You Return Tomorrow

Pick one:
- **a)** UNSPSC picker → BOQ + Vendor Registration (P1)
- **b)** Investor Analytics Dashboard KPI board (P1)
- **c)** Wire Resend for forgot-password (P1)
- **d)** Something new the user brings

Everything's saved. Sweet dreams 🌙
