# Helper for v72d UI testing: `setup` creates a TEST-TPLC-UI draft template owned by testvendor; `cleanup` removes it and any notice approved from it.
import sys
sys.path.insert(0, "/app/backend/tests")
import test_v72d_template_criteria as T  # noqa: E402

T.NAME = "TEST-TPLC-UI"


def cleanup():
    T._cleanup()


def setup():
    cleanup()
    tv = str(T.DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
    T.DB.vendors.update_one({"_id": T.ObjectId(tv)}, {"$set": {}})
    print(T._tpl(tv))


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
