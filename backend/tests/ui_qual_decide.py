# Helper (iteration 150): after ui_qual_setup.py setup, committee1 raises a doubt on the "good" bid and disqualifies it so the UI can verify doubt buttons are hidden.
import sys
import requests
sys.path.insert(0, "/app/backend/tests")
import test_v72c_criteria_stage2 as T  # noqa: E402

REF = "TEST-QUI-1"
T.DB.notices.update_one({"notice_ref": REF}, {"$set": {"tenant_id": "PMC-KZ-01"}})
s = requests.Session()
r = s.post(f"{T.API}/staff/auth/login", json={"email": "committee1@demo.pmcmanagers.com", "password": T.DEMO_PW, "active_role": "committee_member"})
s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
q = s.get(f"{T.API}/tender-criteria/{REF}/qualification").json()
bids = q.get("bids") or []
print([(b.get("bid_ref"), b.get("status"), b.get("decision")) for b in bids])
good = next(b for b in bids if b.get("bid_ref") == sys.argv[1])
bid_id = good.get("bid_id")
print(s.post(f"{T.API}/tender-criteria/{REF}/bids/{bid_id}/doubt", json={"criterion_id": "mpturn01", "reason": "TEST doubt"}).text)
print(s.post(f"{T.API}/tender-criteria/{REF}/bids/{bid_id}/resolve", json={"decision": "disqualify", "note": "TEST disqualified"}).text)
print(s.post(f"{T.API}/tender-criteria/{REF}/bids/{bid_id}/doubt", json={"criterion_id": "mpturn01", "reason": "again"}).status_code)
