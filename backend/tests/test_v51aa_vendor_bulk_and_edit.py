"""v51aa — Bulk CSV template, structured 409, admin full-vendor edit endpoints."""
import os, time, uuid, pytest, requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    csrf = j.get("csrf_token") or j.get("csrf")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


EXPECTED_FIELDS = [
    "company_name","trade_name","registered_address","mailing_address","country",
    "registration_number","incorporation_date","tax_id","legal_entity_type","website",
    "employees_count","contact_name","contact_title","contact_office_phone","contact_mobile",
    "contact_email","signatory_name","signatory_title","signatory_contact",
    "bank_name","bank_branch","bank_account_number","bank_swift","bank_address",
    "turnover_year1","turnover_year2","turnover_year3","turnover_currency",
    "primary_sector","business_description","operating_regions","business_categories",
    "iso_certifications","licenses_permits","insurance_details","litigation_history",
    "kz_licenses","decl_conflict_of_interest","decl_integrity","decl_accuracy",
    "decl_data_consent","decl_fee","decl_notification",
    "signature_name","signature_title","signature_date",
]


# ---- Bulk CSV template ----
def test_bulk_template_csv_headers(admin):
    r = admin.get(f"{BASE}/api/v1/vendors/invite-bulk/template", timeout=20)
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert "pmc_vendor_bulk_template.csv" in r.headers.get("content-disposition", "")
    header = r.text.splitlines()[0].split(",")
    assert header[0] == "email"
    missing = [f for f in EXPECTED_FIELDS if f not in header]
    assert not missing, f"template missing columns: {missing}"


# ---- Bulk invite with full A-E columns ----
def test_bulk_invite_full_columns(admin):
    email = f"test_v51aa_{uuid.uuid4().hex[:8]}@example.com"
    header = ["email", "company_name", "employees_count", "turnover_year1",
              "operating_regions", "decl_integrity"]
    row = [email, "TEST_BulkCo", "25", "500000", "KZ|UZ", "true"]
    csv_text = ",".join(header) + "\n" + ",".join(row) + "\n"
    r = admin.post(f"{BASE}/api/v1/vendors/invite-bulk",
                   json={"csv_text": csv_text}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["invited"] == 1
    vref = j["results"][0]["vendor_ref"]
    # Verify profile coercions via admin full fetch
    r2 = admin.get(f"{BASE}/api/v1/vendors/admin/{vref}/full", timeout=20)
    assert r2.status_code == 200, r2.text
    prof = r2.json().get("profile") or {}
    assert prof.get("company_name") == "TEST_BulkCo"
    assert prof.get("employees_count") == 25
    assert prof.get("turnover_year1") == 500000.0
    assert prof.get("operating_regions") == ["KZ", "UZ"]
    assert prof.get("decl_integrity") is True


# ---- Structured 409 on already-active vendor ----
def test_invite_already_active_returns_structured_409(admin):
    # Pick any already-active vendor from the list; fall back to creating one.
    r = admin.get(f"{BASE}/api/v1/vendors?is_active=true&limit=5", timeout=20)
    active_email = None
    active_ref = None
    if r.status_code == 200:
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", [])
        for v in items:
            if v.get("is_active"):
                active_email = v.get("email"); active_ref = v.get("vendor_ref"); break
    if not active_email:
        # Create + force-activate a vendor
        email = f"test_v51aa_act_{uuid.uuid4().hex[:8]}@example.com"
        r = admin.post(f"{BASE}/api/v1/vendors/invite",
                       json={"email": email, "company_name": "TEST_ActiveCo"}, timeout=20)
        assert r.status_code == 200, r.text
        vref = r.json()["vendor_ref"]
        r = admin.post(f"{BASE}/api/v1/vendors/{vref}/activate",
                       json={"mode": "set_password", "password": "Pwd@12345"}, timeout=20)
        assert r.status_code == 200, r.text
        active_email, active_ref = email, vref

    r = admin.post(f"{BASE}/api/v1/vendors/invite",
                   json={"email": active_email, "company_name": "Dupe"}, timeout=20)
    assert r.status_code == 409, r.text
    detail = r.json().get("detail")
    assert isinstance(detail, dict), f"detail must be object, got {detail!r}"
    assert detail.get("code") == "vendor_already_active"
    assert detail.get("vendor_ref") == active_ref
    assert detail.get("email") == active_email
    assert "message" in detail


# ---- Admin full GET / PATCH ----
def test_admin_full_get_and_patch(admin):
    email = f"test_v51aa_edit_{uuid.uuid4().hex[:8]}@example.com"
    r = admin.post(f"{BASE}/api/v1/vendors/invite",
                   json={"email": email, "company_name": "TEST_EditCo",
                         "prefilled_registration": {"bank_name": "InitialBank",
                                                    "signatory_name": "Keep Me"}},
                   timeout=20)
    assert r.status_code == 200, r.text
    vref = r.json()["vendor_ref"]

    r = admin.get(f"{BASE}/api/v1/vendors/admin/{vref}/full", timeout=20)
    assert r.status_code == 200
    assert isinstance(r.json().get("profile"), dict)

    r = admin.get(f"{BASE}/api/v1/vendors/admin/DOES-NOT-EXIST-123/full", timeout=20)
    assert r.status_code == 404

    r = admin.patch(f"{BASE}/api/v1/vendors/admin/{vref}/full",
                    json={"profile": {"company_name": "Updated", "bank_name": "Halyk"}},
                    timeout=20)
    assert r.status_code == 200, r.text
    prof = r.json().get("profile") or {}
    assert prof.get("company_name") == "Updated"
    assert prof.get("bank_name") == "Halyk"
    # Merge-patch must preserve untouched key
    assert prof.get("signatory_name") == "Keep Me", f"merge lost key: {prof}"
    assert r.json().get("profile_updated_at")
    assert r.json().get("profile_updated_by")
