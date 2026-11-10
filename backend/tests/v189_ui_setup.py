# v189 UI seed: one pending + one legacy-approved (no user) TEST_ buyer application. Usage: create | clean
import json
import secrets
import sys
from datetime import datetime, timezone

from bson import ObjectId
from dotenv import dotenv_values
from pymongo import MongoClient

BE = dotenv_values("/app/backend/.env")
db = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
F = "/tmp/v189.json"

if sys.argv[1] == "create":
    tag = secrets.token_hex(3)
    now = datetime.now(timezone.utc).isoformat()
    base = {"org_type": "private", "country": "IN", "contact_name": "TEST Contact", "ip": "test", "created_at": now}
    p = db.buyer_applications.insert_one({**base, "org_name": f"TEST_UI Pending {tag}", "email": f"test_uip_{tag}@example.com", "status": "pending"}).inserted_id
    code = f"TESTUIOLD{tag.upper()}"
    db.tenants.insert_one({"code": code, "name": "TEST_UI Old", "source": "buyer_application", "is_active": True})
    o = db.buyer_applications.insert_one({**base, "org_name": f"TEST_UI Old {tag}", "email": f"test_uio_{tag}@example.com", "status": "approved", "tenant_code": code}).inserted_id
    d = {"pending": str(p), "old": str(o), "pending_email": f"test_uip_{tag}@example.com", "old_email": f"test_uio_{tag}@example.com", "old_code": code}
    json.dump(d, open(F, "w"))
    print(json.dumps(d))
elif sys.argv[1] == "token":
    import jwt
    from datetime import timedelta
    u = db.admin_users.find_one({"email": sys.argv[2]})
    print(jwt.encode({"sub": str(u["_id"]), "email": u["email"], "portal": "buyer", "jti": u["pwd_reset_jti"], "type": "pwd_reset",
                      "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=7)}, BE["JWT_SECRET"], algorithm="HS256"))
else:
    d = json.load(open(F))
    codes = []
    for k in ("pending", "old"):
        a = db.buyer_applications.find_one({"_id": ObjectId(d[k])})
        if a and a.get("tenant_code"):
            codes.append(a["tenant_code"])
        db.buyer_applications.delete_one({"_id": ObjectId(d[k])})
    for c in set(codes):
        r = db.admin_users.delete_many({"tenant_id": c, "source": "buyer_application"})
        db.tenants.delete_one({"code": c, "source": "buyer_application"})
        print("cleaned", c, r.deleted_count)
