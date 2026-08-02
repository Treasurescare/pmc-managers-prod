"""Wave 7 — MFA (TOTP) for staff. Enrol, verify, disable. Enforced on login
when user.mfa_enabled=True (see routers/staff_auth.py login flow)."""
import io, base64, secrets
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
import pyotp
import qrcode

from db import db
from models.base import now_iso
from security import current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/staff/mfa", tags=["mfa"])


class MFAVerifyIn(BaseModel):
    otp_code: str = Field(min_length=6, max_length=8)


@router.post("/enroll")
async def mfa_enroll(admin=Depends(current_admin)) -> Dict[str, Any]:
    """Generate a TOTP secret + provisioning URI + QR code (base64 PNG).
    Secret is stored pending — MFA is only ACTIVE after /verify succeeds."""
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if doc and doc.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA already enabled — disable first to re-enrol")
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=admin["email"], issuer_name="PMC Managers")
    # Build a PNG QR
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    await db.admin_users.update_one(
        {"_id": ObjectId(admin["id"])},
        {"$set": {"mfa_secret_pending": secret, "mfa_secret_pending_at": now_iso()}},
    )
    return {"otp_uri": uri, "qr_png_base64": qr_b64, "secret": secret}


@router.post("/verify")
async def mfa_verify(payload: MFAVerifyIn, admin=Depends(current_admin)) -> Dict[str, Any]:
    """Verify a TOTP code against the pending secret and enable MFA."""
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    pending = (doc or {}).get("mfa_secret_pending")
    if not pending:
        raise HTTPException(status_code=400, detail="No pending MFA enrolment")
    totp = pyotp.TOTP(pending)
    if not totp.verify(payload.otp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")
    recovery_codes = [secrets.token_hex(4) for _ in range(6)]
    await db.admin_users.update_one(
        {"_id": ObjectId(admin["id"])},
        {"$set": {"mfa_enabled": True, "mfa_secret": pending,
                  "mfa_recovery_codes": recovery_codes, "mfa_enabled_at": now_iso()},
         "$unset": {"mfa_secret_pending": "", "mfa_secret_pending_at": ""}},
    )
    await audit_log("mfa.enable", admin, "admin_user", admin["id"], {})
    return {"ok": True, "recovery_codes": recovery_codes}


@router.post("/disable")
async def mfa_disable(payload: MFAVerifyIn, admin=Depends(current_admin)) -> Dict[str, bool]:
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if not doc or not doc.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    if not pyotp.TOTP(doc["mfa_secret"]).verify(payload.otp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")
    await db.admin_users.update_one(
        {"_id": ObjectId(admin["id"])},
        {"$set": {"mfa_enabled": False},
         "$unset": {"mfa_secret": "", "mfa_recovery_codes": ""}},
    )
    await audit_log("mfa.disable", admin, "admin_user", admin["id"], {})
    return {"ok": True}


@router.get("/status")
async def mfa_status(admin=Depends(current_admin)) -> Dict[str, Any]:
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    return {"enabled": bool((doc or {}).get("mfa_enabled")),
            "pending_enrolment": bool((doc or {}).get("mfa_secret_pending"))}
