"""v48c Bug A — Vendor registration template PDF validation.

Verifies:
 1. GET /api/v1/vendors/registration-template returns 200 + application/pdf
 2. Default Content-Disposition starts with 'inline'
 3. Body starts with %PDF-1.4 and ends with %%EOF
 4. size_bytes > 3000
 5. pypdf can open it and .pages >= 2
 6. ?inline=false returns Content-Disposition starting with 'attachment'
"""
import io
import os
import pytest
import requests
from pypdf import PdfReader


def _base_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    return ""


BASE_URL = _base_url()
URL = f"{BASE_URL}/api/v1/vendors/registration-template"


class TestRegistrationTemplatePDF:
    def test_default_inline_pdf_valid(self):
        r = requests.get(URL, timeout=30)
        assert r.status_code == 200, r.text[:200]
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"unexpected content-type: {ct}"
        disp = r.headers.get("content-disposition", "")
        assert disp.lower().startswith("inline"), f"expected inline disposition, got: {disp}"
        body = r.content
        assert body.startswith(b"%PDF-1."), f"missing %PDF header: {body[:20]!r}"
        # trailing whitespace/newlines are allowed after %%EOF
        assert b"%%EOF" in body[-32:], f"missing %%EOF near end: {body[-64:]!r}"
        assert len(body) > 3000, f"pdf too small: {len(body)} bytes"
        reader = PdfReader(io.BytesIO(body))
        assert len(reader.pages) >= 2, f"expected >=2 pages, got {len(reader.pages)}"

    def test_attachment_disposition_when_inline_false(self):
        r = requests.get(URL, params={"inline": "false"}, timeout=30)
        assert r.status_code == 200
        disp = r.headers.get("content-disposition", "")
        assert disp.lower().startswith("attachment"), f"expected attachment, got: {disp}"

    def test_cache_control_no_store(self):
        r = requests.get(URL, timeout=30)
        cc = r.headers.get("cache-control", "")
        assert "no-store" in cc.lower(), f"expected no-store, got: {cc}"
