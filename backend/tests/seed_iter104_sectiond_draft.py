# Seed a DRAFT registration with Section A-C filled so UI can navigate to Section D (bug #6)
import os, time, requests, json
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ts = int(time.time())
r = requests.post(f"{BASE}/api/v1/registrations", json={
    "email": f"test_secd_{ts}@example.com", "company_name": f"TEST_SECD_{ts}", "country": "IN",
    "data_processing_consent": True})
d = r.json()
p = requests.patch(f"{BASE}/api/v1/registrations/{d['id']}", params={"token": d["magic_token"]}, json={
    "registered_address": "1 Test Street, Mumbai", "registration_number": f"U{ts}",
    "legal_entity_type": "private_limited"})
print("patch", p.status_code, p.text[:200])
json.dump(d, open("/tmp/secd.json", "w"))
print(d["resume_url"])
