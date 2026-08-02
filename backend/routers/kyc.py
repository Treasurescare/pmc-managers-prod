"""Wave 8-10 — KYC connector.

Provider switch via env vars in /app/backend/.env:
  KYC_PROVIDER=kyc-checks | stub    (default: stub)
  KYC_BASE_URL=https://api.kyc-checks.com/v1
  KYC_API_KEY=...
  KYC_WEBHOOK_SECRET=...

If KYC_PROVIDER is not "stub" AND KYC_API_KEY is set, we call the live provider.
Otherwise we fall back to the deterministic stub so demos keep working offline.

Contract (same for stub + live):
- POST /kyc/start    → {case_id, risk_score, status, flags, provider}
- GET  /kyc/{case_id}
- POST /kyc/webhook  → provider async callback (updates in-place)
"""
import secrets, hashlib, hmac, logging
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from bson import ObjectId
import httpx

import config
from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/kyc", tags=["kyc"])


KYCLevel = Literal["basic", "enhanced", "sanctions-only"]


class KYCStartIn(BaseModel):
    vendor_ref: str
    level: KYCLevel = "basic"


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- STUB (deterministic per vendor_ref) ----------

def _run_stub(vendor: dict, level: str) -> dict:
    seed = int(hashlib.sha256((vendor.get("vendor_ref") or "").encode()).hexdigest()[:8], 16)
    risk_score = seed % 100
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
            "provider": "STUB"}


# ---------- KYC-Checks live client ----------

async def _run_kyc_checks(vendor: dict, level: str) -> dict:
    """Live call to KYC-Checks. Contract may vary — adjust the JSON keys once we
    receive the client's actual API doc URL. Defensive: if the call fails or the
    response is missing fields, we log + fall back to a 'review' verdict rather
    than crashing the vendor workflow."""
    if not (config.KYC_BASE_URL and config.KYC_API_KEY):
        logging.warning("KYC_PROVIDER=kyc-checks but base URL/key missing — using stub")
        return _run_stub(vendor, level)

    payload = {
        "reference": vendor.get("vendor_ref"),
        "company_name": vendor.get("company_name"),
        "email": vendor.get("email"),
        "country": vendor.get("country"),
        "level": level,  # provider maps to their tier
    }
    headers = {
        "Authorization": f"Bearer {config.KYC_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{config.KYC_BASE_URL.rstrip('/')}/verify", headers=headers, json=payload)
        if r.status_code >= 400:
            logging.error(f"KYC-Checks HTTP {r.status_code}: {r.text[:400]}")
            return {**_run_stub(vendor, level), "provider": f"kyc-checks-error-{r.status_code}",
                    "flags": ["KYC provider returned an error — case marked for manual review"],
                    "status": "review"}
        j = r.json()
        # Best-effort mapping (adjust once real spec confirmed)
        return {
            "risk_score": int(j.get("risk_score") or j.get("score") or 0),
            "status": (j.get("status") or j.get("decision") or "review").lower(),
            "flags": j.get("flags") or j.get("findings") or [],
            "documents_ok": bool(j.get("documents_ok", True)),
            "sanctions_hit": bool(j.get("sanctions_hit", False)),
            "level": level,
            "provider": "kyc-checks",
            "provider_case_id": j.get("case_id") or j.get("id"),
            "provider_raw": j,
        }
    except Exception as e:
        logging.exception(f"KYC-Checks call failed: {e}")
        return {**_run_stub(vendor, level), "provider": "kyc-checks-exception",
                "flags": ["KYC provider unreachable — case marked for manual review"],
                "status": "review"}


async def _verify(vendor: dict, level: str) -> dict:
    if config.KYC_PROVIDER == "kyc-checks":
        return await _run_kyc_checks(vendor, level)
    return _run_stub(vendor, level)


@router.post("/start")
async def start_kyc(payload: KYCStartIn, admin=Depends(require_role("admin", "legal_counsel"))):
    v = await db.vendors.find_one({"vendor_ref": payload.vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await _verify(v, payload.level)
    case_id = f"kyc_{secrets.token_urlsafe(10)}"
    doc = {
        "case_id": case_id, "vendor_ref": payload.vendor_ref,
        "vendor_email": v.get("email"), "level": payload.level,
        **result, "created_by": admin["id"], "created_at": now_iso(),
    }
    await db.kyc_cases.insert_one(doc)
    await db.vendors.update_one(
        {"vendor_ref": payload.vendor_ref},
        {"$set": {"kyc_status": result["status"], "kyc_score": result["risk_score"],
                  "kyc_at": now_iso(), "kyc_provider": result.get("provider")}},
    )
    await audit_log("kyc.run", admin, "vendor", payload.vendor_ref,
                    {"case_id": case_id, "status": result["status"],
                     "provider": result.get("provider")})
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
async def kyc_webhook(request: Request):
    """Live-mode entry point. Providers POST here with async results.
    If KYC_WEBHOOK_SECRET is set we verify the HMAC signature (X-Kyc-Signature)."""
    body = await request.body()
    if config.KYC_WEBHOOK_SECRET:
        sig = request.headers.get("x-kyc-signature", "")
        expected = hmac.new(config.KYC_WEBHOOK_SECRET.encode(), body,
                             hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = await request.json()
    if payload.get("case_id"):
        await db.kyc_cases.update_one(
            {"case_id": payload["case_id"]},
            {"$set": {"webhook_received_at": now_iso(), "webhook_payload": payload,
                      "status": payload.get("status", "review")}},
        )
    return {"ok": True}
