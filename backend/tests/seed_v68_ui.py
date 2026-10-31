# Seeds TEST partners A,B (+ invite awaiting consent, + approved supplier of A) for v68 UI testing; `cleanup` arg removes.
import sys
import json
sys.path.insert(0, "/app/backend/tests")
import test_v68_partner_reassign_board as t  # noqa: E402

t.RID = "ui68"
t.SUP.update({k: f"test_sup_{k}_ui68@example.com" for k in t.SUP})
t.NOTICE = "TEST-NTC-ui68"
if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    t._cleanup()
    print("cleaned")
    sys.exit(0)
t._cleanup()
t.S["admin"] = t._admin()
pa, aid = t._partner("a")
pb, bid = t._partner("b")
rid1, ctok1, magic1 = t._invite(pa, "one")
rid2, ctok2, magic2 = t._invite(pa, "two")
t.requests.post(f"{t.API}/supplier-invites/{ctok2}", json={"decision": "accept", "signer_name": "TEST Signer",
                                                          "consents": {k: True for k in t.KEYS}})
vref2 = t._approve(rid2)
print(json.dumps({"partner_email": "test_partner_a_ui68@example.com", "password": t.PW, "aid": aid, "bid": bid,
                  "rid1": rid1, "ctok1": ctok1, "magic1": magic1, "rid2": rid2, "vref2": vref2}))
