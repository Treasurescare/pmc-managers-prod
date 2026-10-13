"""Public URL regression tests for v52cn masters/geography/UNSPSC/country-licenses + registration slot."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def test_countries_returns_250_with_regex_key(s):
    r = s.get(f"{API}/masters/countries", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("countries") or data.get("data") or []
    assert len(rows) >= 240, f"expected ~250 countries, got {len(rows)}"
    for row in rows[:10]:
        assert "postal_code_regex" in row, f"missing postal_code_regex in {row}"


def test_states_india_contains_maharashtra(s):
    r = s.get(f"{API}/masters/states", params={"country_code": "IN"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("states") or data.get("data") or []
    names = [str(x.get("name", "")).lower() for x in rows]
    assert any("maharashtra" in n for n in names), f"maharashtra missing in {names[:20]}"


def test_cities_mumbai(s):
    # Pass common param variants
    r = s.get(f"{API}/masters/cities", params={"country_code": "IN", "state_code": "MH", "q": "Mumbai"}, timeout=30)
    if r.status_code != 200:
        r = s.get(f"{API}/masters/cities", params={"country_code": "IN", "state": "Maharashtra", "q": "Mumbai"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("cities") or data.get("data") or []
    assert any("mumbai" in str(x.get("name", "")).lower() for x in rows), f"no Mumbai in {rows[:5]}"


def test_unspsc_search_solar(s):
    r = s.get(f"{API}/masters/unspsc/public/search", params={"q": "solar"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("results") or data.get("data") or []
    assert len(rows) > 0
    for row in rows[:5]:
        assert row.get("code") and row.get("title_en")


def test_unspsc_search_biogas_synonyms(s):
    r = s.get(f"{API}/masters/unspsc/public/search", params={"q": "biogas"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("results") or data.get("data") or []
    assert len(rows) > 0
    titles = " ".join(str(x.get("title_en", "")).lower() for x in rows)
    assert any(k in titles for k in ("methane", "digester", "anaerobic", "biogas")), titles[:300]


def test_unspsc_numeric_prefix_2320(s):
    r = s.get(f"{API}/masters/unspsc/public/search", params={"q": "2320"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items") or data.get("results") or data.get("data") or []
    assert len(rows) > 0
    assert any(str(x.get("code", "")).startswith("2320") for x in rows), [x.get("code") for x in rows[:10]]


def test_country_licenses_IN_has_gst_pan(s):
    r = s.get(f"{API}/masters/country-licenses/IN", timeout=30)
    assert r.status_code == 200
    data = r.json()
    licenses = data.get("licenses", data) if isinstance(data, dict) else data
    codes = [str(x.get("code", "")).lower() for x in licenses]
    assert "gst" in codes and "pan" in codes, codes


def test_country_licenses_ZZ_empty(s):
    r = s.get(f"{API}/masters/country-licenses/ZZ", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("country_code") == "ZZ"
    assert data.get("licenses") == []


def test_put_country_licenses_requires_auth(s):
    r = s.put(f"{API}/masters/country-licenses/IN", json={"licenses": []}, timeout=30)
    assert r.status_code in (401, 403), r.status_code


def test_registration_dynamic_slot_not_unknown(s):
    # Valid-format slot but non-existent registration oid => should NOT return 'Unknown slot'.
    fake_oid = "507f1f77bcf86cd799439011"
    r = s.post(
        f"{API}/registrations/{fake_oid}/documents/country_license_IN_gst",
        files={"file": ("x.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"token": "dummy-token"},
        timeout=30,
    )
    body = (r.text or "").lower()
    assert "unknown slot" not in body, f"slot wrongly rejected: {r.status_code} {body[:200]}"


def test_registration_truly_unknown_slot_rejected(s):
    fake_oid = "507f1f77bcf86cd799439011"
    r = s.post(
        f"{API}/registrations/{fake_oid}/documents/not_a_real_slot",
        files={"file": ("x.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"token": "dummy-token"},
        timeout=30,
    )
    assert r.status_code == 400, (r.status_code, r.text[:200])
    assert "unknown slot" in (r.text or "").lower()
