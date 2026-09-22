# PMC Managers v2 — v45 AWS Deployment Guide

**⚠ CRITICAL PRE-STEP — REDEPLOY v44b FIRST**

Your production frontend today points at the PREVIEW backend (that's why login fails on `www.pmcmanagers.com`). Before rolling v45, redeploy the v44b bundle which has the correct production backend URL baked in.

```powershell
Set-Location C:\Users\abcd\pmcmanagers\
$base = 'https://tender-hub-57.preview.emergentagent.com/downloads'

# --- v44b (login fix) ---
Remove-Item .\pmc-frontend-v44b-build.zip -ErrorAction SilentlyContinue
curl.exe -fSLo pmc-frontend-v44b-build.zip "$base/pmc-frontend-v44b-build.zip"
Get-FileHash .\pmc-frontend-v44b-build.zip -Algorithm SHA256
# expect e8185592e8791b48fa16d6ee42c47ef3f26ff5978c2b8cad8d596b19d6aa284e
.\deploy-frontend-v44b.ps1
```

Wait 3 minutes for CloudFront to settle, hard-refresh `https://www.pmcmanagers.com`, then log in to confirm the login endpoint now works.

---

## Contents of the v45 drop

```
pmc-v45/
├── pmc-frontend-v45-build.zip     → S3 + CloudFront (Tender Pro UI)
├── pmc-backend-v22i.zip           → Elastic Beanstalk (Tender Pro APIs)
├── deploy-frontend-v45.ps1        → Windows PowerShell deploy
└── deploy-backend-v22i.ps1        → Windows PowerShell deploy
```

**Backend zip verified layout (Docker files at absolute root):**
```
Dockerrun.aws.json
Dockerfile
VERSION            (v22i-v45-YYYYMMDD-HHMMSS)
backend/
```

---

## What v45 ships (all curl-verified on preview)

**Phase C — AI DPR + full-doc generation**
- Batch upload up to 3 DPRs at once (`DprGenerateModal`) — each is analyzed in parallel, closest master auto-suggested per file, drafts created together
- `POST /api/v1/tender-pro/dpr/analyze` — LLM extracts header + per-section drafts from PDF/DOCX/TXT
- `POST /api/v1/tender-pro/templates/{tid}/ai-fill-all` — one-shot AI draft for every empty section

**Phase A — Auto tender-ref, per-section save, filters, dynamic covers**
- `POST /api/v1/tender-pro/next-reference?country=KZ&industry=Construction&kind=rfp` → `PMC-KZ-CONS-RFP-26-00001`
- `PATCH /api/v1/tender-pro/templates/{tid}/sections/{code}` — save one section without version bump
- `TenderFilterBar` with search / country / industry / sort (A-Z, Z-A, date newest / oldest)
- Dynamic cover rows already synced to `no_of_covers`

**Phase B — Country templates + save-as-master + EMD master**
- `POST /api/v1/tender-pro/templates/{tid}/save-as-master` promotes a working draft into the master library under (country, industry)
- `emd_masters` collection CRUD + `POST /emd-masters/compute` (verified: 50k fixed @ 5M, 2% → 1M @ 50M)
- **v45b — Auto-EMD prefill**: `EmdMasterPicker` now auto-selects the country's default master when Delivery Country changes on the Notice form (badge shows "Auto-picked")

**Phase D — Rating criteria master + multi-rater aggregate**
- Full **Rating & Fees** sub-tab in Masters panel (compose 1-30 criteria per set, weights, scale, is_default)
- `POST /api/v1/tender-pro/ratings/multi` per-criterion scoring, auto-normalised to 0-100 weighted score
- `GET /api/v1/tender-pro/ratings/aggregate/{vendor_ref}` cross-rater aggregate

---

## Step-by-step (Windows PowerShell)

Assumes `C:\Users\abcd\pmcmanagers\` and AWS CLI with `pmc-admin` profile.

### 1. Download

```powershell
Set-Location C:\Users\abcd\pmcmanagers\
$base = 'https://tender-hub-57.preview.emergentagent.com/downloads'

Remove-Item .\pmc-frontend-v45-build.zip -ErrorAction SilentlyContinue
Remove-Item .\pmc-backend-v22i.zip -ErrorAction SilentlyContinue

curl.exe -fSLo pmc-frontend-v45-build.zip "$base/pmc-frontend-v45-build.zip"
curl.exe -fSLo pmc-backend-v22i.zip       "$base/pmc-backend-v22i.zip"
curl.exe -fSLo deploy-frontend-v45.ps1    "$base/deploy-frontend-v45.ps1"
curl.exe -fSLo deploy-backend-v22i.ps1    "$base/deploy-backend-v22i.ps1"
```

### 2. Verify SHA-256

```powershell
Get-FileHash .\pmc-frontend-v45-build.zip -Algorithm SHA256
Get-FileHash .\pmc-backend-v22i.zip       -Algorithm SHA256
```

**Expected values (computed after slim rebuild — check the trailing block of this README for the definitive values):**
```
pmc-frontend-v45-build.zip  → (see footer)
pmc-backend-v22i.zip        → 5BA9D24DE5C3132F39EBE932765AE1FC6AA77F484C5CA8152BB463777EBAA658
```

If either hash mismatches, **DO NOT deploy**. Re-download using `curl.exe -fSLo`.

### 3. Frontend deploy (~2 min)

```powershell
.\deploy-frontend-v45.ps1
```

### 4. Backend deploy (~4-6 min)

```powershell
.\deploy-backend-v22i.ps1

aws --profile pmc-admin --region eu-west-2 elasticbeanstalk describe-environments `
  --environment-names pmc-backend-prod `
  --query "Environments[0].[Status,Health,VersionLabel]" --output table
```

Watch until `Status = Ready`, `Health = Ok`, `VersionLabel = v22i-*`.

---

## Smoke tests after deploy

1. **Login** at `https://www.pmcmanagers.com/admin` with `adminsupport@pmcmanagers.com` / `Admin@12345`.
2. **Tender Builder → ✨ AI Generate from DPR** — upload 2 DPRs at once, see them analyzed in parallel with different masters auto-picked.
3. **Masters → Rating & Fees** — compose a new criteria set with 5 criteria, mark as default, save.
4. **Notices → New notice** — pick Delivery Country `KZ`, see the EMD picker auto-select the default KZ EMD master (badge "Auto-picked"), enter a Budget → EMD amount auto-fills.
5. **Tender Builder → header form** — after cloning from a DPR-generated draft, see the amber warnings banner at the top of the header form.

## Rollback

```powershell
# Backend — pick v22h in EB console → Application versions → Deploy
# Frontend — re-run .\deploy-frontend-v44b.ps1 (v44b zip still on disk)
```

---

## Definitive SHA-256 (from live download — verify before deploying)

```
pmc-frontend-v45-build.zip   9.5 MB   SHA256: 717db2b5c0f1e0a1bf38726e5b3cc4c2718a90a5fa8c6c1c8c5384c530a47203
pmc-backend-v22i.zip         252K   SHA256: b00423dc4da28885fe66e44022c9dd17a064a7f4a835da31e943d4cf25bcabc7
```

Bundle: main.0e4160f3.js — verified against `https://www.pmcmanagers.com` (no preview URL bleed).
