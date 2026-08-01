from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Response, Depends

from db import db
from models import AdminLoginIn
from security import verify_password, create_admin_token, current_admin
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])


@router.post("/login")
async def admin_login(payload: AdminLoginIn, response: Response) -> Dict[str, Any]:
    user = await db.admin_users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_admin_token(str(user["_id"]), user["email"], user.get("role", "admin"))
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="lax",
                        max_age=config.ACCESS_TOKEN_TTL_MIN * 60, path="/")
    await audit_log("admin.login", {"id": str(user["_id"]), "email": user["email"]},
                    "admin_user", str(user["_id"]), {})
    return {"id": str(user["_id"]), "email": user["email"], "name": user.get("name"),
            "role": user.get("role", "admin"), "token": token}


@router.post("/logout")
async def admin_logout(response: Response) -> Dict[str, bool]:
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/me")
async def admin_me(admin: Dict[str, Any] = Depends(current_admin)) -> Dict[str, Any]:
    return admin
