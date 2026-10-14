"""v52cz — regression coverage for the two download defects:

1. `GET /api/v1/notices/{ref}/pack` returns a usable ZIP for a published
   notice that has a primary document + attachments, and 404s cleanly if
   the notice has no documents linked.
2. `POST /api/v1/uploads/bundle` bundles a set of upload keys into one ZIP
   for signed-in callers, skips vanished keys without failing the whole
   request, and 404s cleanly when nothing resolves.
"""
from __future__ import annotations
import io
import os
import uuid
import zipfile
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _admin_session() -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"},
               timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    s.headers.update({
        "Authorization": f"Bearer {data['token']}",
        "X-CSRF-Token": data.get("csrf_token") or "",
    })
    if data.get("csrf_token") and not s.cookies.get("csrf_token"):
        s.cookies.set("csrf_token", data["csrf_token"])
    return s, data


def _tiny_pdf() -> bytes:
    """Minimal but valid PDF so magic-byte validation accepts it."""
    body = (b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n"
            b"0000000018 00000 n \n0000000057 00000 n \n"
            b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n100\n%%EOF\n")
    # Pad to at least 200 bytes so the backend's _validate_document_bytes
    # minimum size guard is satisfied.
    pad = b"% padding " + b"0" * 220
    return body + pad


def _publish_notice_with_doc(s: requests.Session) -> str:
    tag = uuid.uuid4().hex[:6]
    from datetime import datetime, timedelta, timezone
    deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    payload = {
        "title": f"v52cz pack smoke {tag}",
        "description": "regression — download pack",
        "category": "Civil Works",
        "document_type": "tender",
        "budget_amount": 100000,
        "budget_currency": "USD",
        "delivery_country": "KZ",
        "submission_deadline": deadline,
        "is_published": True,
    }
    r = s.post(f"{API}/notices", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    ref = r.json()["notice_ref"]
    # Attach a primary document so the pack endpoint has something to zip.
    files = {"file": (f"primary-{tag}.pdf", _tiny_pdf(), "application/pdf")}
    data = {"kind": "primary"}
    r = s.post(f"{API}/notices/{ref}/document", files=files, data=data, timeout=20)
    assert r.status_code == 200, r.text
    return ref


def test_notice_pack_returns_zip_for_published_notice():
    s, _ = _admin_session()
    ref = _publish_notice_with_doc(s)
    # Pack endpoint is public — no auth session.
    r = requests.get(f"{API}/notices/{ref}/pack", timeout=20)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/zip"), r.headers
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    # README manifest is always present, plus the primary pdf.
    assert "README.txt" in names
    assert any(n.lower().endswith(".pdf") for n in names), names


def test_notice_pack_404s_when_no_documents_linked():
    s, _ = _admin_session()
    # Create but DO NOT attach any document.
    from datetime import datetime, timedelta, timezone
    deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    tag = uuid.uuid4().hex[:6]
    payload = {
        "title": f"v52cz empty {tag}",
        "description": "regression — empty pack",
        "category": "Civil Works",
        "document_type": "tender",
        "budget_amount": 50000,
        "budget_currency": "USD",
        "delivery_country": "KZ",
        "submission_deadline": deadline,
        "is_published": True,
    }
    r = s.post(f"{API}/notices", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    ref = r.json()["notice_ref"]
    r = requests.get(f"{API}/notices/{ref}/pack", timeout=15)
    assert r.status_code == 404, r.text


def _upload_direct(s: requests.Session, filename: str) -> str:
    """Round-trip a presign + direct upload. Returns storage key."""
    r = s.post(f"{API}/uploads/presign",
               json={"file_name": filename, "content_type": "application/pdf",
                     "scope": "bid-docs", "size_bytes": 400}, timeout=15)
    assert r.status_code == 200, r.text
    key = r.json()["key"]
    r = s.post(f"{API}/uploads/direct",
               data={"key": key},
               files={"file": (filename, _tiny_pdf(), "application/pdf")},
               timeout=20)
    assert r.status_code == 200, r.text
    return key


def test_uploads_bundle_zips_multiple_keys_for_admin():
    s, _ = _admin_session()
    tag = uuid.uuid4().hex[:6]
    keys = [_upload_direct(s, f"bundle-{tag}-{i}.pdf") for i in range(3)]
    r = s.post(f"{API}/uploads/bundle",
               json={"keys": keys, "filename": "bid-bundle-test"},
               timeout=25)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/zip"), r.headers
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert "README.txt" in names
    pdfs = [n for n in names if n.lower().endswith(".pdf")]
    assert len(pdfs) == 3, names


def test_uploads_bundle_requires_signin():
    r = requests.post(f"{API}/uploads/bundle",
                      json={"keys": ["bogus-key"]}, timeout=10)
    assert r.status_code == 401, r.text


def test_uploads_bundle_404s_when_all_keys_missing():
    s, _ = _admin_session()
    r = s.post(f"{API}/uploads/bundle",
               json={"keys": [f"bid-docs/{uuid.uuid4().hex}_missing.pdf"]},
               timeout=10)
    assert r.status_code == 404, r.text


def test_uploads_bundle_skips_missing_but_returns_present():
    s, _ = _admin_session()
    tag = uuid.uuid4().hex[:6]
    good = _upload_direct(s, f"bundle-mixed-{tag}.pdf")
    missing = f"bid-docs/{uuid.uuid4().hex}_gone.pdf"
    r = s.post(f"{API}/uploads/bundle",
               json={"keys": [good, missing], "filename": "mixed"},
               timeout=20)
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        readme = zf.read("README.txt").decode("utf-8")
        pdfs = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
    assert len(pdfs) == 1
    assert "Missing" in readme
