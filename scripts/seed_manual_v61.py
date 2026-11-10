"""Seed clearly labelled DEMO data (preview only) for the v61 manuals: buyer org + users, marketplace listings, bids,
an order with delivery, watchlist, notifications, pending buyer application and team invite. --clean removes it all."""
import io
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
TAG = "manual_demo_v61"
PW = "Demo@Pmc2026"
BUYER, MATE, PEND = "buyer@demo.pmcmanagers.com", "buyer.colleague@demo.pmcmanagers.com", "newbuyer@demo.pmcmanagers.com"
CODE = "DEMOBUYERCO"

if "--clean" in sys.argv:
    ids = [l["_id"] for l in db.mkt_listings.find({"source": TAG})]
    uids = [str(u["_id"]) for u in db.admin_users.find({"source_tag": TAG})]
    print("listings", db.mkt_listings.delete_many({"source": TAG}).deleted_count,
          "bids", db.mkt_bids.delete_many({"listing_id": {"$in": ids}}).deleted_count,
          "orders", db.mkt_orders.delete_many({"listing_id": {"$in": ids}}).deleted_count,
          "watch", db.mkt_watch.delete_many({"listing_id": {"$in": ids}}).deleted_count,
          "media", db.mkt_media.delete_many({"import_id": TAG}).deleted_count,
          "notifs", db.notifications.delete_many({"tag": TAG}).deleted_count,
          "users", db.admin_users.delete_many({"source_tag": TAG}).deleted_count,
          "apps", db.buyer_applications.delete_many({"source_tag": TAG}).deleted_count,
          "team", db.buyer_team_requests.delete_many({"source_tag": TAG}).deleted_count,
          "tenants", db.tenants.delete_many({"code": CODE, "source_tag": TAG}).deleted_count, len(uids))
    sys.exit()

now = datetime.now(timezone.utc)
iso = lambda d=0, h=0: (now + timedelta(days=d, hours=h)).isoformat()  # noqa: E731
pw = bcrypt.hashpw(PW.encode(), bcrypt.gensalt()).decode()
v = db.vendors.find_one({"email": "northfield@demo.pmcmanagers.com"})


def photo(label, col):
    im = Image.new("RGB", (1200, 900), col)
    d = ImageDraw.Draw(im)
    d.rectangle([260, 250, 940, 650], outline="white", width=14)
    d.ellipse([480, 330, 720, 570], outline="white", width=14)
    d.text((40, 40), f"DEMO PHOTO - {label}", fill="white")
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    import base64
    mid = secrets.token_urlsafe(18)
    db.mkt_media.insert_one({"_id": mid, "owner": str(v["_id"]), "kind": "photo", "name": f"{label}.jpg", "mime": "image/jpeg",
                             "size": len(b.getvalue()), "data_b64": base64.b64encode(b.getvalue()).decode(), "import_id": TAG})
    return mid


db.tenants.update_one({"code": CODE}, {"$setOnInsert": {"code": CODE, "name": "DEMO Buyer Co (sample)", "kind": "corporate", "country": "IN", "org_type": "private",
                                                       "primary_contact_email": BUYER, "is_active": True, "source": "buyer_application",
                                                       "created_at": iso(), "source_tag": TAG}}, upsert=True)
prof = {"name": "Asha Demo", "phone": "9800000001", "phone_code": "91", "country_code": "IN", "country": "India", "state_code": "RJ",
        "state_name": "Rajasthan", "city": "Abhaneri", "address": "1 Demo Street (sample)", "zip": None, "org_name": "DEMO Buyer Co (sample)"}
for email, name, admin in ((BUYER, "Asha Demo (buyer)", True), (MATE, "Ravi Demo (colleague)", False)):
    db.admin_users.update_one({"email": email}, {"$set": {"email": email, "name": name, "password_hash": pw, "roles": ["buyer"], "role": "buyer",
                                                          "account_type": "buyer", "tenant_id": CODE, "is_active": True, "email_verified": True,
                                                          "is_org_admin": admin, "buyer_profile": {**prof, "name": name}, "source_tag": TAG, "created_at": iso()}}, upsert=True)
u = db.admin_users.find_one({"email": BUYER})
pid = db.admin_users.find_one_and_update({"email": PEND}, {"$set": {"email": PEND, "name": "Neha Demo (new buyer)", "password_hash": pw, "roles": ["buyer"], "role": "buyer",
                                                                    "account_type": "buyer", "is_active": True, "email_verified": True, "is_org_admin": True,
                                                                    "source_tag": TAG, "created_at": iso()}}, upsert=True, return_document=True)
app = db.buyer_applications.insert_one({"org_name": "Neha Demo (new buyer)", "org_type": "other", "country": "IN", "contact_name": "Neha Demo (new buyer)", "email": PEND,
                                        "phone": "91 9800000003", "status": "pending", "source": "self_register", "email_verified": True, "created_at": iso(-1),
                                        "profile": {**prof, "name": "Neha Demo"}, "user_id": str(pid["_id"]), "source_tag": TAG})
db.admin_users.update_one({"_id": pid["_id"]}, {"$set": {"tenant_id": f"PENDING-{app.inserted_id}"}})
db.buyer_applications.insert_one({"org_name": "DEMO Buyer Co (sample)", "org_type": "private", "country": "IN", "contact_name": "Asha Demo", "email": BUYER,
                                  "phone": "91 9800000001", "status": "approved", "tenant_code": CODE, "source": "admin_added", "email_verified": True,
                                  "signin_status": "sent", "signin_email": BUYER, "signin_sent_at": iso(-3), "signin_users": [BUYER, MATE], "created_at": iso(-4), "source_tag": TAG})
db.buyer_team_requests.insert_one({"tenant_code": CODE, "org_name": "DEMO Buyer Co (sample)", "name": "Karan Demo (invited)", "email": "karan@demo.pmcmanagers.com",
                                   "phone": "9800000004", "status": "pending", "invited_by": BUYER, "created_at": iso(-1), "source_tag": TAG})

base = {"category": "Pumps & piping", "quantity": 1, "unit": "unit", "currency": "USD", "location": "Pune, India (demo)", "image_url": "", "documents": [],
        "eligibility": "verified_buyers", "source": TAG, "seller_id": str(v["_id"]), "seller_name": v["company_name"], "created_at": iso(-5),
        "updated_at": iso(-5), "reserve_price": None, "min_increment": 100, "approved_at": iso(-4), "approved_by": "adminsupport@pmcmanagers.com"}
L = [
    {**base, "title": "DEMO: Centrifugal process water pump", "description": "Sample listing for the training manual. Stainless steel centrifugal pump, 45 m3/h.",
     "photos": [photo("pump", "#1f4e46")], "sale_modes": ["auction"], "start_price": 4000, "buy_now_price": None, "closes_at": iso(0, 3), "status": "live"},
    {**base, "title": "DEMO: Stainless piping skid", "description": "Sample listing for the training manual. Pre-assembled piping skid with valves.",
     "photos": [photo("skid", "#6b4f1d")], "sale_modes": ["fixed", "best_offer"], "start_price": None, "buy_now_price": 12500, "closes_at": iso(10), "status": "live"},
    {**base, "title": "DEMO: Diesel generator 250 kVA", "description": "Sample listing for the training manual. Sold at auction.",
     "photos": [photo("generator", "#2b3a55")], "sale_modes": ["auction"], "start_price": 15000, "buy_now_price": None, "closes_at": iso(-1), "status": "sold"},
    {**base, "title": "DEMO: Industrial air compressor", "description": "Sample listing waiting for PMC approval.", "photos": [photo("compressor", "#5a2a2a")],
     "sale_modes": ["fixed"], "start_price": None, "buy_now_price": 6800, "closes_at": None, "status": "pending", "approved_at": None},
    {**base, "title": "DEMO: Control valve set", "description": "Sample listing waiting for PMC approval.", "photos": [photo("valves", "#3d4d1f")],
     "sale_modes": ["auction"], "start_price": 900, "buy_now_price": None, "closes_at": iso(7), "status": "pending", "approved_at": None},
]
ids = db.mkt_listings.insert_many(L).inserted_ids
me = {"id": str(u["_id"]), "kind": "buyer", "name": "DEMO Buyer Co (sample)", "email": BUYER}
other = {"id": "demo-other", "kind": "buyer", "name": "Other demo buyer", "email": "other@demo.pmcmanagers.com"}
db.mkt_bids.insert_many([
    {"listing_id": ids[0], "kind": "bid", "amount": 4200, "bidder": me, "created_at": iso(0, -5)},
    {"listing_id": ids[0], "kind": "bid", "amount": 4400, "bidder": other, "created_at": iso(0, -4)},
    {"listing_id": ids[1], "kind": "offer", "amount": 11800, "bidder": me, "status": "open", "created_at": iso(0, -2)},
    {"listing_id": ids[2], "kind": "bid", "amount": 16200, "bidder": me, "created_at": iso(-2)}])
db.mkt_orders.insert_one({"listing_id": ids[2], "title": L[2]["title"], "amount": 16200, "currency": "USD", "via": "auction", "buyer": me,
                          "seller_id": str(v["_id"]), "seller_name": v["company_name"], "pmc_fee": 324, "seller_net": 15876, "status": "paid",
                          "paid_at": iso(-1), "payout_status": "due", "delivery_status": "dispatched", "delivery_note": "Truck DEMO-42, ETA 2 days",
                          "dispatched_at": iso(0, -6), "created_at": iso(-1)})
db.mkt_watch.insert_many([{"user_id": str(u["_id"]), "email": BUYER, "listing_id": ids[0], "created_at": iso(-1)},
                          {"user_id": str(u["_id"]), "email": BUYER, "listing_id": ids[1], "created_at": iso(-1)}])
for s, b, link, read in [("You have been outbid \u2014 DEMO: Centrifugal process water pump", "<p>A higher bid of USD 4,400.00 was placed.</p>", f"/market/{ids[0]}", False),
                         ("Closing in 58 minutes \u2014 DEMO: Centrifugal process water pump", "<p>The auction on your watchlist closes soon.</p>", f"/market/{ids[0]}", False),
                         ("Order dispatched \u2014 DEMO: Diesel generator 250 kVA", "<p>The seller marked your order as dispatched. Truck DEMO-42.</p>", "/buyer/orders", False),
                         ("Payment received \u2014 DEMO: Diesel generator 250 kVA", "<p>We received USD 16,200.00.</p>", "/buyer/payments", True),
                         ("You won the auction \u2014 DEMO: Diesel generator 250 kVA", "<p>Please pay to complete the purchase.</p>", "/buyer/orders", True)]:
    db.notifications.insert_one({"user_id": str(u["_id"]), "user_email": BUYER, "subject": s, "body": b, "link": link, "read": read, "created_at": iso(), "tag": TAG})
print("seeded", [str(i) for i in ids])
