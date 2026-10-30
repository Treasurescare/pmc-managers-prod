"""LinkedIn: 'Continue with LinkedIn' sign-in (existing accounts only) and company-page posting with approval."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

import config
from audit import audit_log
from db import db
from models.base import now_iso
from routers._social_signin import sign_in_existing
from routers.marketing import ADMIN, CSRF, _api_base, _id, _oid

router = APIRouter(tags=["linkedin"])
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"


def _cfg() -> dict:
    return {"id": os.environ.get("LINKEDIN_CLIENT_ID", ""), "secret": os.environ.get("LINKEDIN_CLIENT_SECRET", ""),
            "org": os.environ.get("LINKEDIN_ORG_ID", ""), "version": os.environ.get("LINKEDIN_VERSION", "202610")}


def _redirect_uri() -> str:
    return f"{_api_base()}/api/v1/auth/linkedin/callback"


async def _start(purpose: str, portal: str, scope: str) -> RedirectResponse:
    c = _cfg()
    if not c["id"] or not c["secret"]:
        return RedirectResponse(f"{config.FRONTEND_URL}/login?li_error=" + quote("LinkedIn sign-in is not set up yet."))
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"_id": state, "purpose": purpose, "portal": portal,
                                      "created_at": datetime.now(timezone.utc)})
    q = {"response_type": "code", "client_id": c["id"], "redirect_uri": _redirect_uri(), "state": state, "scope": scope}
    return RedirectResponse(AUTH_URL + "?" + urlencode(q))


@router.get("/api/v1/auth/linkedin/status")
async def li_public_status():
    c = _cfg()
    return {"signin_enabled": bool(c["id"] and c["secret"])}


@router.get("/api/v1/auth/linkedin/start")
async def li_start(portal: str = "supplier"):
    if portal not in ("supplier", "staff", "admin"):
        raise HTTPException(status_code=422, detail="Unknown portal")
    return await _start("login", portal, "openid profile email")


@router.get("/api/v1/marketing/linkedin/connect")
async def li_connect(admin=ADMIN):
    return {"url": (await _start("post", "admin", "openid profile email w_organization_social")).headers["location"]}


@router.get("/api/v1/auth/linkedin/callback")
async def li_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    fail = lambda msg: RedirectResponse(f"{config.FRONTEND_URL}/login?li_error=" + quote(msg))
    st = await db.oauth_states.find_one_and_delete({"_id": state}) if state else None
    if error or not code or not st:
        return fail("LinkedIn sign-in was cancelled or expired. Please try again.")
    if datetime.now(timezone.utc) - st["created_at"].replace(tzinfo=timezone.utc) > timedelta(minutes=10):
        return fail("LinkedIn sign-in expired. Please try again.")
    c = _cfg()
    async with httpx.AsyncClient(timeout=15) as cl:
        t = await cl.post(TOKEN_URL, data={"grant_type": "authorization_code", "code": code, "client_id": c["id"],
                                           "client_secret": c["secret"], "redirect_uri": _redirect_uri()})
        if t.status_code != 200:
            return fail("LinkedIn could not confirm your sign-in.")
        tok = t.json()
        info = (await cl.get(USERINFO_URL, headers={"Authorization": f"Bearer {tok['access_token']}"})).json()
    email = (info.get("email") or "").strip().lower()
    if not email or info.get("email_verified") is False:
        return fail("LinkedIn did not share a verified email address.")
    if st["purpose"] == "post":
        await db.mkt_settings.update_one({"_id": "linkedin"}, {"$set": {
            "access_token": tok["access_token"], "connected_by": email, "connected_at": now_iso(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=int(tok.get("expires_in") or 0))).isoformat()}},
            upsert=True)
        await audit_log("linkedin.connect", {"email": email}, "mkt_settings", "linkedin", {})
        return RedirectResponse(f"{config.FRONTEND_URL}/admin/e/marketing?tab=social&li=connected")
    resp = RedirectResponse(f"{config.FRONTEND_URL}/")
    try:
        r = await sign_in_existing(email, st["portal"], resp, request, "linkedin")
    except HTTPException as e:
        return fail(str(e.detail))
    resp.headers["location"] = f"{config.FRONTEND_URL}{r['next']}"
    return resp


# ---------- approval queue ----------

def _post_text(n: dict) -> str:
    bits = [f"New tender on PMC Managers: {n.get('title')}"]
    if n.get("category"):
        bits.append(f"Category: {n['category']}")
    if n.get("delivery_country"):
        bits.append(f"Delivery: {n['delivery_country']}")
    if n.get("submission_deadline"):
        bits.append(f"Closes: {str(n['submission_deadline'])[:10]}")
    bits.append("Registered suppliers can view the notice and bid online.")
    return "\n".join(bits) + "\n\n#tenders #procurement"


async def queue_social_post(notice_ref: str) -> None:
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n or await db.mkt_social_posts.find_one({"notice_ref": notice_ref}):
        return
    await db.mkt_social_posts.insert_one({"notice_ref": notice_ref, "title": n.get("title"), "text": _post_text(n),
                                          "status": "pending", "created_at": now_iso()})


@router.get("/api/v1/marketing/social-posts")
async def list_posts(admin=ADMIN):
    rows = await db.mkt_social_posts.find().sort("created_at", -1).limit(200).to_list(200)
    s = await db.mkt_settings.find_one({"_id": "linkedin"}) or {}
    c = _cfg()
    return {"items": [{**_id(r), "share_url": f"{_api_base()}/api/v1/share/notice/{r['notice_ref']}"} for r in rows],
            "linkedin": {"app_configured": bool(c["id"] and c["secret"]), "org_configured": bool(c["org"]),
                         "connected": bool(s.get("access_token")), "connected_by": s.get("connected_by"),
                         "expires_at": s.get("expires_at")}}


class PostEditIn(BaseModel):
    text: str = Field(min_length=5, max_length=2900)


@router.put("/api/v1/marketing/social-posts/{pid}", dependencies=CSRF)
async def edit_post(pid: str, body: PostEditIn, admin=ADMIN):
    await db.mkt_social_posts.update_one({"_id": _oid(pid), "status": "pending"}, {"$set": {"text": body.text}})
    return {"ok": True}


@router.post("/api/v1/marketing/social-posts/{pid}/reject", dependencies=CSRF)
async def reject_post(pid: str, admin=ADMIN):
    await db.mkt_social_posts.update_one({"_id": _oid(pid), "status": "pending"},
                                         {"$set": {"status": "rejected", "decided_by": admin.get("email"), "decided_at": now_iso()}})
    return {"ok": True}


@router.post("/api/v1/marketing/social-posts/{pid}/mark-posted", dependencies=CSRF)
async def mark_posted(pid: str, admin=ADMIN):
    await db.mkt_social_posts.update_one({"_id": _oid(pid)}, {"$set": {"status": "posted", "posted_manually": True,
                                                                      "decided_by": admin.get("email"), "decided_at": now_iso()}})
    return {"ok": True}


@router.post("/api/v1/marketing/social-posts/{pid}/approve", dependencies=CSRF)
async def approve_post(pid: str, admin=ADMIN):
    p = await db.mkt_social_posts.find_one({"_id": _oid(pid)})
    if not p or p["status"] != "pending":
        raise HTTPException(status_code=409, detail="This post was already handled.")
    c = _cfg()
    s = await db.mkt_settings.find_one({"_id": "linkedin"}) or {}
    if not (c["org"] and s.get("access_token")):
        raise HTTPException(status_code=424, detail="Connect your LinkedIn company page first (button at the top of this tab).")
    n = await db.notices.find_one({"notice_ref": p["notice_ref"]}) or {}
    body = {"author": f"urn:li:organization:{c['org']}", "commentary": p["text"], "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "content": {"article": {"source": f"{_api_base()}/api/v1/share/notice/{p['notice_ref']}",
                                    "title": str(n.get("title") or p.get("title") or "Tender")[:200],
                                    "description": f"{n.get('category') or 'Tender'} · published on PMC Managers"}},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    async with httpx.AsyncClient(timeout=20) as cl:
        r = await cl.post(POSTS_URL, json=body, headers={"Authorization": f"Bearer {s['access_token']}",
                                                         "LinkedIn-Version": c["version"], "X-Restli-Protocol-Version": "2.0.0"})
    if r.status_code >= 400:
        msg = "LinkedIn connection expired — reconnect the page." if r.status_code == 401 else f"LinkedIn refused the post ({r.status_code})."
        await db.mkt_social_posts.update_one({"_id": p["_id"]}, {"$set": {"last_error": r.text[:300]}})
        raise HTTPException(status_code=502, detail=msg)
    await db.mkt_social_posts.update_one({"_id": p["_id"]}, {"$set": {
        "status": "posted", "linkedin_id": r.headers.get("x-restli-id"), "decided_by": admin.get("email"), "decided_at": now_iso()}})
    await audit_log("linkedin.post", admin, "notice", p["notice_ref"], {})
    return {"ok": True}
