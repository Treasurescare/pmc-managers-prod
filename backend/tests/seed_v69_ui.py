# Seed helper for v69 UI tests: `python seed_v69_ui.py seed` / `python seed_v69_ui.py clean <RID>`
import sys
sys.path.insert(0, "/app/backend/tests")
import test_v69_partner_statements_login as t  # noqa: E402

if sys.argv[1] == "seed":
    t.S["admin"] = t._admin()
    t.test_setup()
    print("RID", t.RID, t.S["email_a"], t.S["email_b"], t.S["aid_a"], t.S["aid_c"], t.S["code_a"])
else:
    t.RID = sys.argv[2]
    t._cleanup()
    print("cleaned", t.RID)
