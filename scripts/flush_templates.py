"""Extra production cleanup — clears the template/scoring-config collections that
the main flush kept (your test BOQ/tender/SBD templates, rubrics, etc.).
Keeps everything else as-is. Backs up before deleting.

Run:
    CONFIRM_FLUSH=YES MONGO_URL="<prod-uri>" DB_NAME="pmc_tender_db" python3 flush_templates.py
"""
import os, sys, datetime
from pymongo import MongoClient
from bson import json_util

COLLS = ["boq_templates", "tender_templates", "sbd_templates",
         "vendor_templates", "rubrics", "rating_criteria_sets",
         "auction_invite_templates"]


def main():
    if os.environ.get("CONFIRM_FLUSH") != "YES":
        sys.exit("Refusing to run: set CONFIRM_FLUSH=YES to proceed.")
    uri = os.environ.get("MONGO_URL"); dbn = os.environ.get("DB_NAME")
    if not uri or not dbn:
        sys.exit("MONGO_URL and DB_NAME must be set.")
    db = MongoClient(uri)[dbn]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"./template_flush_backup_{ts}"; os.makedirs(bdir, exist_ok=True)
    existing = set(db.list_collection_names())
    total = 0
    for n in COLLS:
        if n not in existing:
            print(f"  (skip) {n} not present"); continue
        docs = list(db[n].find({}))
        with open(f"{bdir}/{n}.json", "w") as f:
            f.write(json_util.dumps(docs))
        r = db[n].delete_many({}); total += r.deleted_count
        print(f"  cleared {r.deleted_count:>6}  {n}  (backed up {len(docs)})")
    print(f"\nTOTAL DELETED: {total}\nBACKUP: {bdir}")


if __name__ == "__main__":
    main()
