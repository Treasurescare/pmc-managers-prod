# PMC Managers v56s — release bundle + clearance docs

All files are downloadable from the preview `/downloads/` path.

## Production bundles (for AWS)
- `pmc-backend-v56s.zip` — FastAPI backend → Elastic Beanstalk
- `pmc-frontend-v56s-prod-build.zip` — built React app → S3

## Team documents
- `PMC_Bug_Clearance_v56s_20261021.docx`
- `PMC_Bug_Clearance_v56s_20261021.xlsx`

## AWS release steps (run on your side with your AWS access)
1. Backend: deploy `pmc-backend-v56s.zip` to the Elastic Beanstalk environment.
2. Frontend: unzip `pmc-frontend-v56s-prod-build.zip` and upload its CONTENTS to the S3 bucket root.
3. Invalidate CloudFront: `/*`.
4. Hard-refresh; the footer should read Frontend v56 · Backend v56s.

Go-Live stays OFF after deploy (Sector/Contract Type remain optional) until you flip it in Masters → Go-Live.
