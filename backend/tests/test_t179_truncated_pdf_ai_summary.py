# Iteration 179: Supplier AI summary — truncated PDF friendly 400 (not 502), scanned PDF/JPG still 200
import random

import pytest
import requests
from test_t178_scanned_pdf_summary import API, _bytes, _check_summary, _tender_image
from test_t178_scanned_pdf_summary import vs as _vs_fixture

vs = _vs_fixture

FRIENDLY = "This PDF looks damaged or only partly downloaded"


@pytest.mark.parametrize("cut", [300, 3000, 20000, -100])
def test_truncated_pdf_friendly_400(vs, cut):
    pdf = _bytes(_tender_image(random.randint(1, 99999)), "PDF")
    body = pdf[:cut]
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_trunc.pdf", body, "application/pdf")}, timeout=120)
    print("TRUNC", cut, r.status_code, r.text[:200])
    assert r.status_code == 400, r.text[:300]
    assert r.headers.get("content-type", "").startswith("application/json")
    assert FRIENDLY in r.json()["detail"]


def test_scanned_pdf_still_200(vs):
    pdf = _bytes(_tender_image(random.randint(100000, 999999)), "PDF")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_scan.pdf", pdf, "application/pdf")}, timeout=180)
    _check_summary(r)


def test_scanned_jpg_still_200(vs):
    jpg = _bytes(_tender_image(random.randint(100000, 999999)), "JPEG")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_photo.jpg", jpg, "image/jpeg")}, timeout=180)
    _check_summary(r)


def test_garbage_pdf_400(vs):
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_bad.pdf", b"garbage bytes " * 20, "application/pdf")}, timeout=60)
    assert r.status_code == 400
    assert "Traceback" not in r.text


def test_unauth_401():
    r = requests.post(f"{API}/supplier-ai/summary", data={"notice_ref": "DEMO-TND-001"})
    assert r.status_code == 401
