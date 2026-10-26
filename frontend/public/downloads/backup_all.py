"""Full read-only backup of EVERY database/collection in your MongoDB cluster to
JSON files. Nothing is modified. Uses pymongo (already installed).

Run:
    MONGO_URL="YOUR_CONNECTION_STRING" python3 backup_all.py
"""
import os, sys, datetime
from pymongo import MongoClient
from bson import json_util


def main():
    uri = os.environ.get("MONGO_URL")
    if not uri:
        sys.exit('Set MONGO_URL="your-connection-string" before running.')
    cli = MongoClient(uri)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = f"./full_backup_{ts}"
    os.makedirs(root, exist_ok=True)
    skip = {"admin", "local", "config"}
    dbs = [d for d in cli.list_database_names() if d not in skip]
    print("Databases found:", dbs)
    grand = 0
    for dbn in dbs:
        db = cli[dbn]
        ddir = os.path.join(root, dbn)
        os.makedirs(ddir, exist_ok=True)
        for coll in db.list_collection_names():
            docs = list(db[coll].find({}))
            with open(os.path.join(ddir, coll + ".json"), "w") as f:
                f.write(json_util.dumps(docs))
            grand += len(docs)
            print(f"  {dbn}.{coll}: {len(docs)} docs")
    print(f"\nTOTAL DOCS BACKED UP: {grand}")
    print("BACKUP FOLDER:", root)


if __name__ == "__main__":
    main()
