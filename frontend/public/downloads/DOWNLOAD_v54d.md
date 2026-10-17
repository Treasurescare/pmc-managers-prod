# PMC Managers v54d — Searchable country picker in Operating Regions

Release target: 17 Feb 2026

**Contains everything from v54c plus this UX fix.** If you haven't deployed
yet, you can deploy the v54d pair directly and skip v54c.

## What's new

### Section D → Operating Regions → Country is now searchable
The plain 250-row `<select>` forced admins/vendors to scroll manually to
find a country. The new combobox lets you **type letters** (e.g. `ind`)
and instantly floats matches to the top under a "MATCHES" heading — name
or ISO code, starts-with ranked first — while the **full country list
stays visible below** an "ALL COUNTRIES" divider, so nothing is hidden.

- Click a match or press Enter to pick the first match; Escape closes.
- Selecting a country resets state/city/ZIP and unlocks the state cascade
  exactly like before.
- Selected value displays as `🇮🇳 IN — India`.

Verified with a live browser run on the registration form: typed "ind" →
India/Indonesia/British Indian Ocean Territory floated to top → selected
India → state dropdown populated.

## Deploy

Same as before: EB for the backend zip, S3 sync + CloudFront invalidation
for the frontend build. Backend content is identical to v54c.

## Artifacts

* Backend: `pmc-backend-v54d.zip`
* Frontend: `pmc-frontend-v54d-prod-build.zip`
