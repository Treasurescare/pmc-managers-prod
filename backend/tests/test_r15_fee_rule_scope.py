# R15 — Fee rules auto-populate from fee type: fee-type categories persisted, multi-country rules
# (country=MULTI / single code / ALL), extend_type adds countries/categories to the fee type,
# find_rule multi-country match + specificity, list ?country= filter. Run serially: -n 0
import os
import sys
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CATS = [c for c in _mdb.categories.find({"is_active": True}).limit(4)]
SLAB = [{"fee_type": "fixed", "fixed_amount": 25, "tender_value_min": 0, "tender_value_max": None}]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    yield s
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_R15"}})
    _mdb.fee_types.delete_many({"code": {"$regex": "^test_r15"}})


def _ft(admin, name, **kw):
    body = {"name": name, "calc": "fixed", "amount_mode": "single", **kw}
    r = admin.post(f"{API}/fee-types", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _rule(admin, kind, **kw):
    body = {"name": "TEST_R15 rule", "kind": kind, "currency": "USD", "slabs": SLAB, **kw}
    return admin.post(f"{API}/tender-pro/emd-masters", json=body)


class TestFeeTypeCategories:
    def test_all_types_have_categories_field(self, admin):
        r = admin.get(f"{API}/fee-types")
        assert r.status_code == 200
        assert all(isinstance(t.get("categories"), list) for t in r.json())

    def test_patch_categories_persisted(self, admin):
        ft = _ft(admin, "TEST_R15 cats", category_scope="selected")
        body = {k: ft[k] for k in ("name", "timing", "calc", "amount_mode", "category_scope", "billing",
                                   "used_in_tender_builder", "country_scope", "countries", "is_active")}
        body["categories"] = [CATS[0]["name"], CATS[1]["name"]]
        r = admin.patch(f"{API}/fee-types/{ft['id']}", json=body)
        assert r.status_code == 200, r.text
        got = [t for t in admin.get(f"{API}/fee-types").json() if t["id"] == ft["id"]][0]
        assert got["categories"] == body["categories"]


class TestRuleCountries:
    def test_multi_country(self, admin):
        r = _rule(admin, "emd", countries=["kz", "IN"])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["country"] == "MULTI" and d["countries"] == ["IN", "KZ"]

    def test_single_country(self, admin):
        d = _rule(admin, "emd", countries=["KZ"]).json()
        assert d["country"] == "KZ" and d["countries"] == ["KZ"]

    def test_no_country_all(self, admin):
        d = _rule(admin, "emd").json()
        assert d["country"] == "ALL" and d["countries"] == []

    def test_legacy_country_only(self, admin):
        d = _rule(admin, "emd", country="KZ").json()
        assert d["country"] == "KZ" and d["countries"] == ["KZ"]

    def test_list_filter_in(self, admin):
        rows = admin.get(f"{API}/tender-pro/emd-masters", params={"country": "IN"}).json()
        mine = [x for x in rows if x["name"].startswith("TEST_R15")]
        cs = sorted(x["country"] for x in mine)
        assert "MULTI" in cs and "ALL" in cs and "KZ" not in cs
        assert all(x["country"] in ("ALL", "IN") or "IN" in (x.get("countries") or []) for x in rows)


class TestExtendType:
    def test_country_scope_extend(self, admin):
        ft = _ft(admin, "TEST_R15 cty", country_scope="selected", countries=["KZ"])
        r = _rule(admin, ft["code"], countries=["KZ", "IN"])
        assert r.status_code == 422, r.text
        r = _rule(admin, ft["code"], countries=["KZ", "IN"], extend_type=True)
        assert r.status_code == 200, r.text
        assert r.json()["country"] == "MULTI"
        got = _mdb.fee_types.find_one({"code": ft["code"]})
        assert set(got["countries"]) == {"KZ", "IN"}

    def test_category_scope_extend(self, admin):
        ft = _ft(admin, "TEST_R15 cat2", category_scope="selected", categories=[CATS[0]["name"]])
        r = _rule(admin, ft["code"], categories=[CATS[0]["name"], CATS[2]["name"]])
        assert r.status_code == 422, r.text
        r = _rule(admin, ft["code"], categories=[CATS[0]["name"], CATS[2]["name"]], extend_type=True)
        assert r.status_code == 200, r.text
        got = _mdb.fee_types.find_one({"code": ft["code"]})
        assert set(got["categories"]) == {CATS[0]["name"], CATS[2]["name"]}

    def test_patch_rule_extend(self, admin):
        ft = _ft(admin, "TEST_R15 cty3", country_scope="selected", countries=["KZ"])
        rid = _rule(admin, ft["code"], countries=["KZ"]).json()["id"]
        body = {"name": "TEST_R15 rule", "kind": ft["code"], "currency": "USD", "slabs": SLAB,
                "countries": ["KZ", "AE"]}
        assert admin.patch(f"{API}/tender-pro/emd-masters/{rid}", json=body).status_code == 422
        r = admin.patch(f"{API}/tender-pro/emd-masters/{rid}", json={**body, "extend_type": True})
        assert r.status_code == 200, r.text
        assert "AE" in _mdb.fee_types.find_one({"code": ft["code"]})["countries"]

    def test_failed_validation_does_not_extend(self, admin):
        # extend + invalid slab should not leave side effects on the fee type
        ft = _ft(admin, "TEST_R15 cty4", country_scope="selected", countries=["KZ"])
        r = admin.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R15 bad", "kind": ft["code"],
                       "slabs": [], "countries": ["KZ", "QA"], "extend_type": True})
        assert r.status_code == 422
        assert "QA" not in _mdb.fee_types.find_one({"code": ft["code"]})["countries"]


class TestFindRule:
    @pytest.fixture(scope="class")
    def vendor(self):
        v = _mdb.vendors.find_one({"email": VENDOR[0]})
        before = {k: v.get(k) for k in ("country", "business_categories")}
        _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": {"country": "XU",
                                "business_categories": [CATS[0]["name"]]}})
        s = requests.Session()
        r = s.post(f"{API}/vendor/auth/login", json={"email": VENDOR[0], "password": VENDOR[1]})
        assert r.status_code == 200, r.text
        yield s
        _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": before})

    def test_multi_country_registration_fee(self, admin, vendor):
        r = _rule(admin, "registration", name="TEST_R15 reg multi", countries=["XT", "XU"],
                  slabs=[{"fee_type": "fixed", "fixed_amount": 77}])
        assert r.status_code == 200, r.text
        q = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[1]["name"]}).json()
        assert q["required"] is True and q["amount"] == 77.0, q

    def test_specific_beats_all(self, admin, vendor):
        r = _rule(admin, "registration", name="TEST_R15 reg all", slabs=[{"fee_type": "fixed", "fixed_amount": 11}])
        assert r.status_code == 200
        q = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[1]["name"]}).json()
        assert q["amount"] == 77.0, q
        _mdb.emd_masters.delete_many({"name": "TEST_R15 reg multi"})
        q = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[1]["name"]}).json()
        assert q["amount"] == 11.0, q
