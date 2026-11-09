# v60k — base64-in-JSON upload middleware (X-PMC-Upload: b64) regression tests
import base64
import hashlib
import os
import uuid

import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
REG = f"{BASE_URL}/api/v1/registrations"

_created_regs = []


def _mongo():
    env = {}
    with open("/app/backend/.env") as fh:
        for line in fh:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"')
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


@pytest.fixture(scope="module")
def draft():
    email = f"TEST_b64_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(REG, json={"email": email, "company_name": "TEST_B64 Co"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "id" in d and "magic_token" in d
    _created_regs.append(d["id"])
    yield d
    db = _mongo()
    for rid in _created_regs:
        db.uploads.delete_many({"key": {"$regex": f"^registration-docs/{rid}/"}})
        db.registrations.delete_one({"_id": ObjectId(rid)})


def _jpg_bytes(n=200_000):
    # JPEG header + pseudo random bytes containing XSS-looking sequences
    return b"\xff\xd8\xff\xe0" + os.urandom(n) + b"<script>alert(1)</script>" + b"\xff\xd9"


def _b64_post(url, payload, extra_headers=None):
    h = {"Content-Type": "application/json", "X-PMC-Upload": "b64"}
    h.update(extra_headers or {})
    return requests.post(url, json=payload, headers=h)


class TestB64Upload:
    # Core: b64 JSON upload -> byte-identical round trip
    def test_b64_upload_roundtrip(self, draft):
        data = _jpg_bytes()
        payload = {"fields": [{"name": "token", "value": draft["magic_token"]}],
                   "files": [{"name": "file", "filename": "TEST_cert.jpg", "type": "image/jpeg",
                              "b64": base64.b64encode(data).decode()}]}
        r = _b64_post(f"{REG}/{draft['id']}/documents/incorporation_certificate", payload)
        assert r.status_code == 200, r.text
        meta = r.json()
        assert meta["file_name"] == "TEST_cert.jpg"
        assert meta["content_type"] == "image/jpeg"
        assert meta["size_bytes"] == len(data)
        g = requests.get(f"{REG}/{draft['id']}/documents/incorporation_certificate/file",
                         params={"token": draft["magic_token"], "download": "true"})
        assert g.status_code == 200
        assert hashlib.md5(g.content).hexdigest() == hashlib.md5(data).hexdigest()
        assert g.headers["content-type"].startswith("image/jpeg")

    def test_b64_pdf_and_png(self, draft):
        for slot, fn, ct, data in [
            ("incorporation_certificate", "TEST_doc.pdf", "application/pdf", b"%PDF-1.4\n" + os.urandom(50_000) + b"\n%%EOF"),
            ("incorporation_certificate", "TEST_img.png", "image/png", b"\x89PNG\r\n\x1a\n" + os.urandom(30_000)),
        ]:
            payload = {"fields": [{"name": "token", "value": draft["magic_token"]}],
                       "files": [{"name": "file", "filename": fn, "type": ct, "b64": base64.b64encode(data).decode()}]}
            r = _b64_post(f"{REG}/{draft['id']}/documents/{slot}", payload)
            assert r.status_code == 200, r.text
            g = requests.get(f"{REG}/{draft['id']}/documents/{slot}/file", params={"token": draft["magic_token"]})
            assert g.content == data
            assert g.headers["content-type"].startswith(ct)

    def test_non_ascii_filename(self, draft):
        data = b"%PDF-1.4\n" + os.urandom(1000)
        fn = "TEST_Сертификат_ü.pdf"
        payload = {"fields": [{"name": "token", "value": draft["magic_token"]}],
                   "files": [{"name": "file", "filename": fn, "type": "application/pdf", "b64": base64.b64encode(data).decode()}]}
        r = _b64_post(f"{REG}/{draft['id']}/documents/incorporation_certificate", payload)
        assert r.status_code == 200, r.text
        assert r.json()["file_name"] == fn, f"filename mangled: {r.json()['file_name']!r}"

    def test_oversize_rejected(self, draft):
        data = os.urandom(6 * 1024 * 1024)
        payload = {"fields": [{"name": "token", "value": draft["magic_token"]}],
                   "files": [{"name": "file", "filename": "TEST_big.pdf", "type": "application/pdf", "b64": base64.b64encode(data).decode()}]}
        r = _b64_post(f"{REG}/{draft['id']}/documents/incorporation_certificate", payload)
        assert r.status_code == 413, r.text
        assert "limit" in r.json()["detail"].lower()

    # Legacy multipart (no header) still works
    def test_plain_multipart_still_works(self, draft):
        data = _jpg_bytes(10_000)
        r = requests.post(f"{REG}/{draft['id']}/documents/incorporation_certificate",
                          data={"token": draft["magic_token"]},
                          files={"file": ("TEST_mp.jpg", data, "image/jpeg")})
        assert r.status_code == 200, r.text
        g = requests.get(f"{REG}/{draft['id']}/documents/incorporation_certificate/file", params={"token": draft["magic_token"]})
        assert g.content == data

    # Error handling of middleware
    @pytest.mark.parametrize("body", ["{not json", "", '{"files":[{"name":"file","b64":"@@@notb64"}]}',
                                      '{"files":[{"filename":"x","b64":"QQ=="}]}', '[1,2]'])
    def test_malformed_returns_400(self, draft, body):
        r = requests.post(f"{REG}/{draft['id']}/documents/incorporation_certificate", data=body,
                          headers={"Content-Type": "application/json", "X-PMC-Upload": "b64"})
        assert r.status_code == 400, f"{body!r} -> {r.status_code} {r.text}"
        assert r.json() == {"detail": "Malformed upload"}

    def test_missing_token_field_422(self, draft):
        payload = {"fields": [], "files": [{"name": "file", "filename": "a.jpg", "type": "image/jpeg", "b64": "QUFB"}]}
        r = _b64_post(f"{REG}/{draft['id']}/documents/incorporation_certificate", payload)
        assert r.status_code == 422

    def test_bad_token_404(self, draft):
        payload = {"fields": [{"name": "token", "value": "bogus"}],
                   "files": [{"name": "file", "filename": "a.jpg", "type": "image/jpeg", "b64": "QUFB"}]}
        r = _b64_post(f"{REG}/{draft['id']}/documents/incorporation_certificate", payload)
        assert r.status_code == 404

    def test_header_on_normal_json_endpoint_is_harmless_when_absent(self):
        # Non-upload JSON calls (no header) are untouched
        r = requests.get(f"{REG}/document-slots/schema")
        assert r.status_code == 200


class TestVendorUploads:
    # Supplier authenticated upload via /uploads/direct with b64
    def test_vendor_direct_upload_b64(self):
        s = requests.Session()
        lr = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                    json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
        if lr.status_code != 200:
            pytest.skip(f"vendor login failed {lr.status_code} {lr.text[:200]}")
        tok = lr.json().get("access_token") or lr.json().get("token")
        csrf = lr.json().get("csrf_token")
        h = {}
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        if csrf:
            h["X-CSRF-Token"] = csrf
        data = b"%PDF-1.4\n" + os.urandom(2000)
        pre = s.post(f"{BASE_URL}/api/v1/uploads/presign", headers=h,
                     json={"file_name": "TEST_v.pdf", "content_type": "application/pdf", "scope": "vendor-docs", "size_bytes": len(data)})
        assert pre.status_code == 200, pre.text
        key = pre.json()["key"]
        payload = {"fields": [{"name": "key", "value": key}],
                   "files": [{"name": "file", "filename": "TEST_v.pdf", "type": "application/pdf", "b64": base64.b64encode(data).decode()}]}
        r = s.post(f"{BASE_URL}/api/v1/uploads/direct", json=payload, headers={**h, "X-PMC-Upload": "b64"})
        assert r.status_code == 200, r.text
        g = s.get(f"{BASE_URL}/api/v1/uploads/files/{key}", headers=h)
        assert g.status_code == 200, g.text
        assert g.content == data
        _mongo().uploads.delete_one({"key": key})


class TestAdminUploads:
    # Admin authenticated b64 upload (CSRF header must survive middleware) — packages import
    @pytest.fixture(scope="class")
    def admin(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/staff/auth/login",
                   json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
        if r.status_code != 200:
            pytest.skip(f"admin login failed {r.status_code}")
        j = r.json()
        h = {"X-CSRF-Token": j.get("csrf_token", "")}
        if j.get("access_token"):
            h["Authorization"] = f"Bearer {j['access_token']}"
        return s, h

    def _post(self, admin, filename, content, ctype="text/csv"):
        s, h = admin
        payload = {"fields": [], "files": [{"name": "file", "filename": filename, "type": ctype,
                                            "b64": base64.b64encode(content).decode()}]}
        return s.post(f"{BASE_URL}/api/v1/packages/import", json=payload, headers={**h, "X-PMC-Upload": "b64"})

    def test_packages_import_wrong_type(self, admin):
        r = self._post(admin, "TEST_pk.txt", b"hello", "text/plain")
        assert r.status_code == 400, r.text
        assert "csv" in r.json()["detail"].lower()

    def test_packages_import_csv_rows_skipped(self, admin):
        # Rows lacking title/category are skipped -> nothing created, proves CSV body reached endpoint
        r = self._post(admin, "TEST_pk.csv", b"title,category\n,\n,\n")
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 0
        assert r.json()["skipped"] == 2
