# v66 UI seed: creates a submitted TEST partner (country KE) + TEST partner_registration fee rule. `python ui_partner_setup.py cleanup` removes them.
import sys
import requests
sys.path.insert(0, "/app/backend/tests")
import test_v66_partner_fee as t  # noqa: E402

EMAIL = "test_partner_ui_v66@example.com"


def cleanup():
    ids = [str(a["_id"]) for a in t.DB.agents.find({"email": {"$regex": "^test_partner_ui"}})]
    t.DB.payment_transactions.delete_many({"agent_id": {"$in": ids}})
    t.DB.agents.delete_many({"email": {"$regex": "^test_partner_ui"}})
    t.DB.emd_masters.delete_many({"name": {"$regex": "^TEST UI partner fee"}})
    t.DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:|test_partner_ui"}})


if __name__ == "__main__":
    cleanup()
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        print("cleaned"); sys.exit(0)
    ad = t._admin()
    assert t._register(EMAIL, "TEST UI Partner").status_code == 200
    _, aid = t._join_and_submit(EMAIL, "KE")
    r = ad.post(f"{t.API}/tender-pro/emd-masters", json={"name": "TEST UI partner fee KE", "kind": "partner_registration",
                "countries": ["KE"], "currency": "USD", "slabs": [{"fee_type": "fixed", "fixed_amount": 75}]})
    assert r.status_code == 200, r.text
    t.DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}})
    print("AID", aid, EMAIL, t.PW)
