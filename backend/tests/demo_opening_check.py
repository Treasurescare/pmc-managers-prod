# Demo showcase: committee technical-stage bid opening via API (committee1 + committee2) — preview only
import os
import requests

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
REF = "DEMO-TND-OPEN"


def staff(email):
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/staff/auth/login", json={"email": email, "password": "Demo@Pmc2026", "active_role": "committee_member"})
    print(email, "login", r.status_code, r.json().get("active_role") if r.ok else r.text[:200])
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


for i, nm in [(1, "Priya Shah"), (2, "Tom Ellis")]:
    s = staff(f"committee{i}@demo.pmcmanagers.com")
    st = s.get(f"{BASE}/api/v1/bid-opening/{REF}").json()
    print(" i_can_approve technical:", st["stages"]["technical"]["i_can_approve"], "blockers:", st["stages"]["technical"]["blockers"])
    r = s.post(f"{BASE}/api/v1/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": nm, "consent": True})
    print(" approve", r.status_code, r.text[:300])
