# UI setup for v61j: TEST_ live listings (buyers-only all modes, any_verified) + 4 TEST_ pending -> /tmp/v61j.json
import json, os, requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
B = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{B}/api/v1/market"


def login(path, email, pw):
    s = requests.Session()
    r = s.post(f"{B}/api/v1/{path}/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


v = login("vendor", "testvendor@pmcmanagers.com", "Vendor@12345")
a = login("admin", "adminsupport@pmcmanagers.com", "Admin@12345")
out = {"listings": []}
closes = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()


def mk(title, approve=False, **kw):
    body = {"title": title, "sale_modes": ["fixed"], "buy_now_price": 25, "category": "TEST_cat", **kw}
    r = v.post(f"{API}/listings", json=body)
    r.raise_for_status()
    lid = r.json()["id"]
    out["listings"].append(lid)
    v.post(f"{API}/listings/{lid}/submit").raise_for_status()
    if approve:
        a.post(f"{API}/admin/listings/{lid}/decision", json={"action": "approve"}).raise_for_status()
    return lid


allm = dict(sale_modes=["auction", "best_offer", "fixed"], start_price=5, closes_at=closes)
out["live"] = mk("TEST_J_live_buyers", True, **allm)
out["live_any"] = mk("TEST_J_live_any", True, eligibility="any_verified", **allm)
out["pend"] = [mk(f"TEST_J_pend_{i}") for i in range(4)]
json.dump(out, open("/tmp/v61j.json", "w"))
print(out)
