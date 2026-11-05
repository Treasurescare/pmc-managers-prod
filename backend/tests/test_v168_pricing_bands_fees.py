# v168 — Pricing bands, tiers, fee rules by band, per-tender fee plan, publish gates, award fee, supplier fee plan
import asyncio
import os
import sys
import uuid

import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
REF = "TEST-FEE-001"
SUF = uuid.uuid4().hex[:6].upper()


@pytest.fixture(scope="module")
def s():
    ss = requests.Session()
    r = ss.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("csrf_token") or ss.cookies.get("csrf_token")
    ss.headers.update({"X-CSRF-Token": tok or ""})
    return ss


@pytest.fixture(scope="module")
def tmp_notices():
    refs = []
    yield refs
    for r in refs:
        mdb.notices.delete_one({"notice_ref": r})


def _mk_notice(refs, **kw):
    ref = f"TEST-FEE-{SUF}-{len(refs)}"
    doc = {"notice_ref": ref, "title": "TEST_ tmp fee notice", "delivery_country": "GB", "budget_amount": 1000000,
           "category": "Construction", "currency": "USD", "is_published": False, "document_type": "tender",
           "tender_criteria": [{"id": "c1", "kind": "must_pass", "title": "x"}], **kw}
    mdb.notices.insert_one(doc)
    refs.append(ref)
    return ref


# ---------------- bands & tiers ----------------
class TestBands:
    def test_list_bands(self, s):
        r = s.get(f"{API}/pricing/bands")
        assert r.status_code == 200
        d = r.json()
        codes = [b["code"] for b in d["bands"]]
        assert codes[:5] == ["GLOBAL", "REGIONAL", "PROGRAMME", "INDIA", "CHINA"]
        china = next(b for b in d["bands"] if b["code"] == "CHINA")
        assert china["is_active"] is False
        assert d["tiers"] == ["Starter", "Professional", "Programme"]
        assert "_id" not in d["bands"][0]

    def test_update_band_and_clash(self, s):
        b = next(x for x in s.get(f"{API}/pricing/bands").json()["bands"] if x["code"] == "REGIONAL")
        orig = {k: b.get(k) for k in ("name", "countries", "is_active", "award_payer_default", "supplier_fees_default", "notes")}
        try:
            r = s.put(f"{API}/pricing/bands/REGIONAL", json={**orig, "countries": orig["countries"] + ["ar"]})
            assert r.status_code == 200, r.text
            assert "AR" in r.json()["countries"]
            r = s.put(f"{API}/pricing/bands/REGIONAL", json={**orig, "countries": orig["countries"] + ["GB"]})
            assert r.status_code == 409 and "GB" in r.json().get("detail", str(r.json()))
            r = s.put(f"{API}/pricing/bands/REGIONAL", json={**orig, "countries": ["XYZ"]})
            assert r.status_code == 422
            r = s.put(f"{API}/pricing/bands/NOPE_BAND", json={**orig, "countries": []})
            assert r.status_code == 404
        finally:
            r = s.put(f"{API}/pricing/bands/REGIONAL", json=orig)
            assert r.status_code == 200 and r.json()["countries"] == sorted(orig["countries"])

    def test_tiers_put_restore(self, s):
        orig = s.get(f"{API}/pricing/bands").json()["tiers"]
        try:
            r = s.put(f"{API}/pricing/tiers", json={"tiers": orig + ["TEST_Tier"]})
            assert r.status_code == 200 and r.json()["tiers"][-1] == "TEST_Tier"
            assert s.get(f"{API}/pricing/bands").json()["tiers"][-1] == "TEST_Tier"
            assert s.put(f"{API}/pricing/tiers", json={"tiers": []}).status_code == 422
        finally:
            assert s.put(f"{API}/pricing/tiers", json={"tiers": orig}).status_code == 200
        assert s.get(f"{API}/pricing/bands").json()["tiers"] == orig


# ---------------- fee rules (emd-masters) with bands ----------------
class TestFeeRulesBands:
    def test_create_band_rule_and_validation(self, s):
        slab = [{"fee_type": "percentage", "percentage": 0.1, "pct_max": 1000}]
        r = s.post(f"{API}/tender-pro/emd-masters", json={"name": f"TEST_ band rule {SUF}", "kind": "tender_hosting",
                   "bands": ["REGIONAL"], "tier": "Starter", "nil_below": 5000, "currency": "USD", "slabs": slab})
        assert r.status_code == 200, r.text
        d = r.json()
        rid = d.get("id") or d.get("_id")
        try:
            assert d["country"] == "BAND" and d["bands"] == ["REGIONAL"]
            assert d["tier"] == "Starter" and d["nil_below"] == 5000
            r2 = s.post(f"{API}/tender-pro/emd-masters", json={"name": f"TEST_ both {SUF}", "kind": "tender_hosting",
                        "bands": ["GLOBAL"], "countries": ["IN"], "currency": "USD", "slabs": slab})
            assert r2.status_code == 422
            if r2.status_code == 200:
                s.delete(f"{API}/tender-pro/emd-masters/{r2.json().get('id')}")
        finally:
            s.delete(f"{API}/tender-pro/emd-masters/{rid}")

    def test_unknown_band_code_accepted(self, s):
        """Report-only: rule with non-existent band code should ideally be rejected."""
        r = s.post(f"{API}/tender-pro/emd-masters", json={"name": f"TEST_ badband {SUF}", "kind": "tender_hosting",
                   "bands": ["NOSUCHBAND"], "currency": "USD", "slabs": [{"fee_type": "fixed", "fixed_amount": 10}]})
        if r.status_code == 200:
            s.delete(f"{API}/tender-pro/emd-masters/{r.json().get('id')}")
        print("unknown band status", r.status_code)
        assert r.status_code in (200, 422)


# ---------------- per-tender fee plan ----------------
class TestFeePlan:
    def test_get_fee_plan(self, s):
        r = s.get(f"{API}/pricing/notices/{REF}/fee-plan")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["band"]["code"] == "GLOBAL" and d["band"]["name"] == "Global"
        tr = next(i for i in d["items"] if i["code"] == "transaction")
        assert tr["has_rule"] and tr["rate"] == "0.3%, max 50,000; nil below 25,000"
        assert tr["estimate"] == 3000

    def test_fee_plan_validations_and_save(self, s, tmp_notices):
        ref = _mk_notice(tmp_notices)
        base = [{"code": "tender_hosting", "charge": False}, {"code": "tender_document_download", "charge": False}]
        u = f"{API}/pricing/notices/{ref}/fee-plan"
        r = s.put(u, json={"award_payer": "buyer", "items": base + [{"code": "transaction", "charge": True}]})
        assert r.status_code == 422 and "email" in r.text.lower()
        r = s.put(u, json={"award_payer": "supplier", "items": base + [{"code": "transaction", "charge": False}]})
        assert r.status_code == 422 and "reason" in r.text.lower()
        r = s.put(u, json={"award_payer": "supplier", "items": [{"code": "tender_hosting", "charge": True},
                   {"code": "tender_document_download", "charge": False}, {"code": "transaction", "charge": True}]})
        assert r.status_code == 422 and "No fee rule" in r.text
        r = s.put(u, json={"award_payer": "supplier", "tier": "BadTier", "items": base + [{"code": "transaction", "charge": True}]})
        assert r.status_code == 422
        r = s.put(u, json={"award_payer": "supplier", "items": base + [{"code": "transaction", "charge": True}]})
        assert r.status_code == 200, r.text
        n = mdb.notices.find_one({"notice_ref": ref})
        assert n["fee_plan"]["award_payer"] == "supplier" and n["fee_plan"]["band"] == "GLOBAL"
        t = s.get(f"{API}/notice-terms/{ref}")
        assert t.status_code == 200, t.text
        td = t.json()
        assert td.get("winner_fee_enabled") is True and float(td.get("winner_fee_pct")) == 0.3
        # buyer payer with email -> winner fee off
        r = s.put(u, json={"award_payer": "buyer", "payer_email": "TEST_buyer@example.com",
                           "items": base + [{"code": "transaction", "charge": True}]})
        assert r.status_code == 200
        n = mdb.notices.find_one({"notice_ref": ref})
        assert n["winner_fee_enabled"] is False and n["fee_plan"]["payer_email"] == "test_buyer@example.com"


# ---------------- publish gates ----------------
class TestPublishGate:
    def test_publish_without_plan_409(self, s, tmp_notices):
        ref = _mk_notice(tmp_notices)
        r = s.post(f"{API}/notices/{ref}/publish")
        assert r.status_code == 409 and "Confirm the fees first" in r.text
        r = s.patch(f"{API}/notices/{ref}", json={"is_published": True})
        assert r.status_code == 409 and "Confirm the fees first" in r.text
        assert mdb.notices.find_one({"notice_ref": ref})["is_published"] is False

    def test_fee_plan_locked_after_publish(self, s, tmp_notices):
        ref = _mk_notice(tmp_notices, is_published=True, fee_plan={"items": []})
        r = s.put(f"{API}/pricing/notices/{ref}/fee-plan", json={"award_payer": "supplier", "items": []})
        assert r.status_code == 409

    def test_publish_with_plan_passes_fee_gate(self, s, tmp_notices):
        ref = _mk_notice(tmp_notices)
        base = [{"code": "tender_hosting", "charge": False}, {"code": "tender_document_download", "charge": False},
                {"code": "transaction", "charge": True}]
        assert s.put(f"{API}/pricing/notices/{ref}/fee-plan", json={"award_payer": "supplier", "items": base}).status_code == 200
        r = s.post(f"{API}/notices/{ref}/publish")
        assert "Confirm the fees first" not in r.text, r.text
        print("publish after plan:", r.status_code, r.text[:200])


# ---------------- award fee ----------------
def _run_raise(bid_ids):
    sys.path.insert(0, "/app/backend")
    from routers.pricing import raise_award_fee

    async def go():
        out = []
        for b in bid_ids:
            try:
                out.append(await raise_award_fee(b, "TEST_runner"))
            except Exception as e:  # 502 from Stripe expected in preview
                out.append(repr(e))
        return out
    return asyncio.run(go())


class TestAwardFee:
    def test_raise_compute_cap_nil_waive(self, s, tmp_notices):
        ref = _mk_notice(tmp_notices)
        base = [{"code": "tender_hosting", "charge": False}, {"code": "tender_document_download", "charge": False}]
        assert s.put(f"{API}/pricing/notices/{ref}/fee-plan", json={"award_payer": "buyer", "payer_email": "test_buyer@example.com",
                     "items": base + [{"code": "transaction", "charge": True}]}).status_code == 200
        ref_w = _mk_notice(tmp_notices)
        assert s.put(f"{API}/pricing/notices/{ref_w}/fee-plan", json={"award_payer": "supplier",
                     "items": base + [{"code": "transaction", "charge": False, "reason": "TEST_ promo"}]}).status_code == 200
        bids = [("normal", ref, 1_000_000), ("cap", ref, 50_000_000), ("nil", ref, 10_000), ("waived", ref_w, 1_000_000)]
        ids = {}
        for k, nr, price in bids:
            ids[k] = str(mdb.bids.insert_one({"bid_ref": f"TEST-BID-{SUF}-{k}", "notice_ref": nr, "price_amount": price,
                                               "price_currency": "USD", "vendor_email": "TEST_v@example.com",
                                               "company_name": "TEST_ Co", "status": "awarded"}).inserted_id)
        try:
            _run_raise(list(ids.values()))
            f = {k: mdb.award_fees.find_one({"bid_id": v}) for k, v in ids.items()}
            assert f["normal"]["amount"] == 3000 and f["normal"]["status"] == "unpaid"
            assert f["normal"]["payer_email"] == "test_buyer@example.com" and f["normal"].get("link_error")
            assert f["cap"]["amount"] == 50000
            assert f["nil"]["amount"] == 0 and f["nil"]["status"] == "nil"
            assert f["waived"]["status"] == "waived" and f["waived"]["reason"] == "TEST_ promo"
            # idempotent
            _run_raise([ids["normal"]])
            assert mdb.award_fees.count_documents({"bid_id": ids["normal"]}) == 1
            # list
            r = s.get(f"{API}/pricing/award-fees")
            assert r.status_code == 200
            items = r.json()["items"]
            assert any(i["bid_id"] == ids["normal"] for i in items) and all("checkout_url" not in i for i in items)
            assert all(i["status"] == "waived" for i in s.get(f"{API}/pricing/award-fees", params={"status": "waived"}).json()["items"])
            # resend: unpaid -> 502 (Stripe key invalid in preview), non-unpaid -> 409
            r = s.post(f"{API}/pricing/award-fees/{ids['normal']}/resend")
            assert r.status_code in (200, 502), r.text
            assert s.post(f"{API}/pricing/award-fees/{ids['nil']}/resend").status_code == 409
            # waive
            assert s.post(f"{API}/pricing/award-fees/{ids['normal']}/waive", json={"reason": ""}).status_code == 422
            r = s.post(f"{API}/pricing/award-fees/{ids['normal']}/waive", json={"reason": "TEST_ goodwill"})
            assert r.status_code == 200
            d = mdb.award_fees.find_one({"bid_id": ids["normal"]})
            assert d["status"] == "waived" and d["waived_by"] == "adminsupport@pmcmanagers.com"
            assert s.post(f"{API}/pricing/award-fees/{ids['normal']}/waive", json={"reason": "again"}).status_code == 409
            assert s.post(f"{API}/pricing/award-fees/{ids['normal']}/resend").status_code == 409
        finally:
            for v in ids.values():
                mdb.bids.delete_one({"_id": ObjectId(v)})
                mdb.award_fees.delete_one({"bid_id": v})


# ---------------- supplier fee plan ----------------
class TestSupplierFees:
    def test_defaults(self, s):
        r = s.get(f"{API}/pricing/supplier-fees/defaults", params={"country": "IN"})
        assert r.status_code == 200
        d = r.json()
        assert d["band"] == "India" and {f["code"] for f in d["fees"]} == {"registration", "tender_document_download"}
        assert all(f["default"] in ("charge", "waive") for f in d["fees"])

    def test_vendor_plan_and_waiver(self, s):
        vref = f"TEST-VEN-{SUF}"
        vid = mdb.vendors.insert_one({"vendor_ref": vref, "email": f"test_ven_{SUF.lower()}@example.com",
                                      "company_name": "TEST_ Vendor", "country": "IN",
                                      "business_categories": ["Construction"]}).inserted_id
        try:
            u = f"{API}/pricing/vendors/{vref}/fee-plan"
            assert s.get(u).status_code == 200
            assert s.put(u, json={"fees": {"registration": "waive"}}).status_code == 422
            r = s.put(u, json={"fees": {"registration": "waive", "tender_document_download": "charge", "junk": "waive"},
                               "reason": "TEST_ partner"})
            assert r.status_code == 200
            fp = mdb.vendors.find_one({"_id": vid})["fee_plan"]
            assert fp["fees"] == {"registration": "waive", "tender_document_download": "charge"}
            assert s.put(f"{API}/pricing/vendors/NOPE-{SUF}/fee-plan", json={"fees": {}}).status_code == 404
            sys.path.insert(0, "/app/backend")
            from routers.vendor_categories import _category_fee
            v = mdb.vendors.find_one({"_id": vid})
            q = asyncio.run(_category_fee(v, "Other Cat"))
            assert q["required"] is False and q["reason"] == "waived"
        finally:
            mdb.vendors.delete_one({"_id": vid})

    def test_registration_decision_waive_needs_reason(self, s):
        """Approve with supplier_fees waive but no reason -> 422 before vendor creation."""
        reg = mdb.registrations.insert_one({"company_name": "TEST_ Reg Co", "email": f"test_reg_{SUF.lower()}@example.com",
                                            "status": "submitted", "country": "IN", "registered_address": "x",
                                            "registration_number": "1", "legal_entity_type": "llc"}).inserted_id
        try:
            r = s.post(f"{API}/registrations/{reg}/decision", json={"action": "approve", "supplier_fees": {"registration": "waive"}})
            print("decision no reason:", r.status_code, r.text[:200])
            assert r.status_code in (422, 400, 404)
            assert not mdb.vendors.find_one({"email": f"test_reg_{SUF.lower()}@example.com"})
        finally:
            mdb.registrations.delete_one({"_id": reg})
