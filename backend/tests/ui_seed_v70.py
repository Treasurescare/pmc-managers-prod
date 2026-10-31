# v70 UI seed/cleanup helper: `python tests/ui_seed_v70.py seed|clean RID`
import sys
import requests
from bson import ObjectId
import test_v70_partner_profile_cards as t

mode, rid = sys.argv[1], sys.argv[2]
t.RID = rid
t.SUP = {k: f"test_sup_{k}_{rid}@example.com" for k in ("one",)}
if mode == "clean":
    t._cleanup()
    t.DB.partner_commission_settings.delete_one({"key": "leaderboard"})
    if t.DB.agents.count_documents({}) == 0:
        t.DB.counters.delete_one({"name": "partner_code"})
    print("cleaned")
    sys.exit()
t.S["admin"] = t._admin()
s, aid, email = t._partner("a")
r = s.post(f"{t.API}/agents/me/suppliers", json={"company_name": f"TEST Supplier one {rid}", "email": t.SUP["one"], "mobile": "+91 9876543210"})
rid1 = r.json()["id"]
ctok = t.DB.registrations.find_one({"_id": ObjectId(rid1)})["partner_consent_token"]
requests.post(f"{t.API}/supplier-invites/{ctok}", json={"decision": "self", "signer_name": "TEST Self", "consents": {"data_privacy": True}})
t.DB.registrations.update_one({"_id": ObjectId(rid1)}, {"$set": {"registered_address": "1 TEST Road", "country": "IN",
                                                                "registration_number": f"TESTREG{rid}", "legal_entity_type": "Private Limited", "status": "submitted"}})
print("approve", t.S["admin"].post(f"{t.API}/registrations/{rid1}/decision", json={"action": "approve"}).status_code)
t.DB.partner_commission_settings.update_one({"key": "leaderboard"}, {"$set": {"show_names": False}}, upsert=True)
je = f"test_partner_j_{rid}@example.com"
requests.post(f"{t.API}/agents/register", json={"email": je, "name": "TEST Partner j"})
print("A", email, aid, t.DB.agents.find_one({"_id": ObjectId(aid)})["partner_code"])
print("J", je, t.DB.agents.find_one({"email": je})["invite_token"])
