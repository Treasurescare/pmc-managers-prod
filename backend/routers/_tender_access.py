"""R9 — shared access layer for the Tender Builder (templates + Tender Pro).

The staff Tender Builder and the vendor Tender Builder share ONE set of
backend endpoints. Those endpoints no longer gate on a single role; they gate
on a *principal* that is either:

  * a staff principal  — resolved from the admin `access_token`, role must be
    in the allowed set (admin / reviewer / auditor), OR
  * a vendor principal — resolved from the `vendor_token`, which additionally
    carries R9 entitlement (active paid subscription + at least one paid
    category) and a `read_only` flag for lapsed subscriptions.

Resource ownership is enforced server-side: a vendor may only read/mutate
templates they own (`owner_vendor_id`) plus the shared master library (read
only). Staff keep full access. This is the authoritative tenancy boundary —
UI checks are advisory only.
"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends
from bson import ObjectId
import jwt

import config
from db import db
from models.base import now_iso
from security import require_csrf


# ----------------------- subscription + category entitlement -----------------------

def vendor_country(vdoc: dict) -> Optional[str]:
    """Best-effort ISO country for a vendor (subscription price is per country)."""
    vdoc = vdoc or {}
    profile = vdoc.get("profile") or {}
    for v in (vdoc.get("country"), profile.get("country"),
              vdoc.get("primary_country"), vdoc.get("incorporation_country"),
              vdoc.get("home_country")):
        if v:
            return str(v).upper()[:3]
    ops = vdoc.get("operating_countries") or []
    if ops:
        return str(ops[0]).upper()[:3]
    return None


def _master_price(m: Optional[dict]) -> float:
    for s in (m or {}).get("slabs") or []:
        amt = s.get("fixed_amount")
        if amt and float(amt) > 0:
            return float(amt)
    return 0.0


async def sub_config(country: Optional[str] = None) -> dict:
    """Tender-builder subscription price straight from the Fee Master
    (emd_masters, kind='subscription') for the vendor's COUNTRY. No priced
    master for that country -> free (enabled False)."""
    free = {"enabled": False, "amount": 0.0, "currency": "usd",
            "period_days": 365, "master_id": None, "master_name": None,
            "country": (country or None)}
    if not country:
        return free
    m = await db.emd_masters.find_one({"kind": "subscription",
                                       "country": country.upper(), "is_active": True,
                                       "category": None})
    if not m:
        m = await db.emd_masters.find_one({"kind": "subscription",
                                           "country": country.upper(), "is_active": True})
    price = _master_price(m)
    if not m or price <= 0:
        return free
    return {"enabled": True, "amount": price,
            "currency": (m.get("currency") or "usd").lower(),
            "period_days": int(m.get("period_days") or 365),
            "master_id": str(m["_id"]), "master_name": m.get("name"),
            "country": country.upper()}


def sub_active(vdoc: dict) -> bool:
    sub = (vdoc or {}).get("tender_builder_sub") or {}
    if not sub.get("active"):
        return False
    exp = sub.get("expires_at")
    return bool(exp) and exp > now_iso()


async def vendor_entitlement(vdoc: dict) -> dict:
    """R9 entitlement snapshot. Policy: the Tender Builder is subscription-gated
    ONLY when the Fee Master defines a real price for the vendor's country. No
    priced master -> the full builder is FREE for KYC-approved vendors. There is
    no fallback/sample price and renewal is re-checked here at operation time."""
    country = vendor_country(vdoc)
    cfg = await sub_config(country)
    required = bool(cfg.get("enabled")) and float(cfg.get("amount") or 0) > 0
    active = sub_active(vdoc)
    entitled = (not required) or active
    read_only = required and not active
    return {
        "country": country,
        "sub_required": required,
        "sub_active": active,
        "free": (not required),
        "sub_expires_at": (vdoc.get("tender_builder_sub") or {}).get("expires_at"),
        "price": {"amount": cfg.get("amount"), "currency": cfg.get("currency"),
                  "period_days": cfg.get("period_days"),
                  "master_id": cfg.get("master_id"), "master_name": cfg.get("master_name")},
        "entitled": bool(entitled),
        "read_only": bool(read_only),
    }


# ----------------------- principal resolution -----------------------

def _decode(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except Exception:
        return None


async def _resolve_admin(request: Request) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        return None
    payload = _decode(token)
    if not payload or payload.get("type") != "access":
        return None
    user = await db.admin_users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        return None
    return {
        "kind": "admin",
        "id": str(user["_id"]),
        "email": user["email"],
        "role": payload.get("role") or user.get("role") or "admin",
        "roles": user.get("roles") or [user.get("role") or "admin"],
    }


async def _resolve_vendor(request: Request) -> Optional[dict]:
    token = request.cookies.get("vendor_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        return None
    payload = _decode(token)
    if not payload or payload.get("type") != "vendor_access":
        return None
    v = await db.vendors.find_one({"_id": ObjectId(payload["sub"])})
    if not v:
        return None
    if int(payload.get("gen") or 0) < int(v.get("token_generation") or 0):
        return None
    ent = await vendor_entitlement(v)
    return {
        "kind": "vendor",
        "role": "vendor",
        "id": str(v["_id"]),
        "email": v["email"],
        "vendor_ref": v.get("vendor_ref"),
        "company_name": v.get("company_name"),
        "kyc_status": v.get("kyc_status") or "verified",
        "entitlement": ent,
    }


_ADMIN_ROLES = ("admin", "reviewer", "auditor")


async def tender_principal(request: Request) -> dict:
    """Resolve a staff OR vendor principal. Prefers an admin session; falls
    back to a vendor session. Raises 401 if neither is present."""
    admin = await _resolve_admin(request)
    if admin and admin["role"] in _ADMIN_ROLES:
        return admin
    vendor = await _resolve_vendor(request)
    if vendor:
        if vendor["kyc_status"] != "verified":
            raise HTTPException(status_code=403,
                detail="Your account must be approved and KYC-verified to use the tender builder.")
        return vendor
    raise HTTPException(status_code=401, detail="Not authenticated")


def is_vendor(p: dict) -> bool:
    return p.get("kind") == "vendor"


def assert_write(p: dict) -> None:
    """Writes require: staff with admin role, or an entitled (not read-only)
    vendor. Lapsed/unpaid vendors keep read access but cannot mutate."""
    if not is_vendor(p):
        if p.get("role") not in ("admin", "reviewer"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return
    ent = p.get("entitlement") or {}
    if ent.get("read_only"):
        raise HTTPException(status_code=402,
            detail="Your tender-builder subscription has lapsed. Resubscribe to continue editing.")
    if not ent.get("entitled"):
        raise HTTPException(status_code=402,
            detail="An active tender-builder subscription is required to edit tenders.")


async def write_principal(request: Request) -> dict:
    p = await tender_principal(request)
    if not is_vendor(p):
        await require_csrf(request)
    assert_write(p)
    return p


def scope_filter(p: dict, base: Optional[dict] = None) -> dict:
    """Restrict a template query to what the principal may READ. Staff: all.
    Vendor: own drafts + shared (approved) masters."""
    q = dict(base or {})
    if is_vendor(p):
        q["$or"] = [
            {"is_master": True, "moderation_status": {"$nin": ["pending", "rejected"]}},
            {"owner_vendor_id": p["id"]},
        ]
    return q


def assert_can_edit_doc(p: dict, doc: dict) -> None:
    """A write against a specific template doc. Vendors may only edit their own
    non-master drafts; masters are read-only to them."""
    if not is_vendor(p):
        return
    if doc.get("is_master"):
        raise HTTPException(status_code=403, detail="Master templates are read-only.")
    if doc.get("owner_vendor_id") != p["id"]:
        raise HTTPException(status_code=404, detail="Template not found")
    if doc.get("review_status") in ("submitted", "approved"):
        raise HTTPException(status_code=409,
            detail=f"This tender is '{doc.get('review_status')}' and can't be edited now.")


def assert_can_read_doc(p: dict, doc: dict) -> None:
    if not is_vendor(p):
        return
    if doc.get("is_master") and doc.get("moderation_status") not in ("pending", "rejected"):
        return
    if doc.get("owner_vendor_id") == p["id"]:
        return
    raise HTTPException(status_code=404, detail="Template not found")


def actor(p: dict) -> dict:
    """Audit-log actor shape compatible with audit_log()."""
    return {"id": p.get("id"), "email": p.get("email"),
            "role": "vendor" if is_vendor(p) else p.get("role")}
