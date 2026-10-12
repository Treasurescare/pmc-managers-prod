# PMC Managers — Backend + Frontend v52ci (12 Oct 2026)

## What's in this build (your Q (h))

### Structured Operation Regions — multi-row office editor
Vendor Registration **Section D** → "Operating regions" is no longer a plain
comma-separated input. Each entry is now a full office card with:

- **Office name \*** (text)
- **Country \*** (dropdown from 30-country master, shows "KZ — Kazakhstan")
- **Address \*** (multiline)
- **City \***, **State / Province \***, **ZIP** (text)

Add/remove offices individually; adding is blocked if any required field
is missing (clear message). Backwards compatible — any legacy string[]
entries show up as a dismissible amber banner above the editor saying
*"Previously declared regions (please re-add as offices below)"*.

**New component**: `RegionOfficeEditor.jsx`.
**New testids**: `op-regions-editor`, `op-region-row-<i>`, per-field
`op-region-{name,country,address,city,state,zip}-{i}`, and the add form
`op-region-new-*` + `op-region-add-btn`.

### Admin review — structured display
`VendorsPanel.jsx` detail now renders each office on its own line
(name bold, address · city · state · ZIP · country code). Legacy strings
continue to render in their original single-line form. New testids:
`kpi-region-office-<i>` / `kpi-region-legacy-<i>`.

### Backend model change
`backend/models/registration.py` — `operating_regions` type widened from
`List[str]` to `List[Any]` so the PATCH endpoint accepts both legacy
strings and new structured office objects without migration.

## Deploy
- **Backend**: ship `pmc-backend-v52ci.zip` (model change requires redeploy).
- **Frontend**: sync `pmc-frontend-v52ci-prod-build.zip` to S3, invalidate `/*`.

Files:
- `pmc-frontend-v52ci-prod-build.zip`
- `pmc-backend-v52ci.zip`
