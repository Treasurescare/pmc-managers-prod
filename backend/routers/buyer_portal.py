"""Buyer portal: free self-registration, profile (masters-backed), dashboard of bids/orders/payments,
in-app notifications, and PMC-approved team invites. Buyers are admin_users with role "buyer" whose
tenant (source buyer_application) is created when PMC approves them."""
import re
from datetime import timedelta
from html import escape as E
from typing import Literal, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from notify import notify_role, notify_user, vendor_confirm
from routers.growth import _now, _send_buyer_signin, approve_buyer_app, pmc_staff
from security import current_admin, hash_password, require_csrf, verify_password

router = APIRouter(prefix="/api/v1/buyer", tags=["buyer-portal"])
PHONE = r"^[0-9][0-9 \-]{5,18}$"


def _out(d: dict) -> dict:
    return BaseDocument.out(d)


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=PHONE)
    country_code: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=1, max_length=120)
    state_code: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=300)
    zip: Optional[str] = Field(default=None, max_length=20)
    org_name: Optional[str] = Field(default=None, max_length=160)


class RegisterIn(ProfileIn):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


async def _profile(p: ProfileIn) -> dict:
    """Country / city must come from the masters; phone code is taken from the country master."""
    cc = p.country_code.upper()
    c = await db.masters_countries.find_one({"code": cc, "is_active": True})
    if not c:
        raise HTTPException(status_code=422, detail="Please choose a country from the list")
    q = {"country_code": cc, "name": p.city, "is_active": True, **({"state_code": p.state_code} if p.state_code else {})}
    city = await db.masters_cities.find_one(q)
    if not city:
        raise HTTPException(status_code=422, detail="Please choose a city from the list")
    zipc = (p.zip or "").strip()
    if zipc and c.get("postal_code_regex") and not re.fullmatch(c["postal_code_regex"], zipc):
        raise HTTPException(status_code=422, detail=f"ZIP / postal code format for {c['name']}: {c.get('postal_code_format') or 'see country'}")
    return {"name": p.name.strip(), "phone": re.sub(r"[ \-]", "", p.phone), "phone_code": c.get("phone_code"),
            "country_code": cc, "country": c["name"], "state_code": p.state_code or city.get("state_code"),
            "state_name": city.get("state_name"), "city": city["name"], "address": (p.address or "").strip() or None,
            "zip": zipc or None, "org_name": (p.org_name or "").strip() or None}


async def current_buyer(request: Request) -> dict:
    a = await current_admin(request)
    if a.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Buyer sign-in required")
    u = await db.admin_users.find_one({"_id": ObjectId(a["id"])})
    if not u or not u.get("is_active", True):
        raise HTTPException(status_code=403, detail="This buyer account is disabled")
    t = await db.tenants.find_one({"code": u.get("tenant_id"), "source": "buyer_application"})
    return {**a, "user": u, "tenant": t, "verified": bool(t and t.get("is_active", True))}


async def buyer_write(request: Request, b=Depends(current_buyer)) -> dict:
    await require_csrf(request)
    return b


def _me(b: dict) -> dict:
    u, t = b["user"], b["tenant"]
    return {"id": b["id"], "email": u["email"], "name": u.get("name"), "avatar_data_url": u.get("avatar_data_url"),
            "profile": u.get("buyer_profile") or {}, "verified": b["verified"], "is_org_admin": bool(u.get("is_org_admin")),
            "org": {"code": t["code"], "name": t["name"]} if t else None,
            "status": "verified" if b["verified"] else "pending_approval"}


# ---------- public: register + email confirmation ----------
def _verify_token(uid: str, email: str) -> str:
    return jwt.encode({"sub": uid, "email": email, "type": "buyer_verify", "exp": _now() + timedelta(days=3)},
                      config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


@router.post("/register")
async def register(body: RegisterIn, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[-1].strip()
    if await db.buyer_applications.count_documents({"ip": ip, "created_at": {"$gte": (_now() - timedelta(hours=1)).isoformat()}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many registrations. Please try again later.")
    email = body.email.lower()
    if await db.admin_users.find_one({"email": email}) or await db.vendors.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="This email already has a PMC account. Sign in, or use Forgot password.")
    prof = await _profile(body)
    app = {"org_name": prof["org_name"] or prof["name"], "org_type": "private" if prof["org_name"] else "other", "country": prof["country_code"],
           "contact_name": prof["name"], "email": email, "phone": f"{prof['phone_code'] or ''} {prof['phone']}".strip(),
           "status": "pending", "source": "self_register", "email_verified": False, "ip": ip, "created_at": now_iso(), "profile": prof}
    r = await db.buyer_applications.insert_one(app)
    u = await db.admin_users.insert_one({
        "email": email, "name": prof["name"], "password_hash": hash_password(body.password), "roles": ["buyer"], "role": "buyer",
        "account_type": "buyer", "tenant_id": f"PENDING-{r.inserted_id}", "is_active": True, "email_verified": False,
        "is_org_admin": True, "buyer_profile": prof, "source": "self_register", "created_at": now_iso()})
    await db.buyer_applications.update_one({"_id": r.inserted_id}, {"$set": {"user_id": str(u.inserted_id)}})
    url = f"{config.FRONTEND_URL.rstrip('/')}/buyers/verify-email?token={_verify_token(str(u.inserted_id), email)}"
    await vendor_confirm(email, "Confirm your email — PMC Managers buyer account",
                         f"<p>Hello {E(prof['name'])},</p><p>Thanks for registering as a buyer. Please confirm your email address "
                         "(the link works for 3 days). After that, PMC verifies your account and you can bid and buy.</p>", "Confirm my email", url)
    return {"ok": True}


class TokenIn(BaseModel):
    token: str = Field(max_length=2000)


@router.post("/verify-email")
async def verify_email(body: TokenIn):
    try:
        d = jwt.decode(body.token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="This confirmation link is invalid or has expired")
    if d.get("type") != "buyer_verify" or not ObjectId.is_valid(d.get("sub", "")):
        raise HTTPException(status_code=400, detail="This confirmation link is invalid or has expired")
    u = await db.admin_users.find_one({"_id": ObjectId(d["sub"]), "email": d["email"]})
    if not u:
        raise HTTPException(status_code=400, detail="This confirmation link is invalid or has expired")
    if not u.get("email_verified"):
        await db.admin_users.update_one({"_id": u["_id"]}, {"$set": {"email_verified": True}})
        a = await db.buyer_applications.find_one_and_update({"user_id": str(u["_id"])}, {"$set": {"email_verified": True}})
        if a:
            await notify_role("admin", f"New buyer registration — {a['org_name']}",
                              f"<p>{E(a['contact_name'])} &lt;{E(a['email'])}&gt; ({a['country']}) registered as a buyer and confirmed their email.</p>"
                              "<p>Review in Admin → Growth → Buyer applications.</p>", "buyer_application", str(a["_id"]))
    return {"ok": True, "email": u["email"]}


# ---------- signed-in buyer ----------
@router.get("/me")
async def me(b=Depends(current_buyer)):
    return _me(b)


@router.put("/me")
async def update_me(body: ProfileIn, b=Depends(buyer_write)):
    prof = await _profile(body)
    await db.admin_users.update_one({"_id": b["user"]["_id"]}, {"$set": {"name": prof["name"], "buyer_profile": prof}})
    return _me(await current_buyer_fresh(b))


async def current_buyer_fresh(b: dict) -> dict:
    u = await db.admin_users.find_one({"_id": b["user"]["_id"]})
    return {**b, "user": u}


class AvatarIn(BaseModel):
    data_url: str = Field(max_length=560_000, pattern=r"^data:image/(png|jpe?g|webp);base64,")


@router.post("/me/avatar")
async def avatar(body: AvatarIn, b=Depends(buyer_write)):
    await db.admin_users.update_one({"_id": b["user"]["_id"]}, {"$set": {"avatar_data_url": body.data_url}})
    return {"ok": True}


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


@router.post("/me/password")
async def change_password(body: PasswordIn, b=Depends(buyer_write)):
    if not verify_password(body.current_password, b["user"].get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Your current password is not correct")
    await db.admin_users.update_one({"_id": b["user"]["_id"]}, {"$set": {"password_hash": hash_password(body.new_password),
                                                                         "must_change_password": False, "password_changed_at": now_iso()}})
    await audit_log("buyer.password_changed", {"id": b["id"], "email": b["email"]}, "admin_user", b["id"], {})
    return {"ok": True}


def _ids(x: dict) -> dict:
    o = _out(x)
    o["listing_id"] = str(x.get("listing_id"))
    return o


@router.get("/dashboard")
async def dashboard(b=Depends(current_buyer)):
    bids = await db.mkt_bids.find({"bidder.id": b["id"]}).sort("created_at", -1).to_list(300)
    lids = list({x["listing_id"] for x in bids})
    listings = {x["_id"]: x async for x in db.mkt_listings.find({"_id": {"$in": lids}}, {"title": 1, "status": 1, "currency": 1, "closes_at": 1})}
    tops = {x["_id"]: x["top"] async for x in db.mkt_bids.aggregate([
        {"$match": {"listing_id": {"$in": lids}, "kind": "bid"}}, {"$group": {"_id": "$listing_id", "top": {"$max": "$amount"}}}])}
    orders = await db.mkt_orders.find({"buyer.id": b["id"]}).sort("created_at", -1).to_list(300)
    won = {o["listing_id"] for o in orders}
    rows = []
    for x in bids:
        lst = listings.get(x["listing_id"]) or {}
        if x["kind"] == "offer":
            st = x.get("status", "open")
        elif x["listing_id"] in won:
            st = "won"
        elif lst.get("status") == "live":
            st = "leading" if tops.get(x["listing_id"]) == x["amount"] else "outbid"
        else:
            st = "lost"
        rows.append({**_ids(x), "title": lst.get("title"), "currency": lst.get("currency"), "closes_at": lst.get("closes_at"),
                     "listing_status": lst.get("status"), "my_status": st, "top_bid": tops.get(x["listing_id"])})
    out_orders = [_ids(o) for o in orders]
    for o in out_orders:
        for k in ("pmc_fee", "fee_rule", "seller_net", "payout_status", "payout_reference", "payout_by", "session_id"):
            o.pop(k, None)
    payments = [o for o in out_orders if o.get("paid_at")]
    refunds = [o for o in out_orders if o.get("refund_status")]
    unread = await db.notifications.count_documents({"user_id": b["id"], "read": False})
    return {"me": _me(b), "bids": rows, "orders": out_orders, "payments": payments, "refunds": refunds, "unread": unread,
            "counts": {"active_bids": sum(r["my_status"] in ("leading", "outbid", "open") for r in rows),
                       "to_pay": sum(o["status"] == "awaiting_payment" for o in out_orders),
                       "in_delivery": sum(o["status"] == "paid" and o.get("delivery_status") != "received" for o in out_orders),
                       "won": sum(r["my_status"] == "won" for r in rows) + sum(o["via"] == "fixed" for o in out_orders)}}


@router.post("/orders/{oid}/received")
async def mark_received(oid: str, b=Depends(buyer_write)):
    o = await db.mkt_orders.find_one({"_id": ObjectId(oid), "buyer.id": b["id"]}) if ObjectId.is_valid(oid) else None
    if not o or o["status"] != "paid":
        raise HTTPException(status_code=404, detail="Order not found")
    await db.mkt_orders.update_one({"_id": o["_id"]}, {"$set": {"delivery_status": "received", "received_at": now_iso()}})
    return {"ok": True}


# ---------- notifications ----------
@router.get("/notifications")
async def notifications(b=Depends(current_buyer)):
    items = [_out(n) async for n in db.notifications.find({"user_id": b["id"]}).sort("created_at", -1).limit(100)]
    return {"items": items, "unread": sum(not n.get("read") for n in items)}


@router.post("/notifications/{nid}/read")
async def read_one(nid: str, b=Depends(buyer_write)):
    if ObjectId.is_valid(nid):
        await db.notifications.update_one({"_id": ObjectId(nid), "user_id": b["id"]}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def read_all(b=Depends(buyer_write)):
    await db.notifications.update_many({"user_id": b["id"], "read": False}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"ok": True}


# ---------- team: org admin invites, PMC approves ----------
class InviteIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(pattern=PHONE)


def _org_admin(b: dict) -> dict:
    if not b["verified"] or not b["user"].get("is_org_admin"):
        raise HTTPException(status_code=403, detail="Only the organisation's main buyer can manage the team, after PMC verifies the organisation")
    return b


@router.get("/team")
async def team(b=Depends(current_buyer)):
    if not b["tenant"]:
        u = b["user"]
        return {"members": [{"id": b["id"], "name": u.get("name"), "email": u["email"], "is_org_admin": bool(u.get("is_org_admin")),
                             "is_active": True, "me": True}], "requests": []}
    code = b["tenant"]["code"]
    members = [{"id": str(u["_id"]), "name": u.get("name"), "email": u["email"], "is_org_admin": bool(u.get("is_org_admin")),
                "is_active": u.get("is_active", True), "me": str(u["_id"]) == b["id"]}
               async for u in db.admin_users.find({"tenant_id": code, "roles": "buyer"}).sort("email", 1)]
    reqs = [_out(r) async for r in db.buyer_team_requests.find({"tenant_code": code}).sort("created_at", -1).limit(100)]
    return {"members": members, "requests": reqs}


@router.post("/team/invite")
async def invite(body: InviteIn, b=Depends(buyer_write)):
    _org_admin(b)
    code, email = b["tenant"]["code"], body.email.lower()
    if await db.buyer_team_requests.count_documents({"tenant_code": code, "status": "pending"}) >= 10:
        raise HTTPException(status_code=429, detail="You already have 10 invites waiting for PMC approval")
    if await db.admin_users.find_one({"email": email}) or await db.buyer_team_requests.find_one({"email": email, "status": "pending"}):
        raise HTTPException(status_code=409, detail="This email already has a PMC sign-in or a pending invite")
    doc = {"tenant_code": code, "org_name": b["tenant"]["name"], "name": body.name.strip(), "email": email,
           "phone": re.sub(r"[ \-]", "", body.phone), "status": "pending", "invited_by": b["email"], "created_at": now_iso()}
    r = await db.buyer_team_requests.insert_one(doc)
    await audit_log("buyer.team_invite", {"id": b["id"], "email": b["email"]}, "buyer_team_request", str(r.inserted_id), {"email": email})
    await notify_role("admin", f"Buyer team invite to approve — {doc['org_name']}",
                      f"<p>{E(b['email'])} wants to add {E(doc['name'])} &lt;{E(email)}&gt; to {E(doc['org_name'])}.</p>"
                      "<p>Review in Admin → Growth → Buyer applications → Team invites.</p>", "buyer_team_request", str(r.inserted_id))
    return {"ok": True, "id": str(r.inserted_id)}


@router.post("/team/{uid}/remove")
async def remove(uid: str, b=Depends(buyer_write)):
    _org_admin(b)
    if uid == b["id"]:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    code = b["tenant"]["code"]
    if ObjectId.is_valid(uid):
        r = await db.admin_users.update_one({"_id": ObjectId(uid), "tenant_id": code, "roles": "buyer"}, {"$set": {"is_active": False}})
        if r.matched_count:
            await audit_log("buyer.team_remove", {"id": b["id"], "email": b["email"]}, "admin_user", uid, {})
            return {"ok": True}
        r = await db.buyer_team_requests.update_one({"_id": ObjectId(uid), "tenant_code": code, "status": "pending"}, {"$set": {"status": "cancelled"}})
        if r.matched_count:
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Team member not found")


# ---------- PMC admin ----------
@router.get("/admin/team-requests")
async def admin_team_requests(status: str = "pending", admin=Depends(pmc_staff)):
    return {"items": [_out(r) async for r in db.buyer_team_requests.find({"status": status}).sort("created_at", -1).limit(300)]}


class TeamDecisionIn(BaseModel):
    action: Literal["approve", "reject"]


@router.post("/admin/team-requests/{rid}/decision")
async def admin_team_decide(rid: str, body: TeamDecisionIn, request: Request, admin=Depends(pmc_staff)):
    await require_csrf(request)
    r = await db.buyer_team_requests.find_one({"_id": ObjectId(rid), "status": "pending"}) if ObjectId.is_valid(rid) else None
    if not r:
        raise HTTPException(status_code=409, detail="Only pending invites can be decided")
    upd = {"status": "approved" if body.action == "approve" else "rejected", "decided_by": admin["email"], "decided_at": now_iso()}
    if body.action == "approve":
        res = await _send_buyer_signin({"tenant_code": r["tenant_code"], "org_name": r["org_name"], "org_admin": False}, r["email"], r["name"], admin)
        if res["signin_status"] == "email_in_use":
            raise HTTPException(status_code=409, detail="That email already has a different PMC sign-in")
        upd.update(res)
    await db.buyer_team_requests.update_one({"_id": r["_id"]}, {"$set": upd})
    await audit_log("buyer.team_decide", admin, "buyer_team_request", rid, upd)
    return {"ok": True, **upd}


class AdminBuyerIn(ProfileIn):
    email: EmailStr


@router.post("/admin/buyers")
async def admin_add_buyer(body: AdminBuyerIn, request: Request, admin=Depends(pmc_staff)):
    """PMC adds a verified buyer directly: organisation + sign-in emailed in one step."""
    await require_csrf(request)
    email = body.email.lower()
    if await db.admin_users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="This email already has a PMC sign-in")
    prof = await _profile(body)
    a = {"org_name": prof["org_name"] or prof["name"], "org_type": "private" if prof["org_name"] else "other", "country": prof["country_code"],
         "contact_name": prof["name"], "email": email, "phone": f"{prof['phone_code'] or ''} {prof['phone']}".strip(), "status": "approved",
         "source": "admin_added", "email_verified": True, "created_at": now_iso(), "profile": prof, "decided_by": admin["email"], "decided_at": now_iso()}
    r = await db.buyer_applications.insert_one(a)
    a["_id"] = r.inserted_id
    upd = await approve_buyer_app(a, admin)
    await db.admin_users.update_one({"email": email}, {"$set": {"buyer_profile": prof}})
    await db.buyer_applications.update_one({"_id": r.inserted_id}, {"$set": upd})
    await audit_log("buyer.admin_added", admin, "buyer_application", str(r.inserted_id), {"email": email, **upd})
    return {"ok": True, "id": str(r.inserted_id), **upd}


async def notify_bidder(who: dict, subject: str, body: str, link: str) -> None:
    """Marketplace event to a buyer (bell by user id) or supplier (bell by email)."""
    await notify_user(who.get("id") if who.get("kind") == "buyer" else None, who.get("email"), subject, body, link)
