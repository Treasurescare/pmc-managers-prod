# PMC Managers v2 — v44 AWS Deployment Guide

**Contents of the v44 drop**
```
pmc-v44/
├── pmc-frontend-v44-build.zip     → deploy to S3 + CloudFront
├── pmc-backend-v22h.zip           → deploy to Elastic Beanstalk (Docker)
├── deploy-frontend-v44.sh         → Linux/macOS bash deploy script
├── deploy-frontend-v44.ps1        → Windows PowerShell deploy script
├── deploy-backend-v22h.sh         → Linux/macOS bash deploy script
└── deploy-backend-v22h.ps1        → Windows PowerShell deploy script
```

Both zips are **AWS-ready**:
- `pmc-backend-v22h.zip` contains `Dockerfile` + `Dockerrun.aws.json` at the **absolute zip root** (verified via `unzip -l`) — Elastic Beanstalk Docker platform will pick them up on first parse.
- `pmc-frontend-v44-build.zip` is the raw `build/` output from `craco build` — `index.html` + `asset-manifest.json` + `manifest.json` + `static/` + `downloads/` all at the zip root.

---

## What v44 ships

### Frontend (bundle `main.45271923.js`, 305 kB gzip)
- **Admin Vendors panel — inline "Activate now" button** on every inactive vendor row (`data-testid=vendor-activate-<vendor_ref>`)
  - Green pill button visible under each inactive row (see it by clicking the **INACTIVE** filter chip)
  - `window.confirm` flow: **OK** → resend magic link, **Cancel** → admin enters a temp password (≥ 8 chars) and vendor is force-activated with `must_change_password=True`
- **Auto-scroll + emerald ring highlight (3.5 s fade)** on any vendor row that was just invited, activated or force-activated — newly-created vendors no longer feel like they "disappeared"
- **Registration flow — new "Directors · Beneficial Owners" tab** inserted between Section D and Section E
  - Dynamic add/remove rows (unlimited entries)
  - Fields: Full legal name, Role (Director / Shareholder / UBO / Officer / Other), Nationality, ID/Passport #, Ownership %, Residential address
  - **Submit gate**: at least one row with a non-empty `full_name` required. Reason surfaced inline (red text) + toast.
  - Localised in EN / RU / KK
- **Stepper CSS tightened** so the 6 steps wrap gracefully at every viewport

### Backend v22h (Elastic Beanstalk Docker)
- **`POST /api/v1/vendors/{vendor_ref}/activate`** (admin + CSRF)
  - `mode=resend_link` → regenerates magic token and re-emails the verify link
  - `mode=set_password` → force-activates immediately with an admin-supplied password (min 8 chars); flags `must_change_password=True`
- **Directors persistence** — `RegistrationUpdateIn.model_config = ConfigDict(extra="allow")` already accepts `reg.directors[]`; no schema migration required.
- No breaking changes on top of v22g.

---

## Step-by-step (Windows PowerShell)

Assumes your working dir is `C:\Users\abcd\pmcmanagers\` and AWS CLI is configured with the `pmc-admin` profile.

### 1. Download the two zips + deploy scripts (from the preview URL — production CloudFront returns SPA `index.html` for /downloads/* until they land)

```powershell
Set-Location C:\Users\abcd\pmcmanagers\
$base = 'https://pmc-forest-green.preview.emergentagent.com/downloads'
curl.exe -fSLo pmc-frontend-v44-build.zip  "$base/pmc-frontend-v44-build.zip"
curl.exe -fSLo pmc-backend-v22h.zip        "$base/pmc-backend-v22h.zip"
curl.exe -fSLo deploy-frontend-v44.ps1     "$base/deploy-frontend-v44.ps1"
curl.exe -fSLo deploy-backend-v22h.ps1     "$base/deploy-backend-v22h.ps1"
```

### 2. Verify SHA-256 checksums (paste values from this README's footer)

```powershell
Get-FileHash .\pmc-frontend-v44-build.zip -Algorithm SHA256
Get-FileHash .\pmc-backend-v22h.zip       -Algorithm SHA256
```

Compare against the values at the very bottom of this README. **If either mismatches, DO NOT deploy** — re-download using `curl.exe -fSLo` (the `-f` flag makes curl fail loudly on 4xx/5xx instead of writing HTML on top of your zip).

### 3. Frontend deploy (~2 min)

```powershell
.\deploy-frontend-v44.ps1
```

Expected tail:
```
[4/4] CloudFront invalidation created: I1234ABCDEF
Frontend v44 deploy complete.
```

Wait 1–3 min for CloudFront invalidation, then hard-refresh `https://www.pmcmanagers.com/admin`.

### 4. Backend deploy (~4–6 min)

```powershell
.\deploy-backend-v22h.ps1
```

Watch env status:
```powershell
aws --profile pmc-admin --region eu-west-2 elasticbeanstalk describe-environments `
  --environment-names pmc-backend-prod `
  --query 'Environments[0].[Status,Health,VersionLabel]' --output table
```
`Status` should transition `Updating → Ready`, `Health` should end at `Ok`, and `VersionLabel` should show `v22h-YYYYMMDD-HHMMSS`.

---

## Step-by-step (Linux/macOS bash)

```bash
cd ~/pmc-v44-deploy   # wherever the artefacts land
chmod +x deploy-frontend-v44.sh deploy-backend-v22h.sh
./deploy-frontend-v44.sh
./deploy-backend-v22h.sh
```

---

## Smoke tests after both deploys land

**Frontend**
1. Sign in at `https://www.pmcmanagers.com/admin` (`adminsupport@pmcmanagers.com` / `Admin@12345`).
2. Click **VENDORS** → click the **INACTIVE** filter chip.
3. Confirm each inactive row shows a green **ACTIVATE NOW** button.
4. Click the button on any test vendor → confirm the `window.confirm` prompt appears.
5. Press **OK** → confirm a green toast fires and the row scrolls into view with an emerald ring highlight.

**Registration**
1. Open a fresh browser: `https://www.pmcmanagers.com/register`.
2. Enter any email and click **SEND ME A RESUME LINK**.
3. Confirm the stepper shows **6** tabs in this order: `A · B · C · D · DIRECTORS · E`.
4. Click **DIRECTORS · BENEFICIAL OWNERS** → confirm the form renders with Person #1.
5. Click **+ ADD ANOTHER PERSON** → confirm a second Person row appears.

**Backend**
```powershell
$Api = 'https://api.pmcmanagers.com'   # or your prod backend URL
$login = curl.exe -sS -X POST "$Api/api/v1/admin/auth/login" `
           -H "Content-Type: application/json" `
           -d '{"email":"adminsupport@pmcmanagers.com","password":"Admin@12345"}' | ConvertFrom-Json
$activate = curl.exe -sS -X POST "$Api/api/v1/vendors/PMC-SUP-000029/activate" `
              -H "Authorization: Bearer $($login.token)" `
              -H "X-CSRF-Token: $($login.csrf_token)" `
              -H "Content-Type: application/json" `
              --cookie "csrf_token=$($login.csrf_token)" `
              -d '{"mode":"resend_link"}'
$activate
```
Expected: `{"ok":true,"vendor_ref":"PMC-SUP-000029","mode":"resend_link", ...}`

---

## Rollback (if v44 misbehaves)

Roll the backend back to v22g in one click via the EB console **Application versions** tab — pick the previous version label and click **Deploy**.

Roll the frontend back by re-running `deploy-frontend-v43.sh` (v43 zip is still in your `pmc-v43/` folder).

---

## Checksums

See the footer of this file after the build lands — `sha256sum` values printed during the build are appended below.

### SHA-256 checksums (verified on preview build 22 Feb 2026)

```
c079e2236e6fbf9e58eb6860840837b92a134a20b303dbb01339977f1480b38f  pmc-frontend-v44-build.zip   (128 MB)
a40a2621b1be8b0446a3dd2cd804c61eb9ba92e644282e650bbddafcf5aa2f51  pmc-backend-v22h.zip         (244 kB)
```

Backend zip top-level entries (must be at absolute root):
```
Dockerrun.aws.json
Dockerfile
VERSION
backend/
```
