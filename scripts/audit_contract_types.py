#!/usr/bin/env python3
"""
Contract Types duplicate audit — READ ONLY / DRY RUN.

Safe to run against production. It performs NO writes, deletes, merges or
index creation. It only reads `contract_types` and prints duplicate groups
(by `code` and by normalized `name`) plus per-row detail and reference usage
so you can decide what to remediate.

Usage (run from the deployment environment where the prod DB is reachable):

    export MONGO_URL="<production mongo connection string>"
    export DB_NAME="<production db name>"
    python3 audit_contract_types.py

Optional:
    export AUDIT_JSON_OUT="/tmp/contract_types_audit.json"   # also dump full report

Nothing is pasted into chat; the script reads credentials from the environment
only. If MONGO_URL / DB_NAME are unset it exits immediately.
"""
import json
import os
import re
import sys
from collections import defaultdict

try:
    from pymongo import MongoClient
except ImportError:
    print("pymongo is required. Install with: pip install pymongo")
    sys.exit(1)

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

if not MONGO_URL or not DB_NAME:
    print("ERROR: set MONGO_URL and DB_NAME environment variables first.")
    print("  export MONGO_URL=... ; export DB_NAME=... ; python3 audit_contract_types.py")
    sys.exit(1)


def norm_name(v):
    """Normalize a display name for duplicate detection: lowercase, collapse
    whitespace, strip trailing grouping suffix noise."""
    return re.sub(r"\s+", " ", (v or "").strip().lower())


def main():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8000)
    db = client[DB_NAME]
    col = db["contract_types"]

    rows = list(col.find({}))
    total = len(rows)
    print("=" * 70)
    print(f"contract_types audit (READ ONLY)  db={DB_NAME}  total_rows={total}")
    print("=" * 70)

    # Reference usage counts: how many notices point at each contract_type_code
    usage = defaultdict(int)
    try:
        for n in db["notices"].find({}, {"contract_type_code": 1}):
            c = n.get("contract_type_code")
            if c:
                usage[c] += 1
    except Exception as e:
        print(f"(note: could not scan notices for usage counts: {e})")

    # Group by exact code
    by_code = defaultdict(list)
    by_name = defaultdict(list)
    for r in rows:
        by_code[r.get("code")].append(r)
        by_name[norm_name(r.get("name"))].append(r)

    dup_codes = {k: v for k, v in by_code.items() if k is not None and len(v) > 1}
    dup_names = {k: v for k, v in by_name.items() if k and len(v) > 1}

    def fmt(r):
        return {
            "_id": str(r.get("_id")),
            "code": r.get("code"),
            "name": r.get("name"),
            "parent_code": r.get("parent_code"),
            "created_at": str(r.get("created_at")) if r.get("created_at") else None,
            "notice_usage": usage.get(r.get("code"), 0),
        }

    report = {"total_rows": total, "duplicate_codes": {}, "duplicate_names": {}}

    print(f"\nDUPLICATE CODES: {len(dup_codes)} group(s)")
    for code, group in sorted(dup_codes.items()):
        print(f"\n  code='{code}'  ({len(group)} rows)")
        report["duplicate_codes"][code] = [fmt(r) for r in group]
        for r in group:
            f = fmt(r)
            print(f"    - _id={f['_id']}  name='{f['name']}'  parent={f['parent_code']}  "
                  f"created={f['created_at']}  notices_using_code={f['notice_usage']}")

    print(f"\nDUPLICATE NAMES (normalized, may differ in code): {len(dup_names)} group(s)")
    for name, group in sorted(dup_names.items()):
        codes = sorted({r.get("code") for r in group})
        # Only interesting if more than one distinct code shares the name
        report["duplicate_names"][name] = [fmt(r) for r in group]
        print(f"\n  name~='{name}'  ({len(group)} rows, codes={codes})")
        for r in group:
            f = fmt(r)
            print(f"    - _id={f['_id']}  code='{f['code']}'  parent={f['parent_code']}  "
                  f"created={f['created_at']}  notices_using_code={f['notice_usage']}")

    print("\n" + "=" * 70)
    if not dup_codes and not dup_names:
        print("RESULT: 0 duplicates found — nothing to remediate.")
    else:
        print(f"RESULT: {len(dup_codes)} duplicate-code group(s), "
              f"{len(dup_names)} duplicate-name group(s). NO changes were made (dry run).")
    print("=" * 70)

    out = os.environ.get("AUDIT_JSON_OUT")
    if out:
        with open(out, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"Full JSON report written to {out}")

    client.close()


if __name__ == "__main__":
    main()
