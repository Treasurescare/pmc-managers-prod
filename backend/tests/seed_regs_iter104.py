# Seed 2 SUBMITTED registrations (complete + incomplete) for UI tests of bugs #15/#55
import os, time, requests, json
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ts = int(time.time())
out = {}
decl = {k: True for k in ["decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
                         "decl_data_consent", "decl_fee", "decl_notification"]}
sig = {"signature_name": "Test Signer", "signature_title": "Director", "signature_date": "2026-01-15"}
for kind in ["complete", "incomplete"]:
    email = f"test_reg_{kind}_{ts}@example.com"
    r = requests.post(f"{BASE}/api/v1/registrations", json={
        "email": email, "company_name": f"TEST_REG_{kind.upper()}_{ts}", "country": "IN",
        "data_processing_consent": True})
    d = r.json(); rid, tok = d["id"], d["magic_token"]
    patch = {**decl, **sig}
    if kind == "complete":
        patch.update({"registered_address": "1 Test Street, Mumbai", "registration_number": f"U{ts}",
                      "legal_entity_type": "private_limited"})
    p = requests.patch(f"{BASE}/api/v1/registrations/{rid}", params={"token": tok}, json=patch)
    if p.status_code != 200:
        print(kind, "patch", p.status_code, p.text[:400])
    s = requests.post(f"{BASE}/api/v1/registrations/{rid}/submit", params={"token": tok})
    print(kind, rid, "submit", s.status_code, s.text[:200])
    out[kind] = rid
json.dump(out, open("/tmp/regs.json", "w"))
print(out)
