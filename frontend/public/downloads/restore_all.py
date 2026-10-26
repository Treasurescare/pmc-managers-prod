"""Restore a full_backup_* folder created by backup_all.py. For each collection
it WIPES the current contents then reloads from the JSON file.

Run:
    MONGO_URL="YOUR_CONNECTION_STRING" python3 restore_all.py ./full_backup_YYYYMMDD_HHMMSS
"""
import os, sys
from pymongo import MongoClient
from bson import json_util


def main():
    uri = os.environ.get("MONGO_URL")
    if not uri:
        sys.exit('Set MONGO_URL="your-connection-string" before running.')
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 restore_all.py ./full_backup_<timestamp>")
    root = sys.argv[1]
    cli = MongoClient(uri)
    total = 0
    for dbn in sorted(os.listdir(root)):
        ddir = os.path.join(root, dbn)
        if not os.path.isdir(ddir):
            continue
        db = cli[dbn]
        for fn in sorted(os.listdir(ddir)):
            if not fn.endswith(".json"):
                continue
            coll = fn[:-5]
            with open(os.path.join(ddir, fn)) as f:
                docs = json_util.loads(f.read())
            db[coll].delete_many({})
            if docs:
                db[coll].insert_many(docs)
            total += len(docs)
            print(f"  restored {dbn}.{coll}: {len(docs)} docs")
    print(f"\nRESTORE COMPLETE — {total} docs")


if __name__ == "__main__":
    main()
