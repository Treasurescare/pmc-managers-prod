"""v57e — PUBLIC reverse-auction system: discovery list, anonymous state,
hash-chained events, heartbeat, SSE, atomic duplicate-price guard, dup-price
notification, bid validation and governance-gated award disclosure."""
import os
import json
import time
import hashlib
import threading
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api/v1/reverse-auctions"
LIVE_AID = "6adf14da2e789255c9a9eb27"
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"

_mc = MongoClient(os.environ["MONGO_URL"])
mdb = _mc[os.environ["DB_NAME"]]

FORBIDDEN_KEYS = {"vendor_id", "vendor_email", "company_name", "current_leader_id",
                  "email", "user_email", "closed_by", "created_by"}


def _walk_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}", k, v
            yield from _walk_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{path}[{i}]")


def _assert_no_identity(payload, extra_strings=(), allow_winner_company=False):
    for p, k, v in _walk_keys(payload):
        if k in FORBIDDEN_KEYS:
            if allow_winner_company and k == "company_name" and ".winner." in p + ".":
                continue
            raise AssertionError(f"IDENTITY LEAK key {p}={v!r}")
    raw = json.dumps(payload, default=str)
    for s in extra_strings:
        if s and s in raw:
            raise AssertionError(f"IDENTITY LEAK string {s!r} in payload")


# ---------- fixtures -------------------------------------------------

@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}",
                      "X-CSRF-Token": d["csrf_token"]})
    return s


@pytest.fixture(scope="module")
def vendors():
    """Seed 2 TEST vendors in Mongo and log in through the real API."""
    import sys
    sys.path.insert(0, "/app/backend")
    from security import hash_password
    out = []
    for n in (1, 2):
        email = f"test_ra57e_v{n}@example.com"
        mdb.vendors.update_one({"email": email}, {"$set": {
            "email": email, "company_name": f"TEST_RA57E Company {n}",
            "contact_name": f"TEST v{n}", "password_hash": hash_password("Vendor@12345"),
            "status": "active", "vendor_ref": f"TEST-RA57E-{n}", "token_generation": 0,
            "must_change_password": False}}, upsert=True)
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                   json={"email": email, "password": "Vendor@12345"})
        assert r.status_code == 200, r.text
        tok = r.json().get("token") or s.cookies.get("vendor_token")
        s.cookies.clear()
        s.headers.update({"Authorization": f"Bearer {tok}"})
        out.append((s, email, f"TEST_RA57E Company {n}"))
    yield out
    mdb.vendors.delete_many({"email": {"$regex": "^test_ra57e_v"}})
    mdb.notifications.delete_many({"user_email": {"$regex": "^test_ra57e_v"}})


@pytest.fixture(scope="module")
def created_ids():
    ids = []
    yield ids
    for aid in ids:
        mdb.reverse_auctions.delete_one({"_id": ObjectId(aid)})
        for c in ("reverse_auction_bids", "reverse_auction_participants",
                  "reverse_auction_events", "reverse_auction_viewers",
                  "reverse_auction_invitations"):
            mdb[c].delete_many({"auction_id": aid})
        mdb.bids.delete_many({"auction_id": aid})


def _new_live_auction(admin, vendors, created_ids, title="TEST_RA57E live"):
    r = admin.post(API, json={"title": title, "currency": "USD",
                              "starting_price": 100000, "floor_price": 50000,
                              "min_decrement": 1000, "duration_minutes": 30,
                              "anti_snipe_seconds": 0})
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    created_ids.append(aid)
    for s, _, _ in vendors:
        rr = s.post(f"{API}/{aid}/register")
        assert rr.status_code == 200, rr.text
    rs = admin.post(f"{API}/{aid}/start")
    assert rs.status_code == 200, rs.text
    return aid


# ---------- public discovery ----------------------------------------

class TestPublicList:
    @pytest.mark.parametrize("status", [None, "live", "upcoming", "closed", "awarded"])
    def test_list_filters_and_no_leak(self, status):
        r = requests.get(f"{API}/public/list", params={"status": status} if status else {})
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["items"], list) and d["count"] == len(d["items"])
        exp = {"live": {"live"}, "upcoming": {"draft"}, "closed": {"closed"},
               "awarded": {"closed"}}.get(status)
        for c in d["items"]:
            if exp:
                assert c["status"] in exp
            if c["award_status"] != "awarded_published":
                assert c["winner"] is None
            _assert_no_identity(c, allow_winner_company=c["award_status"] == "awarded_published")
        if status == "live":
            assert any(c["id"] == LIVE_AID for c in d["items"])


# ---------- public state / events / heartbeat / SSE ------------------

class TestPublicLiveAuction:
    def test_state_anonymous_masked(self):
        r = requests.get(f"{API}/{LIVE_AID}/state")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "live" and d["winner"] is None
        assert d["leader_alias"] is None or d["leader_alias"].startswith("Bidder ")
        for b in d["bids"]:
            assert b["alias"].startswith("Bidder ")
        parts = list(mdb.reverse_auction_participants.find({"auction_id": LIVE_AID}))
        leaks = [p.get("vendor_email") for p in parts] + [p.get("company_name") for p in parts] \
            + [p.get("vendor_id") for p in parts]
        _assert_no_identity(d, extra_strings=leaks)

    def test_state_invalid_id_404(self):
        r = requests.get(f"{API}/not-an-objectid/state")
        assert r.status_code in (400, 404, 422), f"got {r.status_code}"

    def test_state_unknown_id_404(self):
        r = requests.get(f"{API}/{ObjectId()}/state")
        assert r.status_code == 404

    def test_events_hash_chain(self):
        r = requests.get(f"{API}/{LIVE_AID}/events")
        assert r.status_code == 200
        evs = r.json()["items"]
        assert len(evs) >= 1
        prev = "GENESIS"
        for i, e in enumerate(evs):
            assert e["seq"] == i + 1
            assert e["previous_hash"] == prev
            body = {"auction_id": LIVE_AID, "seq": e["seq"], "kind": e["kind"],
                    "data": e["data"], "at": e["at"], "previous_hash": e["previous_hash"]}
            recomputed = hashlib.sha256(json.dumps(body, sort_keys=True, default=str)
                                        .encode()).hexdigest()
            assert recomputed == e["hash"], f"hash mismatch seq {e['seq']}"
            prev = e["hash"]
        _assert_no_identity(r.json())

    def test_heartbeat(self):
        vid = f"TESTv{int(time.time()*1000)}"
        r = requests.post(f"{API}/{LIVE_AID}/heartbeat", json={"viewer_id": vid})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and isinstance(d["viewer_count"], int) and d["viewer_count"] >= 1
        st = requests.get(f"{API}/{LIVE_AID}/state").json()
        assert st["viewer_count"] >= 1
        mdb.reverse_auction_viewers.delete_one({"viewer_id": vid})

    def test_heartbeat_validation(self):
        r = requests.post(f"{API}/{LIVE_AID}/heartbeat", json={"viewer_id": "x"})
        assert r.status_code == 422

    def test_sse_stream_masked(self):
        with requests.get(f"{API}/{LIVE_AID}/stream", stream=True, timeout=(10, 15)) as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            buf = ""
            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                buf += chunk
                if "\n\n" in buf:
                    break
        line = [l for l in buf.splitlines() if l.startswith("data: ")][0]
        d = json.loads(line[6:])
        assert d["id"] == LIVE_AID and d["status"] == "live"
        _assert_no_identity(d)


# ---------- bidding / duplicate / governance (own TEST auctions) -----

class TestBidding:
    def test_draft_auction_upcoming_and_bid_rejected(self, admin, vendors, created_ids):
        r = admin.post(API, json={"title": "TEST_RA57E draft", "starting_price": 1000,
                                  "floor_price": 100, "min_decrement": 10})
        assert r.status_code == 200
        aid = r.json()["id"]
        created_ids.append(aid)
        vs, _, _ = vendors[0]
        assert vs.post(f"{API}/{aid}/register").status_code == 200
        rb = vs.post(f"{API}/{aid}/bid", json={"price": 900})
        assert rb.status_code == 400 and "not live" in rb.json()["detail"].lower()
        up = requests.get(f"{API}/public/list", params={"status": "upcoming"}).json()
        assert any(c["id"] == aid for c in up["items"])

    def test_validation_floor_and_decrement(self, admin, vendors, created_ids):
        aid = _new_live_auction(admin, vendors, created_ids)
        vs, _, _ = vendors[0]
        r = vs.post(f"{API}/{aid}/bid", json={"price": 40000})
        assert r.status_code == 400 and "floor" in r.json()["detail"].lower()
        r = vs.post(f"{API}/{aid}/bid", json={"price": 99500})
        assert r.status_code == 400 and "lower" in r.json()["detail"].lower()
        r = vs.post(f"{API}/{aid}/bid", json={"price": 99000})
        assert r.status_code == 200
        _assert_no_identity(r.json(), extra_strings=[vendors[0][1], vendors[0][2]])

    def test_atomic_duplicate_price_and_notification(self, admin, vendors, created_ids):
        aid = _new_live_auction(admin, vendors, created_ids, "TEST_RA57E dup")
        seen = []
        for rnd in range(8):
            price = 95000 - rnd * 1000
            results = {}
            barrier = threading.Barrier(2)

            def go(i):
                s, _, _ = vendors[i]
                barrier.wait()
                results[i] = s.post(f"{API}/{aid}/bid", json={"price": price})

            ts = [threading.Thread(target=go, args=(i,)) for i in (0, 1)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            codes = sorted(r.status_code for r in results.values())
            seen.append(codes)
            # exactly ONE winner per price, never two
            assert codes.count(200) == 1, f"round {rnd} codes={codes}"
            assert codes[1] in (400, 409)
            assert mdb.reverse_auction_bids.count_documents({"auction_id": aid, "price": price}) == 1
            if codes == [200, 409]:
                loser = [i for i, r in results.items() if r.status_code == 409][0]
                assert "already" in results[loser].json()["detail"].lower()
                n = mdb.notifications.find_one({"user_email": vendors[loser][1], "related_id": aid})
                assert n is not None and "already taken" in n["subject"]
        print("concurrent rounds:", seen)
        # Deterministic 409 through the real bid path: reserve a price row as a
        # competitor whose insert landed but auction row not yet updated.
        cur = requests.get(f"{API}/{aid}/state").json()["current_price"]
        p = cur - 5000
        mdb.reverse_auction_bids.insert_one({"auction_id": aid, "vendor_id": "TEST_competitor",
                                             "price": float(p), "is_auto": False, "at": "2026-01-01T00:00:00+00:00"})
        r = vendors[0][0].post(f"{API}/{aid}/bid", json={"price": p})
        assert r.status_code == 409, r.text
        n = mdb.notifications.find_one({"user_email": vendors[0][1], "related_id": aid})
        assert n is not None and "already taken" in n["subject"] and n["read"] is False
        # loser can rebid a different price
        r = vendors[0][0].post(f"{API}/{aid}/bid", json={"price": p - 1000})
        assert r.status_code == 200

    def test_sequential_duplicate_price_409(self, admin, vendors, created_ids):
        aid = created_ids[-1]
        # price 95000 already used but is above current - decrement → 400 first
        r = vendors[1][0].post(f"{API}/{aid}/bid", json={"price": 95000})
        assert r.status_code == 400

    def test_governance_gated_award(self, admin, vendors, created_ids):
        aid = _new_live_auction(admin, vendors, created_ids, "TEST_RA57E award")
        assert vendors[0][0].post(f"{API}/{aid}/bid", json={"price": 90000}).status_code == 200
        assert vendors[1][0].post(f"{API}/{aid}/bid", json={"price": 85000}).status_code == 200
        rc = admin.post(f"{API}/{aid}/close")
        assert rc.status_code == 200, rc.text
        st = requests.get(f"{API}/{aid}/state").json()
        assert st["status"] == "closed" and st["winner"] is None
        assert st["award_status"] == "closed_unawarded"
        _assert_no_identity(st, extra_strings=[vendors[1][2], vendors[1][1]])
        # bid after close
        rb = vendors[0][0].post(f"{API}/{aid}/bid", json={"price": 80000})
        assert rb.status_code == 400
        # SSE on closed auction terminates quickly
        t0 = time.time()
        with requests.get(f"{API}/{aid}/stream", stream=True, timeout=(10, 10)) as r:
            body = "".join(r.iter_content(chunk_size=None, decode_unicode=True))
        assert time.time() - t0 < 8 and '"closed"' in body
        # award → in_approvals
        ra = admin.post(f"{API}/{aid}/award")
        assert ra.status_code == 200, ra.text
        bid_id = ra.json()["bid_id"]
        st = requests.get(f"{API}/{aid}/state").json()
        assert st["award_status"] == "in_approvals" and st["winner"] is None
        _assert_no_identity(st, extra_strings=[vendors[1][2]])
        cl = requests.get(f"{API}/public/list", params={"status": "closed"}).json()
        card = [c for c in cl["items"] if c["id"] == aid][0]
        assert card["winner"] is None and card["award_status"] == "in_approvals"
        aw = requests.get(f"{API}/public/list", params={"status": "awarded"}).json()
        assert not any(c["id"] == aid for c in aw["items"])
        evs = requests.get(f"{API}/{aid}/events").json()
        _assert_no_identity(evs, extra_strings=[vendors[1][2], vendors[1][1]])
        # governance completes → published
        mdb.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {"status": "awarded"}})
        st = requests.get(f"{API}/{aid}/state").json()
        assert st["award_status"] == "awarded_published" and st["award_published"] is True
        assert st["winner"]["company_name"] == vendors[1][2]
        assert st["winner"]["winning_price"] == 85000
        aw = requests.get(f"{API}/public/list", params={"status": "awarded"}).json()
        assert any(c["id"] == aid and c["winner"]["company_name"] == vendors[1][2] for c in aw["items"])
        cl = requests.get(f"{API}/public/list", params={"status": "closed"}).json()
        assert not any(c["id"] == aid for c in cl["items"])


class TestConcurrentDifferentPrices:
    """Race: two simultaneous bids at DIFFERENT prices — current_price must end
    at the LOWEST accepted bid (leader must be the lowest bidder)."""
    def test_current_price_is_min_after_race(self, admin, vendors, created_ids):
        aid = _new_live_auction(admin, vendors, created_ids, "TEST_RA57E race")
        bad = []
        cur = 100000
        for rnd in range(8):
            prices = {0: cur - 1000, 1: cur - 2000} if rnd % 2 else {0: cur - 2000, 1: cur - 1000}
            barrier = threading.Barrier(2)
            res = {}

            def go(i):
                barrier.wait()
                res[i] = vendors[i][0].post(f"{API}/{aid}/bid", json={"price": prices[i]})

            ts = [threading.Thread(target=go, args=(i,)) for i in (0, 1)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            st = requests.get(f"{API}/{aid}/state").json()
            bids_min = min(b["price"] for b in st["bids"])
            if st["current_price"] != bids_min:
                bad.append((rnd, st["current_price"], bids_min, [r.status_code for r in res.values()]))
            cur = int(min(st["current_price"], bids_min))
        assert not bad, f"current_price not lowest accepted bid after race: {bad}"


def test_notify_duplicate_price_invokes_email(monkeypatch):
    """Unit: _notify_duplicate_price inserts notification AND calls send_email."""
    import sys, asyncio
    sys.path.insert(0, "/app/backend")
    import routers.auction_live as al
    calls = []

    async def fake_send(to, subj, html, *a, **k):
        calls.append((to, subj))
        return True

    monkeypatch.setattr(al, "send_email", fake_send)
    a = {"_id": ObjectId(), "currency": "USD", "title": "TEST_RA57E unit"}
    v = {"email": "test_ra57e_unit@example.com", "vendor_ref": "TEST-U"}

    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        al.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        await al._notify_duplicate_price(a, v, 12345.0)
    asyncio.run(run())
    assert calls and calls[0][0] == v["email"] and "already taken" in calls[0][1]
    n = mdb.notifications.find_one({"user_email": v["email"], "related_id": str(a["_id"])})
    assert n is not None
    mdb.notifications.delete_many({"user_email": v["email"]})
