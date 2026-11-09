"""Seed demo marketplace listings (preview only) for manual screenshots and help videos. Run with --clean to remove them."""
import base64
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

import fitz
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
TAG = "manual_demo"

if "--clean" in sys.argv:
    print("listings", db.mkt_listings.delete_many({"source": TAG}).deleted_count,
          "media", db.mkt_media.delete_many({"import_id": TAG}).deleted_count)
    sys.exit()

v = db.vendors.find_one({"email": "northfield@demo.pmcmanagers.com"})
doc = fitz.open("/tmp/test_catalogue.pdf")
pics = []
for p in range(2):
    raw = doc.extract_image(doc[p].get_images()[0][0])["image"]
    mid = secrets.token_urlsafe(18)
    db.mkt_media.insert_one({"_id": mid, "owner": str(v["_id"]), "kind": "photo", "name": f"demo{p}.jpg", "mime": "image/jpeg",
                             "size": len(raw), "data_b64": base64.b64encode(raw).decode(), "import_id": TAG})
    pics.append(mid)
now = datetime.now(timezone.utc)
base = {"category": "Pumps & piping", "quantity": 1, "unit": "unit", "currency": "USD", "location": "Demo", "image_url": "", "documents": [],
        "eligibility": "verified_buyers", "source": TAG, "seller_id": str(v["_id"]), "seller_name": v["company_name"],
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "reserve_price": None, "min_increment": 100}
rows = [
    {**base, "title": "Demo: Centrifugal process water pump", "description": "Demo listing for the training manual. Stainless steel centrifugal pump.",
     "photos": [pics[0]], "sale_modes": ["auction"], "start_price": 4000, "buy_now_price": None,
     "closes_at": (now + timedelta(days=14)).isoformat(), "status": "live"},
    {**base, "title": "Demo: Stainless piping skid", "description": "Demo listing for the training manual. Pre-assembled piping skid with valves.",
     "photos": [pics[1]], "sale_modes": ["fixed", "best_offer"], "start_price": None, "buy_now_price": 12500,
     "closes_at": (now + timedelta(days=10)).isoformat(), "status": "live"},
    {**base, "title": "Demo: Pump spare parts kit", "description": "Demo listing waiting for approval.", "photos": [pics[0]],
     "sale_modes": ["fixed"], "start_price": None, "buy_now_price": 900, "closes_at": None, "status": "pending"},
]
db.mkt_listings.insert_many(rows)
print("seeded", len(rows))
