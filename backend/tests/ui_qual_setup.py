# Helper for v72c UI testing: `setup` creates TEST-QUI notice (criteria, committee1/2, 2 zero-EMD bids, technical opened) + TEST-QUIVT vendor draft; `cleanup` removes.
import sys
import json
sys.path.insert(0, "/app/backend/tests")
import test_v72c_criteria_stage2 as T  # noqa: E402

REF, VT = "TEST-QUI-1", "TEST-QUIVT-1"


def cleanup():
    for r in (REF, VT):
        T.DB.bids.delete_many({"notice_ref": r}); T.DB.notices.delete_many({"notice_ref": r})
        T.DB.committees.delete_many({"notice_ref": r}); T.DB.opening_records.delete_many({"notice_ref": r})
    T.DB.uploads.delete_many({"key": {"$regex": "TESTQ2UI"}})


def setup():
    cleanup()
    T.E2E = REF
    T.RID = "UI"
    D = T.DB
    D.notices.insert_one({"notice_ref": REF, "title": "TEST UI stage2 tender", "is_published": True, "kyc_bypass": True, "category": "",
                          "budget_amount": 100000.0, "budget_currency": "USD", "description": T.DESC,
                          "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"},
                          "tender_criteria": [T.MUST, T.ISO, T.STAFF, T.METH], "submission_deadline": T._now(days=3),
                          "bid_opening_date": T._now(days=4), "created_at": T._now()})
    tv = str(D.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
    D.notices.insert_one({"notice_ref": VT, "title": "TEST UI vendor draft tender", "is_published": False, "origin": "vendor",
                          "prepared_by_vendor_id": tv, "review_status": "draft", "description": T.DESC, "category": "",
                          "budget_amount": 5000.0, "budget_currency": "USD", "submission_deadline": T._now(days=9), "created_at": T._now()})
    c1 = str(D.admin_users.find_one({"email": "committee1@demo.pmcmanagers.com"})["_id"])
    c2 = str(D.admin_users.find_one({"email": "committee2@demo.pmcmanagers.com"})["_id"])
    D.committees.insert_one({"notice_ref": REF, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2, "votes": [], "created_at": T._now()})
    import requests
    def vl(e):
        s = requests.Session(); r = s.post(f"{T.API}/vendor/auth/login", json={"email": e, "password": T.DEMO_PW})
        s.headers["X-CSRF-Token"] = r.json().get("csrf_token") or ""; return s
    def sl(e):
        s = requests.Session(); r = s.post(f"{T.API}/staff/auth/login", json={"email": e, "password": T.DEMO_PW, "active_role": "committee_member"})
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]; return s
    g = T._bid(vl("northfield@demo.pmcmanagers.com"), 2500000, 10, 9000)
    b = T._bid(vl("brightwater@demo.pmcmanagers.com"), 400000, 20, 8000)
    D.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": T._now(hours=-3), "bid_opening_date": T._now(hours=-2)}})
    for e, n in (("committee1@demo.pmcmanagers.com", "Committee One"), ("committee2@demo.pmcmanagers.com", "Committee Two")):
        r = sl(e).post(f"{T.API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": n, "consent": True})
        print(r.status_code, r.text[:150])
    refs = {str(x["_id"]): x["bid_ref"] for x in D.bids.find({"notice_ref": REF})}
    print(json.dumps({"good": refs[g], "bad": refs[b]}))


{"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
