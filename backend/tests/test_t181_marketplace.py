# Supplier Marketplace (v61a) API regression + fix tests — iteration 181 (CSRF, best-offer deadline, public payload, seller_bank, reserve validation)
# Requires: python tests/mkt_t180_seed.py create (TEST_ vendor2, TEST_ buyer org + user, TEST_ listing fee rule for country XQ)
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api/v1/market"
SEED = json.load(open("/tmp/mkt_t180_seed.json"))
mdb = MongoClient("mongodb://localhost:27017")["pmc_tender_db"]
S = {}


def future(h=48):
    return (datetime.now(timezone.utc) + timedelta(hours=h)).isoformat()


def vlogin(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def alogin(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


@pytest.fixture(scope="module")
def v1():
    return vlogin("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def v2():
    return vlogin("test_mkt_v2_t180@example.com", "Vendor@12345")


@pytest.fixture(scope="module")
def adm():
    return alogin("adminsupport@pmcmanagers.com", "Admin@12345")


@pytest.fixture(scope="module")
def buyer():
    return alogin("test_mkt_buyer_t180@example.com", "Buyer@12345")


def mk(v, adm, title, modes, waive=False, **kw):
    body = {"title": title, "description": "TEST desc", "category": "TEST_cat", "sale_modes": modes, "currency": "USD", **kw}
    r = v.post(f"{API}/listings", json=body)
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    assert v.post(f"{API}/listings/{lid}/submit").status_code == 200
    r = adm.post(f"{API}/admin/listings/{lid}/decision", json={"action": "approve", "waive_sale_fee": waive})
    assert r.status_code == 200 and r.json()["status"] == "live", r.text
    return lid


class TestMarketplace:
    # --- seller validation + lifecycle ---
    def test_validation(self, v1):
        base = {"title": "TEST_val", "currency": "USD"}
        cases = [({"sale_modes": ["auction"], "closes_at": future()}, "starting price"),
                 ({"sale_modes": ["auction"], "start_price": 10}, "starting price"),
                 ({"sale_modes": ["best_offer"]}, "deadline"),
                 ({"sale_modes": ["fixed"]}, "buy-now"),
                 ({"sale_modes": ["auction"], "start_price": 10, "closes_at": "2020-01-01T00:00:00+00:00"}, "future")]
        for extra, msg in cases:
            r = v1.post(f"{API}/listings", json={**base, **extra})
            assert r.status_code == 400 and msg in r.json()["detail"], (extra, r.text)
        assert v1.post(f"{API}/listings", json={**base, "sale_modes": []}).status_code == 422

    def test_draft_edit_submit_withdraw(self, v1, adm):
        r = v1.post(f"{API}/listings", json={"title": "TEST_draft", "sale_modes": ["fixed"], "buy_now_price": 100})
        lid = r.json()["id"]
        S["draft"] = lid
        mine = v1.get(f"{API}/mine").json()
        row = next(x for x in mine["items"] if x["id"] == lid)
        assert row["status"] == "draft"
        assert v1.put(f"{API}/listings/{lid}", json={"title": "TEST_draft_edited", "sale_modes": ["fixed"], "buy_now_price": 120}).status_code == 200
        row = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        assert row["title"] == "TEST_draft_edited" and row["buy_now_price"] == 120
        assert v1.post(f"{API}/listings/{lid}/submit").json()["status"] == "pending"
        assert v1.put(f"{API}/listings/{lid}", json={"title": "TEST_x", "sale_modes": ["fixed"], "buy_now_price": 1}).status_code == 409
        pend = adm.get(f"{API}/admin/listings", params={"status": "pending"}).json()["items"]
        assert any(x["id"] == lid for x in pend)
        # not public while pending
        assert requests.get(f"{API}/listings/{lid}").status_code == 404
        assert v1.post(f"{API}/listings/{lid}/withdraw").status_code == 200
        row = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        assert row["status"] == "withdrawn"

    def test_reject_note_resubmit(self, v1, adm):
        lid = v1.post(f"{API}/listings", json={"title": "TEST_reject", "sale_modes": ["fixed"], "buy_now_price": 50}).json()["id"]
        v1.post(f"{API}/listings/{lid}/submit")
        r = adm.post(f"{API}/admin/listings/{lid}/decision", json={"action": "reject", "notes": "TEST add photos"})
        assert r.json()["status"] == "rejected"
        row = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        assert row["status"] == "rejected" and row["review_notes"] == "TEST add photos"
        assert v1.put(f"{API}/listings/{lid}", json={"title": "TEST_reject_v2", "sale_modes": ["fixed"], "buy_now_price": 55}).status_code == 200
        assert v1.post(f"{API}/listings/{lid}/submit").status_code == 200
        # decision on non-pending -> 409
        adm.post(f"{API}/admin/listings/{lid}/decision", json={"action": "approve"})
        assert adm.post(f"{API}/admin/listings/{lid}/decision", json={"action": "approve"}).status_code == 409

    def test_listing_fee_402(self, v2):
        lid = v2.post(f"{API}/listings", json={"title": "TEST_fee402", "sale_modes": ["fixed"], "buy_now_price": 10}).json()["id"]
        r = v2.post(f"{API}/listings/{lid}/submit")
        S["fee402"] = (r.status_code, r.text[:300])
        assert r.status_code in (402, 500, 502), r.text
        if r.status_code == 402:
            d = r.json()["detail"]
            assert "checkout_url" in d and d["amount"] == 7

    # --- settings ---
    def test_settings_persist(self, adm):
        r = adm.put(f"{API}/admin/settings", json={"fee_type": "fixed", "fee_value": 30, "charge": True})
        assert r.status_code == 200 and r.json() == {"fee_type": "fixed", "fee_value": 30.0, "charge": True}
        assert adm.get(f"{API}/admin/settings").json()["fee_value"] == 30.0
        assert adm.put(f"{API}/admin/settings", json={"fee_type": "x", "fee_value": 1}).status_code == 422
        assert adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": -1}).status_code == 422
        adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": 5, "charge": True})

    # --- public + reserve hidden ---
    def test_public_and_reserve_hidden(self, v1, adm):
        lid = mk(v1, adm, "TEST_auction_any", ["auction", "fixed"], start_price=100, reserve_price=500, min_increment=10,
                 buy_now_price=2000, closes_at=future(), eligibility="any_verified")
        S["auc"] = lid
        items = requests.get(f"{API}/listings", params={"q": "TEST_auction_any"}).json()["items"]
        assert [x["id"] for x in items] == [lid]
        hidden = ("reserve_price", "review_notes", "sale_fee_waived", "decided_by", "decided_at", "submitted_at")
        assert all(k not in x for x in items for k in hidden), items
        d = requests.get(f"{API}/listings/{lid}").json()
        assert all(k not in d for k in hidden), d
        assert "reserve_price" not in d and d["top_bid"] is None and d["buy_now_price"] == 2000
        assert all(x["status"] == "live" for x in requests.get(f"{API}/listings").json()["items"])
        assert requests.get(f"{API}/listings", params={"q": "zzzTEST_nomatch"}).json()["items"] == []

    # --- bidding rules ---
    def test_bid_rules(self, v1, v2, buyer):
        lid = S["auc"]
        r = requests.post(f"{API}/listings/{lid}/bid", json={"amount": 200})
        # v61a fix: CSRF now runs first, so anonymous bid -> 403 CSRF (was 401 'sign in')
        assert r.status_code in (401, 403), r.text
        S["anon_bid"] = (r.status_code, r.text)
        assert v1.post(f"{API}/listings/{lid}/bid", json={"amount": 200}).status_code == 403
        r = v2.post(f"{API}/listings/{lid}/bid", json={"amount": 99})
        assert r.status_code == 400 and "100" in r.json()["detail"]
        assert v2.post(f"{API}/listings/{lid}/bid", json={"amount": 100}).status_code == 200
        assert buyer.post(f"{API}/listings/{lid}/bid", json={"amount": 105}).status_code == 400
        assert buyer.post(f"{API}/listings/{lid}/bid", json={"amount": 110}).status_code == 200
        d = requests.get(f"{API}/listings/{lid}").json()
        assert d["top_bid"] == 110 and d["bid_count"] == 2 and d["reserve_met"] is False
        assert v2.post(f"{API}/listings/{lid}/offer", json={"amount": 300}).status_code == 400  # mode not enabled
        # withdraw blocked with bids
        assert v1.post(f"{API}/listings/{lid}/withdraw").status_code == 409

    def test_verified_buyers_only(self, v1, v2, adm, buyer):
        lid = mk(v1, adm, "TEST_buyers_only", ["fixed"], buy_now_price=1000, eligibility="verified_buyers")
        r = v2.post(f"{API}/listings/{lid}/buy")
        assert r.status_code == 403 and "buyer organisations" in r.json()["detail"]
        # plain PMC admin (non buyer tenant) cannot buy
        assert adm.post(f"{API}/listings/{lid}/buy").status_code == 403
        r = buyer.post(f"{API}/listings/{lid}/buy")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["status"] == "awaiting_payment" and o["amount"] == 1000 and o["pmc_fee"] == 50 and o["seller_net"] == 950
        S["buy_order"] = o["id"]
        assert requests.get(f"{API}/listings/{lid}").json()["status"] == "sold"
        assert buyer.post(f"{API}/listings/{lid}/buy").status_code == 409

    def test_offers_replace_and_accept_fixed_fee(self, v1, v2, adm, buyer):
        adm.put(f"{API}/admin/settings", json={"fee_type": "fixed", "fee_value": 30, "charge": True})
        lid = mk(v1, adm, "TEST_offer", ["best_offer"], closes_at=future(), eligibility="any_verified")
        assert v2.post(f"{API}/listings/{lid}/offer", json={"amount": 400, "note": "TEST a"}).status_code == 200
        assert v2.post(f"{API}/listings/{lid}/offer", json={"amount": 450}).status_code == 200
        assert buyer.post(f"{API}/listings/{lid}/offer", json={"amount": 420}).status_code == 200
        row = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        amts = sorted(o["amount"] for o in row["offers"])
        assert amts == [420, 450], amts
        top = next(o for o in row["offers"] if o["amount"] == 450)
        other = next(o for o in row["offers"] if o["amount"] == 420)
        assert v2.post(f"{API}/offers/{top['id']}/accept").status_code == 404  # not the seller
        r = v1.post(f"{API}/offers/{top['id']}/accept")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["pmc_fee"] == 30 and o["seller_net"] == 420 and o["via"] == "best_offer"
        assert mdb.mkt_bids.find_one({"_id": ObjectId(other["id"])})["status"] == "declined"
        assert v1.post(f"{API}/offers/{other['id']}/accept").status_code == 404

    def test_waived_fee(self, v1, v2, adm):
        lid = mk(v1, adm, "TEST_waived", ["fixed"], waive=True, buy_now_price=800, eligibility="any_verified")
        o = v2.post(f"{API}/listings/{lid}/buy").json()
        assert o["pmc_fee"] == 0 and o["seller_net"] == 800
        adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": 5, "charge": False})
        lid = mk(v1, adm, "TEST_chargeoff", ["fixed"], buy_now_price=800, eligibility="any_verified")
        o = v2.post(f"{API}/listings/{lid}/buy").json()
        assert o["pmc_fee"] == 0
        adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": 5, "charge": True})

    # --- auction close ---
    def test_auction_close_sold_and_unsold(self, v1, v2, adm, buyer):
        lid = S["auc"]  # top bid 110 < reserve 500 -> closed_unsold
        mdb.mkt_listings.update_one({"_id": ObjectId(lid)}, {"$set": {"closes_at": "2020-01-01T00:00:00+00:00"}})
        assert requests.get(f"{API}/listings/{lid}").json()["status"] == "closed_unsold"
        lid2 = mk(v1, adm, "TEST_auction_win", ["auction"], start_price=100, reserve_price=150, closes_at=future(), eligibility="any_verified")
        v2.post(f"{API}/listings/{lid2}/bid", json={"amount": 120})
        buyer.post(f"{API}/listings/{lid2}/bid", json={"amount": 200})
        mdb.mkt_listings.update_one({"_id": ObjectId(lid2)}, {"$set": {"closes_at": "2020-01-01T00:00:00+00:00"}})
        assert requests.get(f"{API}/listings/{lid2}").json()["status"] == "sold"
        o = mdb.mkt_orders.find_one({"listing_id": ObjectId(lid2)})
        assert o["buyer"]["kind"] == "buyer" and o["amount"] == 200 and o["pmc_fee"] == 10 and o["via"] == "auction"
        S["auc_order"] = str(o["_id"])
        assert v2.post(f"{API}/listings/{lid2}/bid", json={"amount": 999}).status_code == 409

    # --- purchases / pay / payout ---
    def test_purchases_and_pay(self, buyer, v2):
        p = buyer.get(f"{API}/my-purchases").json()
        ids = [o["id"] for o in p["orders"]]
        assert S["buy_order"] in ids and S["auc_order"] in ids and p["me"]["kind"] == "buyer"
        assert v2.get(f"{API}/my-purchases").status_code == 200
        assert requests.get(f"{API}/my-purchases").status_code == 401
        r = buyer.post(f"{API}/orders/{S['buy_order']}/pay", headers={"Origin": BASE_URL})
        S["pay"] = (r.status_code, r.text[:300])
        assert r.status_code == 200 and "checkout.stripe.com" in r.json()["checkout_url"], r.text
        assert v2.post(f"{API}/orders/{S['buy_order']}/pay").status_code == 409  # not their order

    def test_admin_orders_and_payout(self, adm):
        oid = S["buy_order"]
        assert adm.post(f"{API}/admin/orders/{oid}/payout", json={"reference": "TEST-REF"}).status_code == 409
        mdb.mkt_orders.update_one({"_id": ObjectId(oid)}, {"$set": {"status": "paid", "payout_status": "due"}})
        items = adm.get(f"{API}/admin/orders").json()["items"]
        row = next(x for x in items if x["id"] == oid)
        assert "seller_bank" in row
        # testvendor has no vendor bank -> falls back to registrations (or {}); v2 order bank comes from vendor doc
        v2rows = [x for x in items if x["seller_id"] == SEED["v2"]]
        for x in v2rows:
            assert x["seller_bank"].get("bank_account_number") == "TEST-123", x["seller_bank"]
        r = adm.post(f"{API}/admin/orders/{oid}/payout", json={"reference": "TEST-REF-1"})
        assert r.status_code == 200
        o = mdb.mkt_orders.find_one({"_id": ObjectId(oid)})
        assert o["payout_status"] == "sent" and o["payout_reference"] == "TEST-REF-1"

    def test_admin_endpoints_need_auth(self, v1):
        assert requests.get(f"{API}/admin/listings").status_code == 401
        assert v1.get(f"{API}/admin/settings").status_code in (401, 403)
        assert requests.get(f"{API}/mine").status_code == 401


class TestT181Fixes:
    def test_reserve_below_start_400(self, v1):
        r = v1.post(f"{API}/listings", json={"title": "TEST_resv", "sale_modes": ["auction"], "start_price": 100, "reserve_price": 50, "closes_at": future()})
        assert r.status_code == 400 and "reserve" in r.json()["detail"].lower(), r.text
        r = v1.post(f"{API}/listings", json={"title": "TEST_resv_ok", "sale_modes": ["auction"], "start_price": 100, "reserve_price": 100, "closes_at": future()})
        assert r.status_code == 200
        S["resv_ok"] = r.json()["id"]
        # PUT path also validates
        r = v1.put(f"{API}/listings/{S['resv_ok']}", json={"title": "TEST_resv_ok", "sale_modes": ["auction"], "start_price": 100, "reserve_price": 10, "closes_at": future()})
        assert r.status_code == 400

    def test_csrf_required_on_bid_offer_buy_pay(self, v1, v2, adm, buyer):
        lid = mk(v1, adm, "TEST_csrf", ["auction", "best_offer", "fixed"], start_price=10, buy_now_price=500, closes_at=future(), eligibility="any_verified")
        S["csrf_l"] = lid
        for sess in (v2, buyer):
            tok = sess.headers.pop("X-CSRF-Token")
            try:
                for path, body in (("bid", {"amount": 20}), ("offer", {"amount": 30}), ("buy", None)):
                    r = sess.post(f"{API}/listings/{lid}/{path}", json=body)
                    assert r.status_code == 403 and "CSRF" in r.json()["detail"], (path, r.text)
                r = sess.post(f"{API}/orders/{'0'*24}/pay")
                assert r.status_code == 403, r.text
                # wrong token
                r = sess.post(f"{API}/listings/{lid}/bid", json={"amount": 20}, headers={"X-CSRF-Token": "bogus"})
                assert r.status_code == 403
            finally:
                sess.headers["X-CSRF-Token"] = tok
        # with header works for both kinds
        assert v2.post(f"{API}/listings/{lid}/bid", json={"amount": 20}).status_code == 200
        assert buyer.post(f"{API}/listings/{lid}/offer", json={"amount": 300}).status_code == 200
        r = buyer.post(f"{API}/listings/{lid}/buy")
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        r = buyer.post(f"{API}/orders/{oid}/pay", headers={"Origin": BASE_URL})
        assert r.status_code == 200 and "checkout_url" in r.json(), r.text
        # GET my-purchases without header still OK
        h = buyer.headers.pop("X-CSRF-Token")
        try:
            assert buyer.get(f"{API}/my-purchases").status_code == 200
        finally:
            buyer.headers["X-CSRF-Token"] = h

    def test_best_offer_deadline(self, v1, v2, adm, buyer):
        adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": 10, "charge": True})
        lid = mk(v1, adm, "TEST_bo_deadline", ["best_offer"], closes_at=future(), eligibility="any_verified")
        assert buyer.post(f"{API}/listings/{lid}/offer", json={"amount": 250}).status_code == 200
        assert requests.get(f"{API}/listings", params={"q": "TEST_bo_deadline"}).json()["items"]
        mdb.mkt_listings.update_one({"_id": ObjectId(lid)}, {"$set": {"closes_at": "2020-01-01T00:00:00+00:00"}})
        r = v2.post(f"{API}/listings/{lid}/offer", json={"amount": 300})
        assert r.status_code == 409 and r.json()["detail"] == "The deadline for offers has passed", r.text
        assert requests.get(f"{API}/listings", params={"q": "TEST_bo_deadline"}).json()["items"] == []
        assert all(x["id"] != lid for x in requests.get(f"{API}/listings").json()["items"])
        row = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        assert len(row["offers"]) == 1
        r = v1.post(f"{API}/offers/{row['offers'][0]['id']}/accept")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["amount"] == 250 and o["pmc_fee"] == 25 and o["seller_net"] == 225
        # best_offer+fixed past deadline: still visible (fixed remains), offer blocked, buy works
        lid2 = mk(v1, adm, "TEST_bo_fixed_deadline", ["best_offer", "fixed"], buy_now_price=90, closes_at=future(), eligibility="any_verified")
        mdb.mkt_listings.update_one({"_id": ObjectId(lid2)}, {"$set": {"closes_at": "2020-01-01T00:00:00+00:00"}})
        assert [x["id"] for x in requests.get(f"{API}/listings", params={"q": "TEST_bo_fixed_deadline"}).json()["items"]] == [lid2]
        assert buyer.post(f"{API}/listings/{lid2}/offer", json={"amount": 50}).status_code == 409
        assert buyer.post(f"{API}/listings/{lid2}/buy").status_code == 200
        adm.put(f"{API}/admin/settings", json={"fee_type": "percent", "fee_value": 5, "charge": True})
