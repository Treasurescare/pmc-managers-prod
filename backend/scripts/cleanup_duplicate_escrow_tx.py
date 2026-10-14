#!/usr/bin/env python3
"""One-shot cleanup — duplicate open escrow transactions.

Each bid must hold ONE open escrow transaction (pending / received /
awaiting_signatures). Rows created before the v51ap guard left some bids
with two open rows, which blocks new inbound EMD receipts (HTTP 409).

Keeps the NEWEST open row per duplicated bid and cancels the rest
(audit trail preserved). Dry-run by default; pass --apply to write.

Usage:
    cd /app/backend
    python scripts/cleanup_duplicate_escrow_tx.py
    python scripts/cleanup_duplicate_escrow_tx.py --apply
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import db
from models.base import now_iso
from audit import audit_log

OPEN = ["pending", "received", "awaiting_signatures"]


async def main(apply: bool) -> None:
    pipeline = [
        {"$match": {"status": {"$in": OPEN}}},
        {"$group": {"_id": "$bid_ref", "count": {"$sum": 1},
                     "tx_ids": {"$push": "$_id"},
                     "statuses": {"$push": "$status"}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    found = 0
    cancelled = 0
    async for row in db.escrow_transactions.aggregate(pipeline):
        found += 1
        tx_ids = sorted(row["tx_ids"])  # ObjectIds sort by creation time
        keep, extras = tx_ids[-1], tx_ids[:-1]
        print(f"{row['_id']}: {row['count']} open rows {row['statuses']} "
              f"— keep {keep}, cancel {len(extras)}")
        for tid in extras:
            if apply:
                await db.escrow_transactions.update_one(
                    {"_id": tid},
                    {"$set": {"status": "cancelled", "updated_at": now_iso()},
                     "$push": {"audit_trail": {
                         "at": now_iso(),
                         "by": "system:cleanup-script",
                         "event": "cancelled",
                         "comment": "Duplicate cleanup — kept newest open row"}}})
                await audit_log("escrow.tx_cancel",
                                 {"id": "system", "email": "system:cleanup-script"},
                                 "escrow_tx", str(tid), {"bid_ref": row["_id"]})
            cancelled += 1
            print(f"  {'CANCELLED' if apply else 'would cancel'} {tid}")
    print(f"\n{'APPLIED' if apply else 'DRY-RUN'}: {found} duplicated bid(s), "
          f"{cancelled} row(s) {'cancelled' if apply else 'to cancel'}")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
