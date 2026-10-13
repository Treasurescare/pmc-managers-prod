"""v52cn — regression tests for the Masters v2 API family.

Hits the live backend via REACT_APP_BACKEND_URL (same pattern as other
test_v52* files). Verifies:
- Geography endpoints return the imported dr5hn dataset and support
  country/state/text filters.
- UNSPSC search surfaces results from the full codeset and respects the
  synonym expansion in masters_v2.py (e.g. "biogas" → methane/digester/anaerobic).
- Country licenses: public GET is open, PUT is admin-gated.
- Registration upload endpoint accepts the dynamic
  `country_license_{CC}_{code}` slot keys and rejects truly unknown slots.
"""
from __future__ import annotations
import io
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


# ---------- Geography ----------
def test_countries_returns_full_master():
    r = requests.get(f"{API}/masters/countries", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 240, f"Expected ~250 countries, got {len(data)}"
    codes = {c["code"] for c in data}
    assert {"IN", "US", "GB", "KZ", "AE", "SG"}.issubset(codes)
    assert all("postal_code_regex" in c for c in data)


def test_states_filtered_by_country():
    r = requests.get(f"{API}/masters/states", params={"country_code": "IN"}, timeout=15)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and len(rows) > 20
    assert "Maharashtra" in {s["name"] for s in rows}


def test_cities_search_scoped_to_state():
    states = requests.get(f"{API}/masters/states", params={"country_code": "IN"}, timeout=15).json()
    mh = next(s for s in states if s["name"] == "Maharashtra")
    r = requests.get(f"{API}/masters/cities", params={
        "country_code": "IN", "state_code": mh["state_code"], "q": "Mumbai",
    }, timeout=15)
    assert r.status_code == 200
    assert any("Mumbai" in c["name"] for c in r.json())


# ---------- UNSPSC ----------
def test_unspsc_public_search_full_codeset():
    r = requests.get(f"{API}/masters/unspsc/public/search",
                     params={"q": "solar", "limit": 5}, timeout=15)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and len(rows) > 0
    assert all("code" in x and "title_en" in x for x in rows)


def test_unspsc_biogas_synonym_expansion():
    """UNSPSC dataset lacks the literal word "biogas"; masters_v2 expands
    it to methane / digester / anaerobic."""
    r = requests.get(f"{API}/masters/unspsc/public/search",
                     params={"q": "biogas", "limit": 20}, timeout=15)
    assert r.status_code == 200
    titles = " ".join(x["title_en"].lower() for x in r.json())
    assert any(k in titles for k in ("methane", "digester", "anaerobic")), \
        f"synonym expansion failed; titles={titles!r}"


def test_unspsc_numeric_prefix_search():
    r = requests.get(f"{API}/masters/unspsc/public/search",
                     params={"q": "2320", "limit": 5}, timeout=15)
    assert r.status_code == 200
    for row in r.json():
        assert row["code"].lstrip("0").startswith("2320") or row["code"].startswith("2320")


# ---------- Country licenses ----------
def test_country_license_public_get_india():
    r = requests.get(f"{API}/masters/country-licenses/IN", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["country_code"] == "IN"
    codes = {l["code"] for l in data.get("licenses") or []}
    assert "gst" in codes and "pan" in codes


def test_country_license_unseeded_country_returns_empty():
    r = requests.get(f"{API}/masters/country-licenses/ZZ", timeout=15)
    assert r.status_code == 200
    assert r.json() == {"country_code": "ZZ", "licenses": []}


def test_country_license_put_requires_admin():
    r = requests.put(f"{API}/masters/country-licenses/IN",
                     json={"licenses": [{"code": "test", "name": "Test", "mandatory": False}]},
                     timeout=15)
    assert r.status_code in (401, 403)


# ---------- Dynamic registration slots ----------
def test_registration_dynamic_license_slot_accepted():
    """`country_license_*` slot keys must pass the whitelist check
    (so the registration lookup is what fails, not an 'Unknown slot' 400)."""
    files = {"file": ("x.pdf", io.BytesIO(b"x"), "application/pdf")}
    data = {"token": "x"}
    r = requests.post(
        f"{API}/registrations/507f1f77bcf86cd799439011/documents/country_license_IN_gst",
        files=files, data=data, timeout=15,
    )
    assert r.status_code in (400, 404)
    assert "Unknown slot" not in r.text, r.text


def test_registration_bogus_slot_rejected():
    files = {"file": ("x.pdf", io.BytesIO(b"x"), "application/pdf")}
    data = {"token": "x"}
    r = requests.post(
        f"{API}/registrations/507f1f77bcf86cd799439011/documents/not_a_real_slot",
        files=files, data=data, timeout=15,
    )
    assert r.status_code == 400
    assert "Unknown slot" in r.text
