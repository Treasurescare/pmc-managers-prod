# Seed/clean a TEST notice for consortium UI testing: python seed_ui_consortium.py seed|clean
import sys
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient

ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
REF = "TEST-UICONS-1"
now = lambda **kw: (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()
CRIT = [
    {"id": "mpturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte", "threshold": 1000000,
     "unit": "USD", "kind": "must_pass", "consortium_rule": "lead", "proof_required": False},
    {"id": "mpiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "each"},
    {"id": "scstaff1", "title": "Qualified key staff", "answer_type": "number", "operator": "gte", "threshold": 5, "unit": "staff",
     "kind": "scored", "max_points": 10, "scoring": "auto", "full_points_at": 15, "consortium_rule": "combined"},
]


def clean():
    for c in ("bids", "notices", "consortia", "committees", "opening_records"):
        DB[c].delete_many({"notice_ref": REF})
    DB.notifications.delete_many({"related_notice_ref": REF})
    DB.agents.delete_many({"email": "test_ui_draft@example.com"})


if sys.argv[1] == "seed":
    clean()
    DB.notices.insert_one({"notice_ref": REF, "title": "TEST UI consortium tender", "is_published": True, "kyc_bypass": True,
                           "category": "", "budget_amount": 100000.0, "budget_currency": "USD", "description": "TEST UI consortium",
                           "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"}, "tender_criteria": CRIT,
                           "consortium_allowed": True, "consortium_max_members": 3, "created_at": now(),
                           "submission_deadline": now(days=3), "bid_opening_date": now(days=4)})
    print("seeded", REF)
else:
    clean()
    print("cleaned")
