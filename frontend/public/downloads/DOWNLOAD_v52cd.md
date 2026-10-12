# PMC Managers — Frontend v52cd (12 Oct 2026)

## What's in this build

### Notices → Create notice: searchable Tender Template picker with auto-fill
The plain "Tender template (Tender Builder)" dropdown is now a **search picker**:

- Type to filter by **name**, **tender reference number**, **created date**
  (dd/mm/yyyy or ISO) or **tender value** (commas ignored). Each result row
  shows the ref, created date, ₹ value and section count so you can tell
  same-named drafts apart.
- Picking a tender **auto-fills Title, Work Description and Budget amount**
  from the tender's header (toast confirms). A **✕ clear** button unlinks.
- Friendly no-match message suggests the searchable dimensions.
- Testids: `notice-tender-template` (search box), `notice-tpl-picker`,
  `notice-tpl-opt-<id>`, `notice-tpl-nomatch`, `notice-tender-template-clear`.

## Deploy
- Backend: unchanged from v52bz.
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.

File: `pmc-frontend-v52cd-prod-build.zip`
