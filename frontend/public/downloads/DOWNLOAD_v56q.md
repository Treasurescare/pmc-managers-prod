# PMC Managers — Release v56q

Adds the Sector / Contract-Type taxonomy above UNSPSC. Includes all v56o bug fixes.

## New — taxonomy masters (Sector → Contract Type → UNSPSC)
Two new master-data sets in their own collections (they never mix into the UNSPSC
commodity pickers). Auto-seeded on boot (idempotent; existing data untouched):

- **Sectors (25)** — Power & Energy (Transmission/Distribution/Generation), Renewable
  Energy (Solar/Wind/Hydro/Biomass), Oil & Gas, Water, Transport, Railways & Metro,
  Ports & Aviation, Buildings, Industrial, Healthcare, Education, Telecom & IT,
  Logistics, Mining, Environment, Agriculture, Defence, Facilities/O&M.
- **Contract types (30)** — EPC (Engineering & Design / Procurement / Construction /
  Turnkey), Works (Civil, E&M, Fire, Security, Horticulture, Interiors, O&M),
  PPP (BOT, BOOT, DBFOT, HAM, DBFO, Annuity), Supply/Goods, Services/Consultancy,
  O&M, Framework/Rate Contract.

Manage them in **Admin → Masters → Sectors** and **→ Contract types** (add / rename /
disable, with parent → child nesting). Public endpoints:
`/api/v1/masters/sectors/public` and `/api/v1/masters/contract-types/public`.

The earlier v56p attempt (which seeded these flat into the Category list) is
auto-cleaned on boot, so UNSPSC categories stay clean.

## Still to wire (next batch)
- Cascading **Sector → Contract type** pickers on the notice-creation form and
  vendor registration/profile (optional now; made mandatory at go-live).
- Public tender board filter by sector / contract type.

## Bug fixes carried from v56o
#58 catalog disable · #44 eval default rubric · #17 docusign vendor envelopes ·
#23 corrigenda validate-before-write · #36 closed-tender Start bid · #72 escrow link message.

## Deploy order
1. Upload `pmc-backend-v56q.zip` to Elastic Beanstalk; wait green/healthy (masters seed on boot).
2. Upload the **contents** of `pmc-frontend-v56q-prod-build.zip` to the S3 root.
3. CloudFront → invalidate `/*`.
4. Confirm footer reads **Frontend v56q · Backend v56q**.
