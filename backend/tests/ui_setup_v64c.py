# UI fixture helper for v64c: `python ui_setup_v64c.py setup|member_sign REF|cleanup REF`
import sys
sys.path.insert(0, "/app/backend/tests")
import test_v64c_opening_record as T  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

cmd = sys.argv[1]
if cmd == "setup":
    f = T.setup
    fn = getattr(f, "_get_wrapped_function", None)
    gen = (fn() if fn else f.__wrapped__)()
    next(gen)
    T.TestA_Setup().test_bids_and_committee()
    print(T.REF, T.S["c"], T.M_EMAIL, T.S["mid"])
elif cmd == "member_sign":
    ref, email = sys.argv[2], sys.argv[3]
    s = T.requests.Session()
    r = s.post(f"{T.API}/staff/auth/login", json={"email": email, "password": T.STAFF_PW, "active_role": "committee_member"})
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    r = s.post(f"{T.API}/bid-opening/{ref}/approve", json={"stage": "technical", "signer_name": "TEST UI Member", "consent": True})
    print(r.status_code, r.text[:300])
elif cmd == "cleanup":
    ref = sys.argv[2]
    rid = ref.split("_")[-1]
    db = T.DB
    db.uploads.delete_many({"key": {"$regex": f"TESTREC{rid}"}})
    for c in ("bids", "notices", "committees", "opening_records"):
        db[c].delete_many({"notice_ref": ref})
    db.vendors.delete_many({"email": f"test_sealrecvb_{rid.lower()}@example.com"})
    db.admin_users.delete_many({"email": f"test_sealrecmem_{rid.lower()}@example.com"})
    print("cleaned", ref)
