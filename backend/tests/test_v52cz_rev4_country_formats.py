"""v52cz rev4 — country-specific identifier formats master.

Regression for the Escrow Institution Core form rewrite: the public
`/api/v1/masters/country-formats/{cc}` endpoint must return the right
label + example + regex for every seeded country, and gracefully degrade
to null fields for anything not seeded (so the UI falls back to free
text instead of erroring)."""
from __future__ import annotations
import os
import re
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def test_country_formats_india_regex_matches_real_cin():
    r = requests.get(f"{API}/masters/country-formats/IN", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["country_code"] == "IN"
    reg = data["reg_number"]
    assert reg and reg["label"].startswith("CIN")
    # Real CINs from the MCA registry
    for sample in ("L17110MH1973PLC019786", "U72200MH2007PTC167548"):
        assert re.match(reg["regex"], sample), sample
    assert not re.match(reg["regex"], "random garbage")

    pan = data["tax_id"]
    assert pan and pan["label"] == "PAN"
    assert re.match(pan["regex"], "AAAPL1234C")
    assert not re.match(pan["regex"], "1234567890")


def test_country_formats_uk_companies_house():
    r = requests.get(f"{API}/masters/country-formats/GB", timeout=10)
    assert r.status_code == 200
    reg = r.json()["reg_number"]["regex"]
    for ok in ("12345678", "SC123456", "OC123456"):
        assert re.match(reg, ok), ok
    assert not re.match(reg, "ABC123")


def test_country_formats_kazakhstan_bin():
    r = requests.get(f"{API}/masters/country-formats/KZ", timeout=10)
    data = r.json()
    assert re.match(data["reg_number"]["regex"], "060140000385")
    assert not re.match(data["reg_number"]["regex"], "12345")


def test_country_formats_unknown_country_degrades_gracefully():
    """ISO country with no seeded formats must still 200 so the frontend
    can fall back to free-text with no false negatives."""
    r = requests.get(f"{API}/masters/country-formats/ZZ", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["country_code"] == "ZZ"
    assert data["reg_number"] is None
    assert data["tax_id"] is None
    assert data["vat"] is None


def test_country_formats_seeded_country_set_covers_the_big_15():
    """Every country we actually serve bidders from should be seeded so
    users don't fall into the free-text fallback by accident."""
    for cc in ("IN", "KZ", "SG", "JP", "CN", "AU", "AE", "SA", "GB",
               "DE", "FR", "US", "BR", "ZA", "NG", "RU", "UA"):
        r = requests.get(f"{API}/masters/country-formats/{cc}", timeout=10)
        assert r.status_code == 200, cc
        d = r.json()
        assert d["reg_number"] is not None, f"missing reg_number seed for {cc}"
        # tax_id or vat should be present for the big economies
        if cc in ("IN", "KZ", "GB", "DE", "FR", "SA", "AE", "US", "BR"):
            assert d["tax_id"] is not None, f"missing tax_id seed for {cc}"
