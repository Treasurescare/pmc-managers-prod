"""v52bx — session cross-contamination + vendor reverse-auction visibility."""
import os
import re
import pytest
import requests
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PWD = "Vendor@12345"


def _parse_set_cookie_names_and_maxage(resp):
    """Return list of (name, max_age) tuples from response Set-Cookie headers."""
    raw = resp.raw.headers.getlist("Set-Cookie") if hasattr(resp.raw.headers, "getlist") else resp.headers.get("Set-Cookie", "").split(",")
    out = []
    for ck in raw:
        m = re.match(r"\s*([^=]+)=([^;]*)", ck)
        if not m:
            continue
        name = m.group(1).strip()
        val = m.group(2).strip()
        ma = re.search(r"[Mm]ax-[Aa]ge=(\-?\d+)", ck)
        out.append((name, val, int(ma.group(1)) if ma else None, ck))
    return out


# ---------- Session cross-contamination (#34) ----------

class TestSessionCrossContamination:
    def test_vendor_then_admin_kills_vendor_cookie(self):
        s = requests.Session()
        # vendor login
        r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                   json={"email": VENDOR_EMAIL, "password": VENDOR_PWD})
        assert r.status_code == 200, f"vendor login failed: {r.text}"
        assert "vendor_token" in s.cookies, "vendor_token cookie not set"

        # confirm vendor /me OK
        me = s.get(f"{BASE_URL}/api/v1/vendor/auth/me")
        assert me.status_code == 200

        # admin login in SAME session (same cookie jar)
        r2 = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
        assert r2.status_code == 200, f"admin login failed: {r2.text}"
        cookies = _parse_set_cookie_names_and_maxage(r2)
        names = [c[0] for c in cookies]
        print("admin-login Set-Cookie:", cookies)
        assert "access_token" in names, "admin login should set access_token"
        # vendor_token deletion header must be present (Max-Age=0 or empty value)
        vendor_del = [c for c in cookies if c[0] == "vendor_token"]
        assert vendor_del, "admin login did not send vendor_token clearing cookie"
        name, val, ma, raw = vendor_del[0]
        assert val == "" or ma == 0, f"vendor_token not cleared properly: {raw}"

        # vendor /me should now 401
        me2 = s.get(f"{BASE_URL}/api/v1/vendor/auth/me")
        assert me2.status_code == 401, f"old vendor session still valid: {me2.status_code}"

        # admin /me should be 200
        am = s.get(f"{BASE_URL}/api/v1/admin/auth/me")
        assert am.status_code == 200, f"admin me failed: {am.status_code} {am.text}"

    def test_admin_then_vendor_kills_access_cookie(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
        assert r.status_code == 200
        assert "access_token" in s.cookies

        r2 = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                    json={"email": VENDOR_EMAIL, "password": VENDOR_PWD})
        assert r2.status_code == 200
        cookies = _parse_set_cookie_names_and_maxage(r2)
        names = [c[0] for c in cookies]
        print("vendor-login Set-Cookie:", cookies)
        assert "vendor_token" in names
        access_del = [c for c in cookies if c[0] == "access_token"]
        assert access_del, "vendor login did not send access_token clearing cookie"
        name, val, ma, raw = access_del[0]
        assert val == "" or ma == 0, f"access_token not cleared properly: {raw}"

        am = s.get(f"{BASE_URL}/api/v1/admin/auth/me")
        assert am.status_code == 401, f"old admin session still valid: {am.status_code}"
        vm = s.get(f"{BASE_URL}/api/v1/vendor/auth/me")
        assert vm.status_code == 200


# ---------- Vendor reverse-auction visibility ----------

class TestReverseAuctionsMine:
    def test_unauth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/v1/reverse-auctions/mine")
        assert r.status_code == 401

    def test_vendor_mine_empty_default(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                   json={"email": VENDOR_EMAIL, "password": VENDOR_PWD})
        assert r.status_code == 200
        mine = s.get(f"{BASE_URL}/api/v1/reverse-auctions/mine")
        assert mine.status_code == 200, mine.text
        body = mine.json()
        assert "items" in body and "count" in body
        assert isinstance(body["items"], list)
        print(f"default mine: count={body['count']}")

    @pytest.mark.asyncio
    async def test_vendor_mine_bid_and_invite(self):
        # Insert fixtures directly in Mongo via backend's db module
        import sys
        sys.path.insert(0, "/app/backend")
        from db import db  # motor async client

        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                   json={"email": VENDOR_EMAIL, "password": VENDOR_PWD})
        assert r.status_code == 200
        vendor_me = s.get(f"{BASE_URL}/api/v1/vendor/auth/me").json()
        vendor_id = vendor_me["id"]
        vendor_email = vendor_me["email"].lower()

        # Pick an existing bid of this vendor to get a notice_ref
        bid = await db.bids.find_one({"vendor_id": vendor_id, "notice_ref": {"$exists": True, "$ne": None}})
        notice_ref = (bid or {}).get("notice_ref") or "TEST_NOTICE_V52BX"
        # If no bid, create a temporary bid row
        temp_bid_id = None
        if not bid:
            res = await db.bids.insert_one({
                "vendor_id": vendor_id, "notice_ref": notice_ref,
                "_test_v52bx": True,
            })
            temp_bid_id = res.inserted_id

        # Insert reverse auction with matching notice_ref
        ra_res = await db.reverse_auctions.insert_one({
            "notice_ref": notice_ref,
            "title": "TEST_V52BX RA by bid",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00Z",
            "_test_v52bx": True,
        })
        ra_id = ra_res.inserted_id

        # Insert a second RA + invitation for this vendor
        ra2_res = await db.reverse_auctions.insert_one({
            "notice_ref": "TEST_V52BX_UNRELATED",
            "title": "TEST_V52BX RA by invite",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00Z",
            "_test_v52bx": True,
        })
        ra2_id = ra2_res.inserted_id
        inv_res = await db.reverse_auction_invitations.insert_one({
            "auction_id": str(ra2_id),
            "email": vendor_email,
            "_test_v52bx": True,
        })

        try:
            mine = s.get(f"{BASE_URL}/api/v1/reverse-auctions/mine")
            assert mine.status_code == 200
            items = mine.json()["items"]
            ids = {it["id"]: it for it in items}
            print(f"mine ids: {list(ids.keys())}")
            assert str(ra_id) in ids, "RA tied to bid notice_ref not returned"
            assert ids[str(ra_id)]["why"] == "You bid on this tender"
            assert str(ra2_id) in ids, "RA via invite not returned"
            assert ids[str(ra2_id)]["why"] == "You were invited by PMC"
        finally:
            await db.reverse_auctions.delete_one({"_id": ra_id})
            await db.reverse_auctions.delete_one({"_id": ra2_id})
            await db.reverse_auction_invitations.delete_one({"_id": inv_res.inserted_id})
            if temp_bid_id:
                await db.bids.delete_one({"_id": temp_bid_id})
