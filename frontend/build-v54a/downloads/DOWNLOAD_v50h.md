# PMC Managers Limited — Release v50h

## Create-Notice form — now fully master-driven
1. **Category** — dropdown fed from Masters → Categories (v50g).
2. **Delivery country** — dropdown fed from `/api/v1/meta/countries` (30-country master).
3. **Auto-EMD** — picker now filters EMD masters by BOTH country AND category
   so you can keep distinct EMD slabs per (country, category) pair.

## Approval Matrix — pick specific users
4. **Assignee picker per step** — Masters → Approval Matrix now shows a
   second dropdown per row: pick a specific escrow officer / legal
   counsel / accountant for that step, or leave as "Any user with this
   role" for pool routing. Dropdown auto-filters to staff holding the
   step's role. Warning line appears when no staff carry that role.

## Backend changes (v50h)
* `EmdMasterIn` adds optional `category` field.
* `GET /api/v1/tender-pro/emd-masters?category=X` — scoped filter
  (unscoped masters still return).
* `ApprovalStepIn` adds optional `assignee_user_id`, `assignee_email`,
  `assignee_name` fields.

## Still TODO
* EMD master EDITOR UI (there is no admin page to create/edit EMD
  masters — only API). I can build one as part of Batch D if you want.
* #99 Tender Builder country filter: left as v50e behaviour per owner.
* #123 Translation button: deferred; needs screen clarification.

## Bundles
* Frontend: `pmc-frontend-v50h-prod-build.zip`
* Backend:  `pmc-backend-v50h.zip` (required — adds endpoints + schema)
