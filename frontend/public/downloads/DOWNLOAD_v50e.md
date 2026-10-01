# PMC Managers Limited — Release v50e

## What's new
### DPR flow: pick ANY saved master (any country/industry) or build new
User request: "when I choose a country I may have a template but that
template may be of a different format and could be of a different
industry vertical — show ALL existing formats in a dropdown and still
have an option to build a brand new format."

The old flow trapped admins: country filter hid every master from
other countries, and the "borrow / build new" options only appeared
when ZERO masters existed for the picked country. If the country had
one master but it was the wrong industry, you had no way to pick
anything else from the dropdown.

Fix (`DprGenerateModal.jsx`):
1. **Master dropdown now always shows every saved master**, grouped
   with native `<optgroup>`:
   - "Masters saved for <COUNTRY> (N)" at the top (same-country match
     first)
   - "Other saved masters (N) — different country, re-usable" below
   Each option is prefixed `[COUNTRY · industry] <name>` so you can
   see at a glance which country and industry you're picking.
2. **"Build a brand-new master from this DPR" checkbox** is now a
   permanent sibling of the dropdown — never gated behind the amber
   "no master" box. Pick it when none of the saved masters match your
   industry or format. The AI drafts a fresh structure and section
   headings from your DPR and saves it as a new master under the
   chosen country.
3. A compact amber note still appears **only** when the country has
   zero same-country masters, and only to guide first-time use.
4. The existing editable section-headings panel (v50d) continues to
   render in both paths (new master + existing master).

Service-worker cache bumped to `pmc-shell-v50e-rev1`.

## Bundles
* **Frontend: `pmc-frontend-v50e-prod-build.zip`** — deploy ONLY this.
* **Backend: `pmc-backend-v49y.zip`** — unchanged.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.

Verify:
- Tender builder → AI-generate from DPR → pick any country →
  dropdown lists masters saved for that country at the top AND all
  other masters below. Picking any of them works. The "Build a
  brand-new master" option is visible immediately beneath the
  dropdown and no longer requires zero country-matches.

## Rollback
Frontend v50d. No API or schema changes.
