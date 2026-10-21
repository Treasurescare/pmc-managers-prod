# PMC Managers — Release v56p

Includes everything in v56o plus the customer-requested contract/works taxonomy.

## Bug-sheet fixes (verified in preview)
- **#58 Product Catalog** — Disable/Enable a product now works (no HTTP 422).
- **#44 Evaluation scoring** — default rubric fallback; scored bids no longer show Tech 0%.
- **#17 DocuSign (vendor)** — vendor envelopes match bids correctly (no false "Nothing to sign yet").
- **#23 Corrigenda** — all validation runs before any write; a failed publish leaves no orphan.
- **#36 Closed tenders** — "Start bid" becomes a disabled "Bidding closed" label.
- **#72 Escrow magic-link** — friendly invalid/expired message instead of raw 404.

## New — contract/works/sector taxonomy (customer request)
Auto-seeded into the Category master on boot (idempotent; existing categories untouched):
- **EPC Contracts** → Engineering and Design · Procurement · Construction and Execution · Turnkey
- **Works** → Civil · Electrical and Mechanical · Fire Protection · Security · Horticulture and Landscape · Interiors and Equipment · Operations and Maintenance
- **PPP** → BOT · DBFOT · HAM
- **Renewable Energy** → Solar · Wind · Hydro
- **Power Sector** → Transmission · Distribution · Production
- **Logistics**
These appear in Admin → Masters → Categories, vendor registration category pickers and public notice filters. No manual DB step — deploying the backend seeds them into production automatically.

## Still open (next batch)
- #55 Registration approve ("missing Section A fields")
- #40 Notice timelines (public key-dates are template placeholders)
- #56 AI FILL ALL (502 on large templates — sequential AI calls)
- #23b Public Corrigenda tab still shows "No corrigenda section published"

## Deploy order
1. Upload `pmc-backend-v56p.zip` to Elastic Beanstalk; wait green/healthy (categories seed on boot).
2. Upload the **contents** of `pmc-frontend-v56p-prod-build.zip` to the S3 root.
3. CloudFront → invalidate `/*`.
4. Confirm footer reads **Frontend v56p · Backend v56p**.
