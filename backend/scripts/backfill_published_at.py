"""v52cu — Backfill `published_at` for notices where `is_published=True`
but `published_at` is null/empty.

Why: the public landing page sorts by `published_at` DESC. A null value
sinks the row to the bottom, so a published-but-never-stamped notice can
"disappear" below the fold. Set `published_at` to `created_at` as the
best-available timestamp.

Run from /app/backend:
    python -m scripts.backfill_published_at

Idempotent — can be run on preview and production safely.
"""
from __future__ import annotations
import asyncio
from db import db


async def main() -> None:
    q = {"is_published": True,
         "$or": [{"published_at": None}, {"published_at": ""}, {"published_at": {"$exists": False}}]}
    total = await db.notices.count_documents(q)
    print(f"[backfill] notices needing published_at: {total}")
    patched = 0
    async for n in db.notices.find(q):
        ca = n.get("created_at")
        if not ca:
            continue
        await db.notices.update_one({"_id": n["_id"]}, {"$set": {"published_at": ca}})
        patched += 1
        print(f"  · {n.get('notice_ref')}  →  published_at={ca}")
    print(f"[backfill] patched {patched}/{total} rows.")


if __name__ == "__main__":
    asyncio.run(main())
