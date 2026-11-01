# v72h: concurrency probe — parallel signatures on different split lines must not overwrite each other.
from concurrent.futures import ThreadPoolExecutor

from bson import ObjectId

from test_v72h_consortium_split_signing import DB, _mk, _u, API, setup, pmc, esc, _bank, M1_EMAIL, _now  # noqa: F401,F811


def test_parallel_line_signing_keeps_all(pmc, esc):  # noqa: F811
    DB.registrations.insert_one({"email": M1_EMAIL, "created_at": _now(), **_bank("M1R")})
    _, tid = _mk("RACE")
    assert pmc.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "TEST"}).status_code == 200
    jobs = [(pmc, i) for i in range(3)] + [(esc, i) for i in range(3)]
    with ThreadPoolExecutor(6) as ex:
        codes = list(ex.map(lambda a: a[0].post(_u(tid, a[1], "sign"), json={}).status_code, jobs))
    assert codes == [200] * 6, codes
    lines = DB.escrow_transactions.find_one({"_id": ObjectId(tid)})["consortium_split"]["lines"]
    got = [sorted(x["signatures"]) for x in lines]
    assert all(x["status"] == "approved" for x in lines), got
