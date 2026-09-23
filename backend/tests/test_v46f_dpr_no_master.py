"""v46f — DPR no-master workflow: build a brand-new master from a DPR.

Verifies:
  1. Login (cookie session + csrf_token in body).
  2. POST /api/v1/tender-pro/dpr/analyze-json accepts base64 TXT and returns header+section_bodies.
  3. POST /api/v1/tender-templates creates a DRAFT (is_master=false).
  4. POST /api/v1/tender-pro/templates/{tid}/save-as-master creates a MASTER
     with top-level country and industry, name ending with '· GB master'.
  5. Cleanup: draft template deleted, master remains (cannot be deleted via API).
"""
import base64
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORDS = ["Admin@12345", "Admin@123"]

DPR_TXT = (
    "Detailed Project Report: Construction of 40km highway in Wales.\n"
    "Estimated budget GBP 12 million. Duration 18 months.\n"
    "Scope: Design, build and commissioning of a two-lane highway including bridges, drainage,\n"
    "signage and safety barriers. Client is the Welsh Government.\n"
    "Evaluation: QCBS (technical 70, financial 30). EMD: 2% of tender value.\n"
    "Bid validity: 120 days. Location: Cardiff to Swansea corridor.\n"
    "Contractor eligibility: minimum turnover GBP 30 million for last 3 years, prior highway experience.\n"
)


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    csrf = None
    for pw in ADMIN_PASSWORDS:
        r = s.post(f"{BASE}/api/v1/staff/auth/login",
                   json={"email": ADMIN_EMAIL, "password": pw, "active_role": "admin"})
        if r.status_code == 200:
            csrf = r.json().get("csrf_token")
            break
    assert csrf, f"Admin login failed with all passwords. Last status={r.status_code} body={r.text[:200]}"
    s.headers.update({"X-CSRF-Token": csrf, "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    return {"draft": None, "master": None}


def test_login_cookie_and_csrf(admin_session):
    assert admin_session.headers.get("X-CSRF-Token")


def test_dpr_analyze_json_txt(admin_session, created_ids):
    b64 = base64.b64encode(DPR_TXT.encode("utf-8")).decode("ascii")
    r = admin_session.post(f"{BASE}/api/v1/tender-pro/dpr/analyze-json?kind=tender",
                            json={"filename": "wales_highway.txt", "content_b64": b64},
                            timeout=120)
    assert r.status_code == 200, f"analyze-json failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert "header" in data and "section_bodies" in data
    assert isinstance(data["section_bodies"], dict)
    created_ids["analyze"] = data


def test_create_draft_from_analyze(admin_session, created_ids):
    a = created_ids.get("analyze")
    assert a, "prior analyze must have run"
    header = dict(a.get("header") or {})
    header["country"] = "GB"
    header["dpr_warnings"] = a.get("warnings") or []
    sec_bodies = a.get("section_bodies") or {}
    if not sec_bodies:
        sec_bodies = {"sec-1": "<p>Placeholder</p>"}
    sections = [
        {"code": code, "kind": "section",
         "title": code.replace("_", " ").replace("-", " ").title(),
         "hint": None, "body": body, "order": i * 10}
        for i, (code, body) in enumerate(sec_bodies.items())
    ]
    ts = int(time.time())
    name = f"TEST_v46f QA Wales Highway {ts}"
    payload = {
        "name": name, "kind": "tender",
        "country": "GB", "industry": "infrastructure",
        "header": header, "sections": sections,
    }
    r = admin_session.post(f"{BASE}/api/v1/tender-templates", json=payload)
    assert r.status_code in (200, 201), f"create draft failed: {r.status_code} {r.text[:300]}"
    doc = r.json()
    assert doc.get("is_master") in (False, None), f"template should be draft, got is_master={doc.get('is_master')}"
    created_ids["draft"] = doc["id"]
    created_ids["draft_name"] = name


def test_save_as_master_persists_country_top_level(admin_session, created_ids):
    tid = created_ids["draft"]
    assert tid
    name = created_ids["draft_name"]
    r = admin_session.post(f"{BASE}/api/v1/tender-pro/templates/{tid}/save-as-master",
                            json={"country": "GB", "industry": "infrastructure",
                                  "name": f"{name} · GB master"})
    assert r.status_code == 200, f"save-as-master failed: {r.status_code} {r.text[:300]}"
    m = r.json()
    assert m.get("is_master") is True
    assert (m.get("country") or "").upper() == "GB"
    assert m.get("industry") == "infrastructure"
    assert m["name"].endswith("· GB master")
    created_ids["master"] = m["id"]


def test_master_visible_in_list(admin_session, created_ids):
    r = admin_session.get(f"{BASE}/api/v1/tender-templates")
    assert r.status_code == 200
    rows = r.json()
    mid = created_ids["master"]
    found = next((d for d in rows if d.get("id") == mid), None)
    assert found, "Newly created master not present in listing"
    assert found.get("is_master") is True
    assert (found.get("country") or "").upper() == "GB"


def test_cleanup_delete_draft(admin_session, created_ids):
    tid = created_ids.get("draft")
    if not tid:
        pytest.skip("no draft to delete")
    r = admin_session.delete(f"{BASE}/api/v1/tender-templates/{tid}")
    assert r.status_code in (200, 204), f"delete draft: {r.status_code} {r.text[:200]}"
