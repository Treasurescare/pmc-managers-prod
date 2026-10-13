"""v52cs — zero-EMD bids must not be stuck at "Supplier · Pay EMD".

Reproduces the production incident (bid PMC-BID-2026-00047): vendor
completed all 5 wizard steps, notice had EMD = 0, backend stored
status="submitted" — and the pipeline could never advance because the
escrow-agent transition required prev_status == "emd_paid".

Covers:
1. Escrow agent CAN accept a zero-EMD bid straight from "submitted"
   (→ escrow_accepted).
2. Escrow agent CANNOT accept a bid WITH EMD due from "submitted"
   (pipeline guard intact → 400).
"""
from __future__ import annotations
import os
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    s.headers.update({
        "Authorization": f"Bearer {data['token']}",
        "X-CSRF-Token": data.get("csrf_token") or "",
    })
    if data.get("csrf_token") and not s.cookies.get("csrf_token"):
        s.cookies.set("csrf_token", data["csrf_token"])
    return s


def _mongo():
    from dotenv import dotenv_values
    cfg = dotenv_values("/app/backend/.env")
    client = MongoClient(cfg["MONGO_URL"])
    return client[cfg["DB_NAME"]]


def test_zero_emd_bid_escrow_can_accept_from_submitted():
    escrow = _login("escrow@pmcmanagers.com", "Escrow@123")
    db = _mongo()
    bid_id = ObjectId()
    db.bids.insert_one({
        "_id": bid_id,
        "bid_ref": "PMC-BID-TEST-ZEROEMD",
        "notice_ref": "PMC-NOT-TEST",
        "vendor_ref": "PMC-SUP-TEST",
        "status": "submitted",
        "emd_due_amount": 0.0,
        "emd_paid_amount": 0.0,
        "is_demo": True,
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00",
    })
    try:
        r = escrow.post(f"{API}/bids/{bid_id}/decision",
                        json={"role": "escrow_agent", "action": "accept"},
                        timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "escrow_accepted"
        doc = db.bids.find_one({"_id": bid_id})
        assert doc["status"] == "escrow_accepted"
    finally:
        db.bids.delete_one({"_id": bid_id})


def test_emd_due_bid_escrow_cannot_skip_payment():
    escrow = _login("escrow@pmcmanagers.com", "Escrow@123")
    db = _mongo()
    bid_id = ObjectId()
    db.bids.insert_one({
        "_id": bid_id,
        "bid_ref": "PMC-BID-TEST-EMDDUE",
        "notice_ref": "PMC-NOT-TEST",
        "vendor_ref": "PMC-SUP-TEST",
        "status": "submitted",
        "emd_due_amount": 500.0,   # EMD IS due — pipeline guard must hold
        "emd_paid_amount": 0.0,
        "is_demo": True,
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00",
    })
    try:
        r = escrow.post(f"{API}/bids/{bid_id}/decision",
                        json={"role": "escrow_agent", "action": "accept"},
                        timeout=15)
        assert r.status_code == 400, r.text
        assert "emd_paid" in r.text
        doc = db.bids.find_one({"_id": bid_id})
        assert doc["status"] == "submitted", "status must not have moved"
    finally:
        db.bids.delete_one({"_id": bid_id})
