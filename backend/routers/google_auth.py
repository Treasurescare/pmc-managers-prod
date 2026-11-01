"""Sign in with Google using PMC's own Google OAuth client (existing vendor and staff accounts only)."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

import config
from db import db
from routers._social_signin import sign_in_existing

router = APIRouter(prefix="/api/v1/auth/google", tags=["google-auth"])
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def _client() -> tuple:
    return os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip(), os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()


def _allowed_origins() -> set:
    raw = [config.FRONTEND_URL] + config.CORS_ORIGINS.split(",") + os.environ.get("GOOGLE_OAUTH_ALLOWED_ORIGINS", "").split(",")
    out = set()
    for o in raw:
        p = urlparse(o.strip())
        if p.scheme and p.netloc:
            out.add(f"{p.scheme}://{p.netloc}")
    return out


class StartIn(BaseModel):
    portal: Literal["supplier", "staff", "admin"]
    redirect_uri: str = Field(min_length=10, max_length=300)


class ExchangeIn(BaseModel):
    code: str = Field(min_length=8, max_length=2048)
    state: str = Field(min_length=16, max_length=128)


@router.get("/config")
async def google_config():
    cid, sec = _client()
    return {"enabled": bool(cid and sec)}


@router.post("/start")
async def start(body: StartIn):
    cid, sec = _client()
    if not (cid and sec):
        raise HTTPException(status_code=503, detail="Google sign-in is not set up yet. Please sign in with your email and password.")
    p = urlparse(body.redirect_uri)
    if f"{p.scheme}://{p.netloc}" not in _allowed_origins() or p.path != "/auth/google/callback":
        raise HTTPException(status_code=400, detail="This site address is not allowed for Google sign-in.")
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"state": state, "portal": body.portal, "redirect_uri": body.redirect_uri,
                                      "created_at": datetime.now(timezone.utc).isoformat()})
    q = {"client_id": cid, "redirect_uri": body.redirect_uri, "response_type": "code", "scope": "openid email profile",
         "state": state, "prompt": "select_account"}
    return {"url": f"{AUTH_URL}?{urlencode(q)}"}


@router.post("/exchange")
async def exchange(body: ExchangeIn, response: Response, request: Request):
    cid, sec = _client()
    since = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    st = await db.oauth_states.find_one_and_update(
        {"state": body.state, "created_at": {"$gte": since}, "used_at": {"$exists": False}},
        {"$set": {"used_at": datetime.now(timezone.utc).isoformat()}})
    if not st or not (cid and sec):
        raise HTTPException(status_code=401, detail="Google sign-in expired. Please try again.")
    async with httpx.AsyncClient(timeout=15) as c:
        t = await c.post(TOKEN_URL, data={"code": body.code, "client_id": cid, "client_secret": sec,
                                          "redirect_uri": st["redirect_uri"], "grant_type": "authorization_code"})
        idt = (t.json() if t.status_code == 200 else {}).get("id_token")
        info = (await c.get(TOKENINFO_URL, params={"id_token": idt})).json() if idt else {}
    if info.get("aud") != cid or str(info.get("email_verified")).lower() != "true":
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
    email = (info.get("email") or "").strip().lower()
    return await sign_in_existing(email, st["portal"], response, request, "google")
