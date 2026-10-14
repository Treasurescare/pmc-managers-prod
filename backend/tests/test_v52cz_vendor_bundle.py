"""v52cz vendor-side coverage — POST /api/v1/uploads/bundle must also
accept the vendor cookie session (same auth gate as /files/{key}).
"""
from __future__ import annotations
import io
import os
import uuid
import zipfile
import requests

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://pmc-forest-green.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api/v1"


def _tiny_pdf() -> bytes:
    body = (b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n"
            b"0000000018 00000 n \n0000000057 00000 n \n"
            b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n100\n%%EOF\n")
    pad = b"% padding " + b"0" * 220
    return body + pad


def _vendor_session() -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{API}/vendor/auth/login",
        json={"email": "manualvendor@pmcmanagers.com",
              "password": "Vendor@12345"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    # Vendor auth uses httpOnly cookies; nothing more required.
    return s


def test_uploads_bundle_works_for_vendor_cookie():
    s = _vendor_session()
    tag = uuid.uuid4().hex[:6]
    # presign + direct upload under the vendor cookie
    r = s.post(f"{API}/uploads/presign",
               json={"file_name": f"vendor-bundle-{tag}.pdf",
                     "content_type": "application/pdf",
                     "scope": "bid-docs", "size_bytes": 400},
               timeout=15)
    assert r.status_code == 200, r.text
    key = r.json()["key"]
    r = s.post(f"{API}/uploads/direct",
               data={"key": key},
               files={"file": (f"vendor-bundle-{tag}.pdf", _tiny_pdf(),
                               "application/pdf")},
               timeout=20)
    assert r.status_code == 200, r.text

    r = s.post(f"{API}/uploads/bundle",
               json={"keys": [key], "filename": "vendor-bundle"},
               timeout=20)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert "README.txt" in names
    assert any(n.lower().endswith(".pdf") for n in names), names
