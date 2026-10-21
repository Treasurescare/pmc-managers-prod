# PMC Managers — Release v56r

Wires the Sector / Contract-type taxonomy (from v56q) into notice creation.

## New in v56r — Notice pickers
- The **Create Notice** form (Admin → Notices → New notice) and the **Edit Notice**
  modal now have cascading **Sector** and **Contract type** dropdowns (grouped
  parent → child), right under Category.
- Selections save on the tender as `sector_code` / `contract_type_code`
  (verified end-to-end: a created notice returns both values).
- Optional for now — becomes mandatory at go-live.

## Still to wire (next batch)
- **Vendor tagging** — same Sector / Contract type selectors on vendor
  registration & profile (for supplier↔tender matching).
- **Board filters** — filter the public tender board by Sector / Contract type.
- **Go-Live switch** — make both mandatory once test data is cleared.

## Carried from v56q / v56o
v56q Sector (25) + Contract-type (30) masters (Admin → Masters) auto-seed on boot;
v56o bug fixes (#58 #44 #17 #23 #36 #72).

## Deploy order
1. Upload `pmc-backend-v56r.zip` to Elastic Beanstalk; wait green/healthy.
2. Upload the **contents** of `pmc-frontend-v56r-prod-build.zip` to the S3 root.
3. CloudFront → invalidate `/*`.
4. Confirm footer reads **Frontend v56r · Backend v56r**.
