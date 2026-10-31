# Seeds an approved TEST partner (+1 supplier invite) for v67 UI testing; run with `cleanup` arg to remove.
import sys
import json
sys.path.insert(0, "/app/backend/tests")
import test_v67_partner_suppliers as t  # noqa: E402

t.RID = "uiseed"
t.SUP.update({k: f"test_sup_{k}_uiseed@example.com" for k in t.SUP})
if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    t._cleanup()
    print("cleaned")
    sys.exit(0)
t._cleanup()
t.S["admin"] = t._admin()
pa, aid = t._partner("a")
r = t._invite(pa, "one").json()
reg = t.DB.registrations.find_one({"email": t.SUP["one"]})
print(json.dumps({"partner_email": f"test_partner_a_uiseed@example.com", "password": t.PW, "aid": aid,
                  "rid": r["id"], "consent_token": reg["partner_consent_token"], "magic": reg["magic_token"]}))
