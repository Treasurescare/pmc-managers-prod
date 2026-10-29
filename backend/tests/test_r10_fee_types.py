# R10 — Fee Type master (CRUD), fee rules validated against fee types, vendor Tender
# Builder per-tender fees (compute / enforcement 402 / Stripe checkout / crediting).
# Run serially: pytest tests/test_r10_fee_types.py -n 0
import os
import sys
import uuid
import base64
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
VB_EMAIL, VB_PW = "test_r10_vendorb@pmcmanagers.com", "VendorB@12345"
CAT = "Fire alarm & safety systems"

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
SEEDED = {"subscription", "premium_subscription", "registration", "emd", "tender_fee",
          "tender_management", "transaction", "data_intel"}


def _vlogin(e, p):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": e, "password": p})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def vendor():
    v = _mdb.vendors.find_one({"email": VENDOR[0]})
    before = {k: v.get(k) for k in ("profile", "business_categories")}
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": {"profile.country": "KZ",
                                                          "business_categories": [CAT]}})
    yield _vlogin(*VENDOR)
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": before})
    vid = str(v["_id"])
    _mdb.tender_templates.delete_many({"owner_vendor_id": vid, "name": {"$regex": "^TEST_R10"}})
    _mdb.payment_transactions.delete_many({"vendor_id": vid, "purpose": "tender_fee"})
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_"}})
    _mdb.fee_types.delete_many({"code": {"$regex": "^test_"}})


@pytest.fixture(scope="module")
def vendor_b():
    from security import hash_password
    _mdb.vendors.update_one({"email": VB_EMAIL}, {"$set": {
        "email": VB_EMAIL, "company_name": "TEST_R10 B", "vendor_ref": "VEN-TESTR10B",
        "password_hash": hash_password(VB_PW), "kyc_status": "verified", "status": "active",
        "is_active": True}}, upsert=True)
    yield _vlogin(VB_EMAIL, VB_PW)
    _mdb.vendors.delete_one({"email": VB_EMAIL})


@pytest.fixture(scope="module")
def st():
    return {}


def _ft(name, **kw):
    d = {"name": name, "timing": "upfront", "calc": "fixed", "amount_mode": "single",
         "category_scope": "all", "billing": "one_time", "used_in_tender_builder": False}
    d.update(kw)
    return d


def _slab(lo=0, hi=None, fixed=None, pct=None, pmin=None, pmax=None):
    return {"tender_value_min": lo, "tender_value_max": hi,
            "fee_type": "fixed" if fixed is not None else "percentage",
            "fixed_amount": fixed, "percentage": pct, "pct_min": pmin, "pct_max": pmax}


def _tpl(name, value=50000, cat=CAT):
    return {"name": name, "kind": "tender",
            "header": {"work_title": f"{name} work", "work_description": "desc",
                       "budget_currency": "USD", "budget_amount": value, "tender_value": value,
                       "product_category": cat},
            "sections": [{"code": "sec-1", "kind": "section", "title": "NIB", "body": "<p>hi</p>"}]}


def _fee(vendor, tid, code="tender_management"):
    r = vendor.get(f"{API}/vendor-tenders/fees/{tid}")
    assert r.status_code == 200, r.text
    return next((f for f in r.json()["fees"] if f["code"] == code), None)


# ---------- Fee type master CRUD ----------
class TestFeeTypes:
    def test_seeded_list(self, admin):
        r = admin.get(f"{API}/fee-types")
        assert r.status_code == 200, r.text
        by = {x["code"]: x for x in r.json()}
        assert SEEDED <= set(by)
        assert by["tender_management"]["timing"] == "on_completion"
        assert by["tender_management"]["used_in_tender_builder"] is True
        assert by["subscription"]["billing"] == "yearly"
        assert all("_id" not in x for x in r.json())

    def test_vendor_denied(self, vendor):
        assert vendor.get(f"{API}/fee-types").status_code in (401, 403)

    def test_csrf_required(self):
        s = requests.Session()
        s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
        r = s.post(f"{API}/fee-types", json=_ft("TEST csrf"))
        assert r.status_code == 403, r.text

    def test_create_patch_delete(self, admin):
        r = admin.post(f"{API}/fee-types", json=_ft("TEST R10 Crud Type", calc="either", amount_mode="range"))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["code"] == "test_r10_crud_type" and d["is_system"] is False
        assert admin.post(f"{API}/fee-types", json=_ft("TEST R10 Crud Type")).status_code == 409
        p = admin.patch(f"{API}/fee-types/{d['id']}", json=_ft("TEST R10 Crud Type2", timing="on_completion"))
        assert p.status_code == 200 and p.json()["timing"] == "on_completion"
        assert p.json()["code"] == "test_r10_crud_type"
        g = {x["code"]: x for x in admin.get(f"{API}/fee-types").json()}
        assert g["test_r10_crud_type"]["name"] == "TEST R10 Crud Type2"
        # in-use → 409
        rr = admin.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R10 use", "country": "KZ",
                        "kind": "test_r10_crud_type", "slabs": [_slab(fixed=1)]})
        assert rr.status_code == 200, rr.text
        assert admin.delete(f"{API}/fee-types/{d['id']}").status_code == 409
        admin.delete(f"{API}/tender-pro/emd-masters/{rr.json()['id']}")
        assert admin.delete(f"{API}/fee-types/{d['id']}").status_code == 200
        assert admin.delete(f"{API}/fee-types/{d['id']}").status_code == 404

    def test_invalid_enum(self, admin):
        assert admin.post(f"{API}/fee-types", json=_ft("TEST bad", timing="later")).status_code == 422


# ---------- Fee rules validated against type ----------
class TestRuleValidation:
    def _post(self, admin, **kw):
        d = {"name": "TEST_R10 v", "country": "KZ", "kind": "registration", "slabs": [_slab(fixed=5)]}
        d.update(kw)
        return admin.post(f"{API}/tender-pro/emd-masters", json=d)

    def test_unknown_kind(self, admin):
        assert self._post(admin, kind="nope_xyz").status_code == 422

    def test_single_two_lines(self, admin):
        assert self._post(admin, slabs=[_slab(0, 10, fixed=1), _slab(10, None, fixed=2)]).status_code == 422

    def test_calc_mismatch(self, admin):
        assert self._post(admin, slabs=[_slab(pct=1)]).status_code == 422
        assert self._post(admin, kind="transaction", slabs=[_slab(fixed=3)]).status_code == 422

    def test_zero_amount(self, admin):
        assert self._post(admin, slabs=[_slab(fixed=0)]).status_code == 422

    def test_selected_needs_categories(self, admin):
        r = self._post(admin, kind="tender_management", categories=[], slabs=[_slab(fixed=5)])
        assert r.status_code == 422

    def test_all_scope_clears_categories_and_single_normalised(self, admin):
        r = self._post(admin, categories=["A", "B"], slabs=[_slab(5, 99, fixed=5)])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["categories"] == [] and d.get("category") is None
        assert d["slabs"][0]["tender_value_min"] == 0 and d["slabs"][0]["tender_value_max"] is None
        admin.delete(f"{API}/tender-pro/emd-masters/{d['id']}")

    def test_existing_kz_rules_patch_roundtrip(self, admin):
        rows = admin.get(f"{API}/tender-pro/emd-masters", params={"country": "KZ"}).json()
        names = {x["name"]: x for x in rows}
        assert "KZ Public Works EMD" in names and "KZ Registration Fee" in names
        for n in ("KZ Public Works EMD", "KZ Registration Fee"):
            x = names[n]
            body = {k: x.get(k) for k in ("name", "country", "industry", "category", "kind",
                                          "currency", "slabs", "is_active", "notes")}
            body["categories"] = x.get("categories") or []
            r = admin.patch(f"{API}/tender-pro/emd-masters/{x['id']}", json=body)
            assert r.status_code == 200, f"{n}: {r.text}"
            assert r.json()["slabs"] == x["slabs"]


# ---------- vendor per-tender fees ----------
class TestTenderFees:
    def test_setup_rule(self, admin, st):
        r = admin.post(f"{API}/tender-pro/emd-masters", json={
            "name": "TEST_R10 TM", "country": "KZ", "kind": "tender_management", "categories": [CAT],
            "currency": "USD", "slabs": [_slab(0, 100000, fixed=50), _slab(100000, None, pct=1, pmax=2500)]})
        assert r.status_code == 200, r.text
        assert r.json()["categories"] == [CAT]
        st["rule"] = r.json()["id"]
        # an all-categories rule inserted directly — the category-specific one must win
        st["allrule"] = str(_mdb.emd_masters.insert_one({
            "name": "TEST_R10 TM all", "country": "KZ", "kind": "tender_management", "categories": [],
            "category": None, "is_active": True, "currency": "USD",
            "slabs": [_slab(fixed=999)]}).inserted_id)

    def test_fee_computed_fixed(self, vendor, st):
        r = vendor.post(f"{API}/tender-templates", json=_tpl(f"TEST_R10 T {uuid.uuid4().hex[:4]}"))
        assert r.status_code == 200, r.text
        st["tid"] = r.json()["id"]
        f = _fee(vendor, st["tid"])
        assert f and f["rule_id"] == st["rule"], f
        assert f["amount"] == 50 and f["paid"] is False and f["timing"] == "on_completion"

    def test_other_category_uses_all_rule(self, vendor, st):
        r = vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R10 other", cat="Elevators & escalators"))
        tid = r.json()["id"]
        f = _fee(vendor, tid)
        assert f and f["rule_id"] == st["allrule"] and f["amount"] == 999

    def test_owner_only(self, vendor_b, st):
        assert vendor_b.get(f"{API}/vendor-tenders/fees/{st['tid']}").status_code == 404
        assert vendor_b.post(f"{API}/vendor-tenders/fees/{st['tid']}/checkout",
                             json={"fee_code": "tender_management", "origin_url": BASE_URL}).status_code == 404

    def test_on_completion_allows_work_blocks_submit(self, vendor, st):
        r = vendor.patch(f"{API}/tender-pro/templates/{st['tid']}/sections/sec-1", json={"body": "<p>x</p>"})
        assert r.status_code == 200, r.text
        s = vendor.post(f"{API}/tender-templates/{st['tid']}/submit-review")
        assert s.status_code == 402, s.text
        assert "Tender management fee" in s.json().get("detail", "")

    def test_pct_and_cap(self, vendor, st):
        assert vendor.patch(f"{API}/tender-templates/{st['tid']}", json=_tpl("TEST_R10 T", 200000)).status_code == 200
        assert _fee(vendor, st["tid"])["amount"] == 2000
        vendor.patch(f"{API}/tender-templates/{st['tid']}", json=_tpl("TEST_R10 T", 900000))
        assert _fee(vendor, st["tid"])["amount"] == 2500  # pct_max cap
        vendor.patch(f"{API}/tender-templates/{st['tid']}", json=_tpl("TEST_R10 T", 200000))

    def test_checkout_and_credit(self, vendor, st):
        r = vendor.post(f"{API}/vendor-tenders/fees/{st['tid']}/checkout",
                        json={"fee_code": "tender_management", "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout.stripe.com" in d["checkout_url"] or d["checkout_url"].startswith("https://")
        st["sid"] = d["session_id"]
        tx = _mdb.payment_transactions.find_one({"session_id": st["sid"]})
        assert tx["amount"] == 2000 and tx["purpose"] == "tender_fee" and tx["payment_status"] == "pending"
        # unpaid status → not credited
        s0 = vendor.get(f"{API}/vendor-tenders/fees/checkout/status/{st['sid']}").json()
        assert s0["payment_status"] != "paid"
        assert _fee(vendor, st["tid"])["paid"] is False
        # simulate Stripe paid
        _mdb.payment_transactions.update_one({"session_id": st["sid"]},
                                             {"$set": {"payment_status": "paid", "status": "completed"}})
        for _ in range(2):  # idempotent
            s1 = vendor.get(f"{API}/vendor-tenders/fees/checkout/status/{st['sid']}")
            assert s1.status_code == 200 and s1.json()["template_id"] == st["tid"]
        f = _fee(vendor, st["tid"])
        assert f["paid"] is True and f["paid_amount"] == 2000, f
        again = vendor.post(f"{API}/vendor-tenders/fees/{st['tid']}/checkout",
                            json={"fee_code": "tender_management", "origin_url": BASE_URL})
        assert again.status_code == 409

    def test_raise_value_difference_due(self, vendor, st):
        vendor.patch(f"{API}/tender-templates/{st['tid']}", json=_tpl("TEST_R10 T", 240000))
        f = _fee(vendor, st["tid"])
        assert f["amount"] == 2400 and f["outstanding"] == 400 and f["paid"] is False
        assert vendor.post(f"{API}/tender-templates/{st['tid']}/submit-review").status_code == 402
        vendor.patch(f"{API}/tender-templates/{st['tid']}", json=_tpl("TEST_R10 T", 200000))
        r = vendor.post(f"{API}/tender-templates/{st['tid']}/submit-review")
        assert r.status_code == 200, r.text

    def test_status_foreign_session_404(self, vendor_b, st):
        assert vendor_b.get(f"{API}/vendor-tenders/fees/checkout/status/{st['sid']}").status_code == 404


# ---------- upfront per-tender fee type enforcement ----------
class TestUpfrontEnforcement:
    def test_setup(self, admin, vendor, st):
        r = admin.post(f"{API}/fee-types", json=_ft("TEST R10 Upfront", used_in_tender_builder=True))
        assert r.status_code == 200, r.text
        st["up_code"] = r.json()["code"]
        rr = admin.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R10 UP", "country": "KZ",
                        "kind": st["up_code"], "slabs": [_slab(fixed=10)]})
        assert rr.status_code == 200, rr.text
        st["up_rule"] = rr.json()["id"]
        t = vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R10 UPT"))
        st["utid"] = t.json()["id"]
        f = _fee(vendor, st["utid"], st["up_code"])
        assert f and f["amount"] == 10 and f["timing"] == "upfront" and not f["paid"]

    def test_header_save_allowed(self, vendor, st):
        assert vendor.patch(f"{API}/tender-templates/{st['utid']}", json=_tpl("TEST_R10 UPT", 60000)).status_code == 200

    @pytest.mark.parametrize("ep", ["fill", "fill_async", "dpr", "dpr_async", "draft", "section", "master", "pdf"])
    def test_blocked_402(self, vendor, st, ep):
        tid = st["utid"]
        b64 = base64.b64encode(b"hello dpr").decode()
        calls = {
            "fill": lambda: vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all", json={"length": "short"}),
            "fill_async": lambda: vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all-async", json={"length": "short"}),
            "dpr": lambda: vendor.post(f"{API}/tender-pro/dpr/analyze-json?template_id={tid}", json={"filename": "a.txt", "content_b64": b64}),
            "dpr_async": lambda: vendor.post(f"{API}/tender-pro/dpr/analyze-async?template_id={tid}", json={"filename": "a.txt", "content_b64": b64}),
            "draft": lambda: vendor.post(f"{API}/tender-templates/{tid}/sections/sec-1/ai-draft", json={}),
            "section": lambda: vendor.patch(f"{API}/tender-pro/templates/{tid}/sections/sec-1", json={"body": "<p>y</p>"}),
            "master": lambda: vendor.post(f"{API}/tender-pro/templates/{tid}/save-as-master", json={"country": "KZ", "industry": "Works"}),
            "pdf": lambda: vendor.get(f"{API}/tender-templates/{tid}/export/pdf"),
        }
        r = calls[ep]()
        assert r.status_code == 402, f"{ep}: {r.status_code} {r.text[:200]}"

    def test_unblocked_after_paid(self, vendor, st):
        _mdb.tender_templates.update_one({"_id": ObjectId(st["utid"])},
                                         {"$set": {f"fees_paid.{st['up_code']}.amount": 10}})
        r = vendor.patch(f"{API}/tender-pro/templates/{st['utid']}/sections/sec-1", json={"body": "<p>y</p>"})
        assert r.status_code == 200, r.text

    def test_teardown_upfront(self, admin, st):
        assert admin.delete(f"{API}/tender-pro/emd-masters/{st['up_rule']}").status_code == 200
        ids = {x["code"]: x["id"] for x in admin.get(f"{API}/fee-types").json()}
        assert admin.delete(f"{API}/fee-types/{ids[st['up_code']]}").status_code == 200
