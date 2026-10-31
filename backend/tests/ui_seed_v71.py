# v71 UI seed/cleanup helper: `python tests/ui_seed_v71.py seed|clean RID`
import sys
import test_v69_partner_statements_login as t

mode, rid = sys.argv[1], sys.argv[2]
t.RID = rid
if mode == "clean":
    t._cleanup()
    t.DB.agents.delete_many({"email": {"$regex": f"^test_.*{rid}@example.com$"}})
    t.DB.registrations.delete_many({"email": {"$regex": f"^test_.*{rid}@example.com$"}})
    if t.DB.agents.count_documents({}) == 0:
        t.DB.counters.delete_one({"name": "partner_code"})
    print("cleaned")
    sys.exit()
t.S["admin"] = t._admin()
s, aid, email = t._partner("ui")
print("A", email, aid, t.DB.agents.find_one({"_id": __import__("bson").ObjectId(aid)})["partner_code"])
r = t.S["admin"].post(f"{t.API}/admin/agents/invite", json={"email": f"test_partner_inv_{rid}@example.com", "name": f"TEST Inv {rid}"})
print("INV", r.json()["id"])
