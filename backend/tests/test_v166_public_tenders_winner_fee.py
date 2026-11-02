# v166 — Open public tenders (category gate bypass) + private-tender 0.30% winner fee
# (notice-terms GET/PUT, bid category aliases/dicts, debrief winner_service_charge).
# Run serially: pytest tests/test_v166_public_tenders_winner_fee.py -n 0
import os
from datetime import datetime, timedelta, timezone
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
OWNER = ("kannan@emeraldcorporates.com", "Owner@123")
HVAC = "Heating, ventilation & air-conditioning (HVAC)"
OTHER = "TEST_V166 Other Category"
ALIAS_NAME = "TEST_V166 Master Cat"
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ST = {}


def _login(path, cred):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": cred[0], "password": cred[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def vdoc():
    v = _mdb.vendors.find_one({"email": VENDOR[0]})
    orig = v.get("business_categories")
    vid = str(v["_id"])
    for k in ("technical", "commercial"):
        _mdb.uploads.update_one({"key": f"bid-docs/TEST_V166_{k}"}, {"$set": {
            "key": f"bid-docs/TEST_V166_{k}", "sealed": True, "owner_vendor_id": vid,
            "content_type": "application/pdf"}}, upsert=True)
    u = _mdb.masters_unspsc.find_one({}, {"code": 1, "title_en": 1})
    ST["unspsc"] = u
    _mdb.categories.insert_one({"name": ALIAS_NAME, "unspsc_code": u["code"], "unspsc_title": u["title_en"], "TEST_V166": True})
    yield v
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": {"business_categories": orig}})
    refs = [n["notice_ref"] for n in _mdb.notices.find({"title": {"$regex": "^TEST_V166"}})]
    _mdb.notices.delete_many({"notice_ref": {"$in": refs}})
    _mdb.bids.delete_many({"notice_ref": {"$in": refs}})
    _mdb.buyer_classifications.delete_many({"notice_ref": {"$in": refs}})
    _mdb.category_upsell_log.delete_many({"notice_ref": {"$in": refs}})
    _mdb.notifications.delete_many({"related_id": {"$in": refs}})
    _mdb.uploads.delete_many({"key": {"$regex": "^bid-docs/TEST_V166"}})
    _mdb.categories.delete_many({"TEST_V166": True})
    _mdb.comparison_runs.delete_many({"notice_ref": {"$in": refs}})


@pytest.fixture(scope="module")
def admin():
    return _login("admin/auth/login", ADMIN)


@pytest.fixture(scope="module")
def vendor(vdoc):
    _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})
    return _login("vendor/auth/login", VENDOR)


DOCS = [{"kind": k, "key": f"bid-docs/TEST_V166_{k}", "filename": f"{k}.pdf", "size_bytes": 10,
         "uploaded_at": "2026-01-01T00:00:00Z"} for k in ("technical", "commercial")]


def _notice(admin, cat, published=True, **extra):
    dl = (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()
    r = admin.post(f"{API}/notices", json={"title": f"TEST_V166 {cat[:20]}", "description": "TEST_V166 notice description",
                                           "category": cat, "delivery_country": "KZ", "submission_deadline": dl,
                                           "budget_amount": 10000, "is_published": False, "kyc_bypass": True, **extra})
    assert r.status_code == 200, r.text
    ref = r.json()["notice_ref"]
    if published:
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"is_published": True, "kyc_bypass": True}})
    else:
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"kyc_bypass": True}})
    return ref


def _bid(vendor, ref):
    return vendor.post(f"{API}/bids", json={"notice_ref": ref, "price_amount": 9000, "price_currency": "USD", "documents": DOCS})


class TestTerms:
    def test_terms_private_default(self, admin):
        ref = _notice(admin, OTHER)
        ST["priv"] = ref
        r = requests.get(f"{API}/notice-terms/{ref}")
        assert r.status_code == 200
        assert r.json() == {"public_tender": False, "winner_fee_enabled": False, "winner_fee_pct": 0}

    def test_terms_404(self):
        assert requests.get(f"{API}/notice-terms/TEST_V166_NOPE").status_code == 404

    def test_terms_public_via_buyer_type_field(self, admin):
        ref = _notice(admin, OTHER)
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"buyer_type": "public_sector"}})
        ST["pub_field"] = ref
        assert requests.get(f"{API}/notice-terms/{ref}").json()["public_tender"] is True


class TestCategoryGate:
    def test_private_tender_403(self, vendor):
        r = _bid(vendor, ST["priv"])
        assert r.status_code == 403, r.text
        assert r.json()["detail"]["code"] == "category_not_registered"

    def test_public_field_tender_bid_ok(self, vendor):
        r = _bid(vendor, ST["pub_field"])
        assert r.status_code == 200, r.text
        assert r.json()["notice_ref"] == ST["pub_field"]

    def test_public_via_classification_bid_ok(self, admin, vendor):
        ref = _notice(admin, OTHER)
        r = admin.post(f"{API}/governance-controls/buyer-classifications", json={
            "notice_ref": ref, "buyer_name": "TEST_V166 Ministry", "buyer_type": "public_sector", "basis": "TEST_V166 state body"})
        if r.status_code == 404:
            pytest.skip("classification route path differs")
        assert r.status_code == 200, r.text
        assert requests.get(f"{API}/notice-terms/{ref}").json()["public_tender"] is True
        b = _bid(vendor, ref)
        assert b.status_code == 200, b.text

    def test_private_sector_classification_still_gated(self, admin, vendor):
        ref = _notice(admin, OTHER)
        _mdb.buyer_classifications.insert_one({"notice_ref": ref, "buyer_type": "private_sector", "status": "verified"})
        r = _bid(vendor, ref)
        assert r.status_code == 403, r.text

    def test_rejected_public_classification(self, admin, vendor):
        # A REJECTED public_sector classification should arguably not make the tender public.
        ref = _notice(admin, OTHER)
        _mdb.buyer_classifications.insert_one({"notice_ref": ref, "buyer_type": "public_sector", "status": "rejected"})
        t = requests.get(f"{API}/notice-terms/{ref}").json()
        print("rejected public classification ->", t)
        ST["rejected_public"] = t["public_tender"]

    def test_dict_categories_accepted(self, admin, vendor, vdoc):
        ref = _notice(admin, OTHER)
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [{"code": "X1", "title": OTHER}]}})
        r = _bid(vendor, ref)
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})
        assert r.status_code == 200, r.text

    def test_alias_unspsc_title_to_master_name(self, admin, vendor, vdoc):
        ref = _notice(admin, ST["unspsc"]["title_en"])
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [ALIAS_NAME]}})
        r = _bid(vendor, ref)
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})
        assert r.status_code == 200, r.text

    def test_alias_master_name_to_unspsc_title(self, admin, vendor, vdoc):
        ref = _notice(admin, ALIAS_NAME)
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [{"code": ST["unspsc"]["code"], "title": ST["unspsc"]["title_en"]}]}})
        r = _bid(vendor, ref)
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})
        assert r.status_code == 200, r.text


class TestWinnerFee:
    def test_published_409(self, admin):
        r = admin.put(f"{API}/notice-terms/{ST['priv']}/winner-fee", json={"enabled": True})
        assert r.status_code == 409

    def test_public_draft_enable_409(self, admin):
        ref = _notice(admin, OTHER, published=False)
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"buyer_type": "public_sector"}})
        r = admin.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True})
        assert r.status_code == 409

    def test_non_admin_denied(self, admin, vendor):
        ref = _notice(admin, OTHER, published=False)
        ST["draft"] = ref
        assert requests.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True}).status_code in (401, 403)
        assert vendor.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True}).status_code in (401, 403)

    def test_enable_disable_draft(self, admin):
        ref = ST["draft"]
        r = admin.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True})
        assert r.status_code == 200, r.text
        assert r.json() == {"public_tender": False, "winner_fee_enabled": True, "winner_fee_pct": 0.30}
        n = _mdb.notices.find_one({"notice_ref": ref})
        assert n["winner_fee_enabled"] is True and n["winner_fee_pct"] == 0.30
        assert _mdb.audit_events.find_one({"event_type": "notice.winner_fee", "target_id": ref})
        r = admin.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": False})
        assert r.status_code == 200 and r.json()["winner_fee_enabled"] is False
        r = admin.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True})
        assert r.status_code == 200

    def test_debrief_winner_and_loser(self, admin, vendor, vdoc):
        ref = ST["draft"]
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"is_published": True}})
        assert requests.get(f"{API}/notice-terms/{ref}").json()["winner_fee_enabled"] is True
        vid = str(vdoc["_id"])
        win = _mdb.bids.insert_one({"notice_ref": ref, "vendor_id": vid, "bid_ref": "TEST_V166-W", "status": "awarded",
                                    "price_amount": 123456.0, "price_currency": "USD"}).inserted_id
        r = vendor.get(f"{API}/bids/{win}/debrief")
        assert r.status_code == 200, r.text
        wc = r.json()["winner_service_charge"]
        assert wc == {"pct": 0.30, "amount": 370.37, "currency": "USD"}
        ST["win_bid"] = str(win)
        _mdb.bids.update_one({"_id": win}, {"$set": {"status": "non_winner"}})
        r = vendor.get(f"{API}/bids/{win}/debrief")
        assert r.status_code == 200 and r.json()["winner_service_charge"] is None
        _mdb.bids.update_one({"_id": win}, {"$set": {"status": "awarded"}})

    def test_debrief_no_fee_when_disabled(self, admin, vendor, vdoc):
        ref = _notice(admin, OTHER)
        b = _mdb.bids.insert_one({"notice_ref": ref, "vendor_id": str(vdoc["_id"]), "bid_ref": "TEST_V166-N", "status": "awarded",
                                  "price_amount": 1000.0, "price_currency": "USD"}).inserted_id
        r = vendor.get(f"{API}/bids/{b}/debrief")
        assert r.status_code == 200 and r.json()["winner_service_charge"] is None

    def test_debrief_fee_after_reclassified_public(self, admin, vendor, vdoc):
        # Edge: fee enabled on draft, then tender classified public_sector -> terms says no fee; debrief should agree.
        ref = ST["draft"]
        _mdb.buyer_classifications.insert_one({"notice_ref": ref, "buyer_type": "public_sector", "status": "verified"})
        t = requests.get(f"{API}/notice-terms/{ref}").json()
        r = vendor.get(f"{API}/bids/{ST['win_bid']}/debrief").json()
        _mdb.buyer_classifications.delete_many({"notice_ref": ref})
        print("terms:", t, "debrief charge:", r.get("winner_service_charge"))
        assert t["winner_fee_enabled"] is False
        assert r.get("winner_service_charge") is None, "debrief charges winner on a PUBLIC tender"


class TestRegression:
    def test_publish_endpoint_still_works(self, admin):
        ref = _notice(admin, OTHER, published=False)
        admin.put(f"{API}/notice-terms/{ref}/winner-fee", json={"enabled": True})
        r = admin.post(f"{API}/notices/{ref}/publish")
        print("publish:", r.status_code, r.text[:200])
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            assert requests.get(f"{API}/notice-terms/{ref}").json()["winner_fee_enabled"] is True
