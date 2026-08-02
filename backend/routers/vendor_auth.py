"""Vendor auth — separate collection from staff, cookie-based session."""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Response, Depends, Request
from bson import ObjectId
import jwt

from db import db
from models.vendor_user import VendorLoginIn, VendorPasswordChangeIn
from security import verify_password, hash_password, new_csrf_token
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/vendor", tags=["vendor-auth"])


def _create_vendor_token(vendor_id: str, email: str) -> str:
    payload = {
        "sub": vendor_id, "email": email, "type": "vendor_access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _set_cookies(response: Response, token: str) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    response.set_cookie("vendor_token", token, httponly=True, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    csrf = new_csrf_token()
    response.set_cookie("csrf_token", csrf, httponly=False, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    return csrf


async def current_vendor(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("vendor_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "vendor_access":
            raise HTTPException(status_code=401, detail="Invalid token")
        v = await db.vendors.find_one({"_id": ObjectId(payload["sub"])})
        if not v:
            raise HTTPException(status_code=401, detail="Vendor not found")
        return {
            "id": str(v["_id"]),
            "email": v["email"],
            "vendor_ref": v.get("vendor_ref"),
            "company_name": v.get("company_name"),
            "must_change_password": v.get("must_change_password", False),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/auth/login")
async def vendor_login(payload: VendorLoginIn, response: Response) -> Dict[str, Any]:
    v = await db.vendors.find_one({"email": payload.email.lower()})
    if not v or not verify_password(payload.password, v.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not v.get("is_active", True):
        raise HTTPException(status_code=403, detail="Vendor account disabled")
    token = _create_vendor_token(str(v["_id"]), v["email"])
    csrf = _set_cookies(response, token)
    await audit_log("vendor.login", None, "vendor", str(v["_id"]), {"email": v["email"]})
    return {
        "id": str(v["_id"]),
        "email": v["email"],
        "vendor_ref": v.get("vendor_ref"),
        "company_name": v.get("company_name"),
        "must_change_password": v.get("must_change_password", False),
        "csrf_token": csrf,
    }


@router.post("/auth/logout")
async def vendor_logout(response: Response) -> Dict[str, bool]:
    response.delete_cookie("vendor_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def vendor_me(vendor=Depends(current_vendor)) -> Dict[str, Any]:
    return vendor


@router.post("/auth/change-password")
async def change_password(payload: VendorPasswordChangeIn, vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if not v or not verify_password(payload.current_password, v.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password incorrect")
    await db.vendors.update_one(
        {"_id": ObjectId(vendor["id"])},
        {"$set": {"password_hash": hash_password(payload.new_password),
                  "must_change_password": False,
                  "password_changed_at": datetime.now(timezone.utc).isoformat()}},
    )
    await audit_log("vendor.password_change", None, "vendor", vendor["id"], {})
    return {"ok": True}
