# UI setup for v61i: TEST_ live listing, 2 TEST_ pending listings, one real catalogue import for testvendor -> /tmp/v61i.json
import json, os, time, requests
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


def mk(title, **kw):
    r = v.post(f"{API}/listings", json={"title": title, "sale_modes": ["fixed"], "buy_now_price": 25, "category": "TEST_cat", **kw})
    r.raise_for_status()
    lid = r.json()["id"]
    out["listings"].append(lid)
    v.post(f"{API}/listings/{lid}/submit").raise_for_status()
    return lid


out["live"] = mk("TEST_UI_live_buyers")
a.post(f"{API}/admin/listings/{out['live']}/decision", json={"action": "approve"}).raise_for_status()
out["live_any"] = mk("TEST_UI_live_any", eligibility="any_verified")
a.post(f"{API}/admin/listings/{out['live_any']}/decision", json={"action": "approve"}).raise_for_status()
out["p1"], out["p2"] = mk("TEST_UI_pend_1"), mk("TEST_UI_pend_2")
with open("/tmp/test_catalogue.pdf", "rb") as f:
    r = v.post(f"{API}/catalogue/import", files={"file": ("TEST_catalogue.pdf", f, "application/pdf")})
r.raise_for_status()
out["import"] = r.json()["id"]
for _ in range(60):
    d = v.get(f"{API}/catalogue/import/{out['import']}").json()
    if d["status"] != "reading":
        break
    time.sleep(3)
out["import_status"], out["import_products"] = d["status"], len(d.get("products") or [])
json.dump(out, open("/tmp/v61i.json", "w"))
print(out)
