# PMC Managers — Frontend v52ce (12 Oct 2026)

## What's in this build

### Notices tender picker — EMD auto-fill added
Follow-up to v52cd: picking a tender in Notices → Create notice now pre-fills
**EMD fixed amount** (`header.emd_amount`) and **EMD % of budget**
(`header.emd_percentage`) alongside title / description / budget. All values
remain ordinary editable inputs after the pick. Toast updated to
"title, description, budget and EMD pre-filled".

Verified live: pick "QA Bridge Tender" → EMD 50,000 filled, manual edit to
75,000 retained; budget 5,000,000 → 6,000,000 retained.

## Deploy
- Backend: unchanged from v52bz.
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.
- Supersedes v52cd (includes it).

File: `pmc-frontend-v52ce-prod-build.zip`
