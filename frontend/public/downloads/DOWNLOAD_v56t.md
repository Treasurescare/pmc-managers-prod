# PMC Managers — v56t (26 Jun 2026)

Production bundles (upload to your AWS stack):

- Backend  → `pmc-backend-v56t.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56t-prod-build.zip` → unzip, upload contents to S3 bucket root
- Then invalidate CloudFront `/*`
- Confirm footer: "Frontend v56t · Backend v56t"

Client bug-sheet + new-capabilities pack:

- Word  → `PMC_Bug_Clearance_v56t_20261022.docx`
- Excel → `PMC_Bug_Clearance_v56t_20261022.xlsx`

## What's new in v56t (on top of v56s)

1. **Homepage taxonomy search** — the public home hero now searches on the
   primary procurement taxonomy: **Sector → Contract type → Category** plus the
   **full 250-country master** and free-text keyword. All controls are optional
   and combine in any order; submitting deep-links to the live board
   `/tenders/all` which restores and applies the same filters (shareable URLs).

2. **Country ↔ currency master** — each country now has an editable
   **accepted-currencies** list with one **primary/default** (Masters →
   *Country currencies*). Notice / Bid / EMD currency pickers **default-load**
   the selected country's primary accepted currency, listing the accepted set
   first, while still allowing **any** active currency to be chosen.

3. **Notice taxonomy backfill** — new admin screen (**Admin → Taxonomy
   backfill**) lists every notice with its Sector + Contract-type **auto-guessed
   from the category/title**; admins review, correct and save in bulk so legacy
   notices show up under the new homepage filters.

4. **Bid & EMD currency locked to tender** — vendor bid price and EMD are always
   quoted in the tender's own currency (which now follows the delivery country's
   primary from #2).

Fixed in passing: the homepage hero form was being hijacked by a legacy
document-level submit handler (routed to `/tenders/live` with the Sector name
placed in `?country=`); the hero now owns its own submit.

Preview-verified. Awaiting production deploy + your confirmation.
