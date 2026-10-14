"""v52cz rev2 — regression: the "Download blank form" endpoint must now
ALWAYS auto-generate a PDF from the live schema. The old flow served
whatever had been uploaded to `vendor_templates` — which recently leaked
a resume DOCX. These tests pin the new behaviour so a stray admin upload
can never surface again."""
from __future__ import annotations
import io
import os
import requests
from pypdf import PdfReader


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def test_blank_form_download_is_always_a_valid_pdf():
    r = requests.get(f"{API}/vendors/registration-template?inline=false", timeout=15)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type") == "application/pdf", r.headers
    # Canonical, auditable filename — not whatever a stray admin uploaded.
    cd = r.headers.get("content-disposition", "")
    assert 'filename="PMC-Vendor-Registration-Form.pdf"' in cd, cd
    assert r.content[:5] == b"%PDF-", "Response is not a valid PDF"
    # Must contain all five section headers (A..E) so form changes stay in sync.
    body_lower = _extract_pdf_text(r.content).lower()
    for marker in ("identity", "contact", "banking", "business profile",
                   "documents & declarations"):
        assert marker in body_lower, f"Missing section marker: {marker!r}"


def test_blank_form_meta_reports_canonical_filename():
    r = requests.get(f"{API}/vendors/registration-template/meta", timeout=10)
    assert r.status_code == 200, r.text
    meta = r.json()
    assert meta.get("available") is True
    assert meta.get("file_name") == "PMC-Vendor-Registration-Form.pdf"


def test_blank_form_contains_schema_field_labels():
    """New fields added to RegistrationUpdateIn should flow through the PDF."""
    r = requests.get(f"{API}/vendors/registration-template?inline=true", timeout=15)
    assert r.status_code == 200
    body = _extract_pdf_text(r.content)
    # Pick a handful of fields from each section to prove schema coverage.
    for marker in ("Legal Name", "Primary Contact",
                   "Bank Account Number", "Primary Sector",
                   "Incorporation Certificate"):
        assert marker in body, f"Missing schema label: {marker!r}"
