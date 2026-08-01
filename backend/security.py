import bcrypt
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Depends
from bson import ObjectId

import config
from db import db


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_admin_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role, "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def new_magic_token() -> str:
    """URL-safe token used to resume registration drafts via email link."""
    return secrets.token_urlsafe(32)


async def current_admin(request: Request) -> dict:
    """Auth dependency for admin/reviewer routes."""
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.admin_users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role", "admin"),
            "tenant_id": user.get("tenant_id", config.DEFAULT_TENANT_ID),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles: str):
    async def _dep(admin: dict = Depends(current_admin)) -> dict:
        if admin.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin
    return _dep
