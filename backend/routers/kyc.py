"""Wave 8 — KYC connector.

Ships as a STUB connector today. Replace `_run_verification()` internals with
a real provider (Sumsub / Onfido / IDMerit / Persona) once the client picks
one — the vendor-facing contract stays identical.

Design goals:
- One-shot `POST /kyc/start`: kick off a check, returns a `case_id` you can poll
- `GET /kyc/{case_id}`: current status + risk score + document flags
- `POST /kyc/{case_id}/webhook`: entry point for provider callbacks (empty for stub)
"""
import secrets, hashlib
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/kyc", tags=["kyc"])


KYCLevel = Literal["basic", "enhanced", "sanctions-only"]


class KYCStartIn(BaseModel):
    vendor_ref: str
    level: KYCLevel = "basic"


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


def _run_verification(vendor: dict, level: str) -> dict:
    """STUB — replace with real provider call. Deterministic based on vendor ref
    so demos give consistent scores. Real providers (Sumsub, Onfido) return an
    async webhook, so make sure to update the DB row in that handler too."""
    seed = int(hashlib.sha256((vendor.get("vendor_ref") or "").encode()).hexdigest()[:8], 16)
    risk_score = seed % 100  # 0..99
    doc_ok = seed % 3 != 0
    sanctions_hit = seed % 17 == 0
    flags: List[str] = []
    if not doc_ok:
        flags.append("Corporate registration document could not be verified")
    if sanctions_hit:
        flags.append("Beneficial owner appears on OFAC watchlist")
    if risk_score > 75:
        flags.append(f"Elevated risk score ({risk_score}/100) — enhanced due diligence recommended")
    status = "clear" if not flags else ("hit" if sanctions_hit else "review")
    return {"risk_score": risk_score, "status": status, "flags": flags,
            "documents_ok": doc_ok, "sanctions_hit": sanctions_hit, "level": level,
            "provider": "STUB (swap for Sumsub / Onfido / Persona)"}


@router.post("/start")
async def start_kyc(payload: KYCStartIn, admin=Depends(require_role("admin", "legal_counsel"))):
    v = await db.vendors.find_one({"vendor_ref": payload.vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = _run_verification(v, payload.level)
    case_id = f"kyc_{secrets.token_urlsafe(10)}"
    doc = {
        "case_id": case_id, "vendor_ref": payload.vendor_ref,
        "vendor_email": v.get("email"), "level": payload.level,
        **result, "created_by": admin["id"], "created_at": now_iso(),
    }
    await db.kyc_cases.insert_one(doc)
    # Update vendor rollup so the Vendor Intel panel can show it
    await db.vendors.update_one(
        {"vendor_ref": payload.vendor_ref},
        {"$set": {"kyc_status": result["status"], "kyc_score": result["risk_score"],
                  "kyc_at": now_iso()}},
    )
    await audit_log("kyc.run", admin, "vendor", payload.vendor_ref,
                    {"case_id": case_id, "status": result["status"]})
    return {"case_id": case_id, **result}


@router.get("/{case_id}")
async def get_kyc(case_id: str, admin=Depends(require_role("admin", "legal_counsel", "auditor"))):
    doc = await db.kyc_cases.find_one({"case_id": case_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")
    return _out(doc)


@router.get("/vendor/{vendor_ref}")
async def list_kyc_for_vendor(vendor_ref: str,
                               admin=Depends(require_role("admin", "legal_counsel", "auditor"))):
    return [_out(k) async for k in db.kyc_cases.find({"vendor_ref": vendor_ref}).sort("created_at", -1)]


@router.post("/webhook")
async def kyc_webhook(payload: dict) -> dict:
    """Live-mode entry point. Providers POST here with async results.
    For the STUB this is a no-op that just logs the payload."""
    if payload.get("case_id"):
        await db.kyc_cases.update_one(
            {"case_id": payload["case_id"]},
            {"$set": {"webhook_received_at": now_iso(), "webhook_payload": payload}},
        )
    return {"ok": True}
