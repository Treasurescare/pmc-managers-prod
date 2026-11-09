# Edge probes for marketplace (iteration 180): best-offer deadline enforcement
import sys
sys.path.insert(0, "/app/backend/tests")
from test_t180_marketplace import API, mdb, vlogin, alogin, mk, future, ObjectId, requests

v1 = vlogin("testvendor@pmcmanagers.com", "Vendor@12345")
v2 = vlogin("test_mkt_v2_t180@example.com", "Vendor@12345")
adm = alogin("adminsupport@pmcmanagers.com", "Admin@12345")
lid = mk(v1, adm, "TEST_offer_deadline", ["best_offer"], closes_at=future(), eligibility="any_verified")
mdb.mkt_listings.update_one({"_id": ObjectId(lid)}, {"$set": {"closes_at": "2020-01-01T00:00:00+00:00"}})
r = v2.post(f"{API}/listings/{lid}/offer", json={"amount": 10})
print("offer after deadline:", r.status_code, r.text[:120])
print("still in public browse:", any(x["id"] == lid for x in requests.get(f"{API}/listings").json()["items"]))
# fixed+best_offer w/out deadline? best_offer requires closes_at; fixed-only listing has no closes -> fine
# public detail leaks decided_by?
d = requests.get(f"{API}/listings/{lid}").json()
print("public keys:", sorted(d.keys()))
# negative/zero offer
print("zero offer:", v2.post(f"{API}/listings/{lid}/offer", json={"amount": 0}).status_code)
