# Production `contract_types` duplicate remediation — plan (NON-DESTRUCTIVE)

Status: PLAN ONLY. No production change performed. Requires explicit user
authorization before any write/index runs against production.

## Context
- Preview `contract_types`: 30 docs, 0 duplicate codes, 0 duplicate names — clean.
- Production state is UNVERIFIED from the preview pod. The duplicate concern was
  reported against production only.
- Seeding is idempotent per `code` (`_seed_contract_types` in server.py), so new
  boots will not add more duplicates; any existing production duplicates would be
  legacy rows created before the code-keyed seed.

## Guard rails (do NOT violate)
- No `delete_many` / `drop` on production taxonomy without a dry-run + user sign-off.
- Do NOT create a unique index on `code`/`name` BEFORE duplicates are remediated —
  index creation will fail or lock on existing dupes.
- Preserve the newest/most-referenced row; never blind-delete.

## Step 1 — Dry-run audit (read-only) against production
Run with a production `MONGO_URL` (user-provided, in the deployment env — never
pasted into chat):
```python
from pymongo import MongoClient, DESCENDING
db = MongoClient(PROD_MONGO_URL)[PROD_DB]
pipeline = [
  {"$group": {"_id": "$code", "ids": {"$push": "$_id"}, "n": {"$sum": 1}}},
  {"$match": {"n": {"$gt": 1}}},
]
dupes = list(db.contract_types.aggregate(pipeline))
print("duplicate codes:", len(dupes))
for d in dupes: print(d["_id"], d["n"])
# repeat grouping on "name" to catch same-name/different-code rows
```
Deliver the dry-run output to the user. If `len(dupes) == 0`, STOP — nothing to do;
proceed straight to Step 3 (index) after sign-off.

## Step 2 — Deterministic merge (only after user approval)
For each duplicate `code` group:
1. Pick the KEEP row deterministically: the one referenced by the most
   notices/vendors/registrations (`sector_code`/`contract_type_code` usage);
   tie-break on newest `created_at`, then lowest `_id`.
2. Re-point any references on the losing rows to the KEEP row's `code` (codes are
   usually identical within a code-group, so typically no re-pointing needed).
3. Delete only the losing rows, one group at a time, logging each `_id` removed.
Run inside a scripted, re-runnable migration with a printed before/after count.

## Step 3 — Prevent recurrence (after groups are clean)
```python
db.contract_types.create_index("code", unique=True)
```
Only after Step 2 confirms 0 duplicate codes. Keep `name` non-unique (display
label can legitimately repeat across groups) unless the user wants it unique.

## Rollback
Keep the dry-run export (JSON dump of all rows) before any delete so any row can
be restored. Store the dump with the deployment artifacts, not in the repo.
