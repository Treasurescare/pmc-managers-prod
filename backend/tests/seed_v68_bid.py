# Creates a TEST bid for the ui68 vendor (partner-stamped) for admin bid-detail UI check.
import sys
sys.path.insert(0, "/app/backend/tests")
from datetime import datetime, timedelta, timezone  # noqa: E402
import test_v68_partner_reassign_board as t  # noqa: E402

NOTICE = "TEST-NTC-ui68"
START = datetime.now(timezone.utc).isoformat()
s = t.requests.Session()
r = s.post(f"{t.API}/vendor/auth/login", json={"email": "test_sup_two_ui68@example.com", "password": "VendorPw@12345"})
vid = r.json()["id"]
s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
t.DB.vendors.update_one({"email": "test_sup_two_ui68@example.com"}, {"$set": {"kyc_status": "verified"}})
t.DB.notices.insert_one({"notice_ref": NOTICE, "title": "TEST notice ui68", "is_published": True, "kyc_bypass": True,
                         "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
                         "budget_amount": 0, "emd_config": {}, "created_at": START})
docs = []
for kind in ("technical", "commercial"):
    key = f"bid-docs/TESTui68/{kind}.pdf"
    t.DB.uploads.insert_one({"key": key, "sealed": True, "owner_vendor_id": vid, "created_at": START})
    docs.append({"kind": kind, "key": key, "filename": f"{kind}.pdf", "size_bytes": 10, "uploaded_at": START})
r = s.post(f"{t.API}/bids", json={"notice_ref": NOTICE, "price_amount": 1000, "price_currency": "USD", "documents": docs})
print(r.status_code, str(t.DB.bids.find_one({"notice_ref": NOTICE})["_id"]))
