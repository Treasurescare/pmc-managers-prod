"""v52cz rev6 — regression for the escrow registration quality-of-life pass.

Covers:
- Save-as-draft at any step (PATCH with partial payload, no 422).
- Documents viewer via magic-token endpoint (no auth needed).
- Banks master: filter by country + search by q.
- Dual phone fields persisted.
"""
from __future__ import annotations
import os
import io
import uuid
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _tiny_pdf():
    return (b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n0000000018 00000 n \n0000000057 00000 n \n"
            b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n100\n%%EOF\n"
            + b"% pad " + b"0" * 220)


def _bare_register():
    """Create a bare draft just like step-1 would from the UI."""
    tag = uuid.uuid4().hex[:6]
    payload = {
        "legal_name": "Rev6 Bank " + tag,
        "primary_contact_email": f"rev6.{tag}@test.io",
        "country": "IN",
    }
    r = requests.post(f"{API}/escrow-institutions/register", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def test_banks_master_filter_by_country_and_search():
    r = requests.get(f"{API}/masters/banks",
                     params={"country_code": "IN"}, timeout=10)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) >= 5, rows
    assert all(b["country_code"] == "IN" for b in rows)
    # Search narrows to a specific bank.
    r = requests.get(f"{API}/masters/banks",
                     params={"country_code": "IN", "q": "SBI"}, timeout=10)
    names = [b["name"] for b in r.json()]
    assert any("State Bank" in n for n in names), names


def test_banks_master_empty_for_unknown_country():
    r = requests.get(f"{API}/masters/banks",
                     params={"country_code": "ZZ"}, timeout=10)
    assert r.status_code == 200 and r.json() == []


def test_save_as_draft_with_only_partial_fields():
    """Legacy POST /register already requires nothing more than contact
    email. Then PATCH with just one new field must succeed — the user
    hit 422 before because the model required address + reg_number."""
    inst = _bare_register()
    r = requests.patch(f"{API}/escrow-institutions/{inst['id']}",
                       params={"token": inst["magic_token"]},
                       json={"legal_name": "Rev6 Bank — Updated",
                              "mobile_phone": "+919876543210",
                              "office_phone":  "+912212345678"},
                       timeout=10)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["mobile_phone"] == "+919876543210"
    assert out["office_phone"] == "+912212345678"


def test_document_viewer_via_magic_token_serves_file():
    """The previous flow sent the user to /uploads/files/{key} which 401s
    for anonymous callers ('Sign in to download tender documents'). The
    new /escrow-institutions/{iid}/documents/{slot}/file endpoint accepts
    the registration's magic token and streams the file."""
    inst = _bare_register()
    # Presign + direct-upload a tiny PDF (admin session needed for presign).
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"},
               timeout=15)
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}",
                      "X-CSRF-Token": d.get("csrf_token") or ""})
    if d.get("csrf_token") and not s.cookies.get("csrf_token"):
        s.cookies.set("csrf_token", d["csrf_token"])
    r = s.post(f"{API}/uploads/presign",
               json={"file_name": "licence.pdf",
                     "content_type": "application/pdf",
                     "scope": "escrow-inst", "size_bytes": 300}, timeout=10)
    key = r.json()["key"]
    s.post(f"{API}/uploads/direct", data={"key": key},
           files={"file": ("licence.pdf", _tiny_pdf(), "application/pdf")},
           timeout=15)
    # Attach the upload reference to the registration (anonymous PATCH
    # with the magic token, just like the UI does).
    requests.patch(f"{API}/escrow-institutions/{inst['id']}",
                   params={"token": inst["magic_token"]},
                   json={"documents": {"regulatory_licence":
                                       {"key": key, "filename": "licence.pdf",
                                        "size_bytes": 300}}},
                   timeout=10)
    # Fetch via the new endpoint — no session, just the magic token.
    r = requests.get(
        f"{API}/escrow-institutions/{inst['id']}/documents/regulatory_licence/file",
        params={"token": inst["magic_token"], "download": "true"}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"


def test_document_viewer_rejects_wrong_token():
    inst = _bare_register()
    r = requests.get(
        f"{API}/escrow-institutions/{inst['id']}/documents/regulatory_licence/file",
        params={"token": "not-the-real-token"}, timeout=10)
    assert r.status_code == 404
