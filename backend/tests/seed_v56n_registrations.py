import os, uuid, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
for i in range(2):
    em = f"delivered+v56nui{uuid.uuid4().hex[:6]}@resend.dev"
    c = requests.post(f"{API}/registrations", json={"email": em, "company_name": f"TEST_v56n UI Reg {i}", "country": "KZ", "data_processing_consent": True}).json()
    body = {"registered_address": "1 Test St", "registration_number": "TEST123", "legal_entity_type": "LLP",
            "decl_conflict_of_interest": True, "decl_integrity": True, "decl_accuracy": True, "decl_data_consent": True,
            "decl_fee": True, "decl_notification": True, "signature_name": "T", "signature_title": "CEO", "signature_date": "2026-10-21"}
    requests.patch(f"{API}/registrations/{c['id']}?token={c['magic_token']}", json=body)
    s = requests.post(f"{API}/registrations/{c['id']}/submit?token={c['magic_token']}")
    print(c["id"], em, s.status_code)
