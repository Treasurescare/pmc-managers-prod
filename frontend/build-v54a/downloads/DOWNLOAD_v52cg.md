# PMC Managers — Frontend v52cg (12 Oct 2026)

## What's in this build

### Tender Builder — Country filter list cleanup (user Q (a))
`TenderBuilderPanel.jsx` + `TenderFilterBar.jsx`:

- Dropdown now shows **"KZ — Kazakhstan"**, **"IN — India"**, etc. — code AND
  name on the same line. Full master list of 30 countries is used.
- The "a few of them are showing full company names" issue is gone: template
  rows whose `country` value isn't a valid ISO code (2-3 chars, letters/digits)
  are stripped from the dropdown. Orphan codes with no master name fall back
  to just the code.

## Deploy
- Backend: unchanged (stay on v52cf).
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.
- Supersedes v52cf frontend (includes it).

File: `pmc-frontend-v52cg-prod-build.zip`
