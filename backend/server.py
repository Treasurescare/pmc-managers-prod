from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import io
import csv
import uuid
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal, Dict, Any

import bcrypt
import jwt
import httpx
import stripe
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File
import asyncio
import json as _json
from fastapi.responses import StreamingResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from starlette.middleware.cors import CORSMiddleware

# ---------- Constants ----------
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 24  # 1 day
REFRESH_TOKEN_TTL_DAYS = 7
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

EMAIL_BASE_URL = "https://integrations.emergentagent.com"  # Emergent Resend proxy
EMERGENT_AUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

# Kazakhstan license categories that gate certain tender types
KZ_LICENSE_TYPES = [
    "Construction (1st category)",
    "Electrical installation",
    "Mechanical works",
    "Plumbing & firefighting",
    "Medical gas installation",
    "HSE compliance",
]

# Which tender categories require which KZ licenses
KZ_CATEGORY_LICENSE_MAP = {
    "Medical gas pipeline systems": ["Medical gas installation"],
    "OT equipment & laminar flow systems": ["Medical gas installation"],
    "Modular operation theatres (OTs)": ["Medical gas installation", "Mechanical works"],
    "External power supply grid connection": ["Electrical installation"],
    "Substation works (HT/LT)": ["Electrical installation"],
    "Transformers procurement & installation": ["Electrical installation"],
    "Elevators & escalators": ["Mechanical works", "Electrical installation"],
    "Elevators for hostel blocks": ["Mechanical works", "Electrical installation"],
    "Elevator & escalator AMC": ["Mechanical works", "Electrical installation"],
    "Fire alarm & safety systems": ["Electrical installation", "HSE compliance"],
    "External firefighting network (hydrants)": ["Plumbing & firefighting", "HSE compliance"],
    "Fire system AMC": ["HSE compliance"],
    "Water treatment plant (WTP)": ["Plumbing & firefighting"],
    "Sewage treatment plant (STP)": ["Plumbing & firefighting"],
    "Hostel bathrooms & plumbing": ["Plumbing & firefighting"],
    "Hospital civil & superstructure works": ["Construction (1st category)", "HSE compliance"],
    "Main academic building civil works": ["Construction (1st category)"],
    "Hotel superstructure works": ["Construction (1st category)"],
}

REGISTRATION_FEE_USD = float(os.environ.get("REGISTRATION_FEE_USD", "100"))
REGISTRATION_FEE_LOOKUP = "pmc_vendor_registration_fee"

# ---------- Mongo ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ---------- Stripe (Flow B — uses env STRIPE_API_KEY, defaulting to shared sk_test_emergent) ----------
stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")

# ---------- App ----------
app = FastAPI(title="PMC Managers Ltd - Tender Management API")
api = APIRouter(prefix="/api")


# ---------- Utilities ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MIN), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=ACCESS_TOKEN_TTL_MIN * 60, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax", max_age=REFRESH_TOKEN_TTL_DAYS * 86400, path="/")


def _serialize_user(user: dict) -> dict:
    user = dict(user)
    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return _serialize_user(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*allowed_roles: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dep


async def create_notification(user_id: str, title: str, body: str, link: Optional[str] = None) -> None:
    await db.notifications.insert_one({
        "user_id": user_id, "title": title, "body": body, "link": link, "read": False, "created_at": now_iso(),
    })


# ---------- Email (Resend via Emergent) ----------
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "PMC Managers Limited")


def _email_wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    cta = ""
    if cta_label and cta_url:
        cta = f'<tr><td style="padding:24px 0"><a href="{cta_url}" style="background:#0033A0;color:#fff;text-decoration:none;padding:12px 22px;font-family:system-ui,sans-serif;font-size:14px">{cta_label}</a></td></tr>'
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#fdfdfd;padding:32px 0;font-family:'IBM Plex Sans',system-ui,sans-serif">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #E4E4E7">
      <tr><td style="background:#050505;color:#fff;padding:20px 28px">
        <div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.6)">PMC Managers Limited</div>
        <div style="font-family:Georgia,serif;font-size:22px;margin-top:4px">Global Tender Board</div>
      </td></tr>
      <tr><td style="padding:32px 28px">
        <h1 style="font-family:Georgia,serif;font-size:28px;margin:0 0 12px;color:#050505">{title}</h1>
        <div style="color:#3f3f46;font-size:14px;line-height:1.6">{body_html}</div>
        {cta}
      </td></tr>
      <tr><td style="border-top:1px solid #E4E4E7;padding:16px 28px;color:#71717a;font-size:11px">
        PMC Managers Limited · Global Tender Board · Automated notification
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_email(to_email: str, subject: str, html: str) -> bool:
    if not EMAIL_KEY:
        logging.warning("EMERGENT_EMAIL_KEY not set — skipping email send")
        return False
    payload = {"to": [to_email], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
        if r.status_code >= 400:
            logging.error(f"Email failed {r.status_code}: {r.text}")
            return False
        return True
    except Exception as e:
        logging.exception(f"Email exception: {e}")
        return False


# ---------- Models ----------
Role = Literal["vendor", "buyer", "admin"]


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    role: Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleCallbackRequest(BaseModel):
    session_id: str
    role: Optional[Role] = None  # required for new users


class RoleAssignRequest(BaseModel):
    role: Role


class VendorProfileIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    company_name: str
    trade_name: Optional[str] = None
    registered_address: str
    mailing_address: Optional[str] = None
    country: str
    country_id_label: Optional[str] = None
    registration_number: str
    incorporation_date: Optional[str] = None
    tax_id: Optional[str] = None
    legal_entity_type: str
    website: Optional[str] = None
    employees_count: Optional[int] = None
    contact_name: str
    contact_title: str
    contact_office_phone: str
    contact_mobile: Optional[str] = None
    contact_email: EmailStr
    signatory_name: str
    signatory_title: str
    signatory_contact: Optional[str] = None
    bank_name: str
    bank_branch: Optional[str] = None
    bank_account_number: str
    bank_swift: str
    bank_address: Optional[str] = None
    primary_sector: str
    business_description: str
    operating_regions: List[str] = []
    business_categories: List[str] = []
    turnover_year1: Optional[float] = None
    turnover_year2: Optional[float] = None
    turnover_year3: Optional[float] = None
    turnover_currency: Optional[str] = "USD"
    previous_projects: List[dict] = []
    references: List[dict] = []
    iso_certifications: Optional[str] = None
    licenses_permits: Optional[str] = None
    insurance_details: Optional[str] = None
    litigation_history: Optional[str] = None
    kz_licenses: List[str] = []  # KZ-specific license types held
    documents: List[dict] = []
    decl_conflict_of_interest: bool = False
    decl_integrity: bool = False
    decl_accuracy: bool = False
    decl_data_consent: bool = False
    decl_fee: bool = False
    decl_notification: bool = False
    signature_name: Optional[str] = None
    signature_title: Optional[str] = None
    signature_date: Optional[str] = None


class TenderIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    document_type: Literal["tender", "rfp", "rfq"] = "tender"
    title: str
    description: str
    category: str
    budget_currency: str = "USD"
    budget_amount: Optional[float] = None
    submission_deadline: str
    delivery_location: Optional[str] = None
    delivery_country: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    required_licenses: List[str] = []
    attachments: List[dict] = []
    # RFQ-specific
    line_items: List[dict] = []  # [{item, qty, unit, target_unit_price}]
    payment_terms: Optional[str] = None
    delivery_date: Optional[str] = None
    # RFP-specific
    scope_of_work: Optional[str] = None
    expected_deliverables: Optional[str] = None
    evaluation_criteria: List[dict] = []  # [{name, weight, description}]
    evaluation_committee: List[dict] = []  # [{name, role}]
    pre_bid_meeting_date: Optional[str] = None
    bid_bond_amount: Optional[float] = None
    # Two-envelope sealed bidding (RFP only)
    two_envelope: bool = False
    # Multi-level approval workflow (P1)
    require_approval: bool = False
    # EMD / Security Deposit (P1)
    emd_required: bool = False
    emd_amount: Optional[float] = None
    emd_currency: str = "USD"
    # Org / department (P1)
    org_id: Optional[str] = None
    department_id: Optional[str] = None


class BidIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    tender_id: str
    price_currency: str = "USD"
    price_amount: float
    delivery_days: int
    proposal: Optional[str] = ""
    attachments: List[dict] = []
    # RFQ-specific
    line_item_prices: List[dict] = []  # [{item, unit_price, subtotal}]
    # RFP-specific
    technical_proposal: Optional[str] = None
    commercial_proposal: Optional[str] = None
    team_composition: Optional[str] = None
    # EMD (P1)
    emd_reference: Optional[str] = None
    emd_payment_intent_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    origin_url: str


class RfpScoreRequest(BaseModel):
    scores: Dict[str, float]  # {criterion_name: score(0-100)}
    notes: Optional[str] = None


# P1 — Buyer Org & Department models
class OrgIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    country: Optional[str] = None
    description: Optional[str] = None


class DepartmentIn(BaseModel):
    org_id: str
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    head_user_id: Optional[str] = None
    # Approval chain rules: [{threshold: <amount over which this level is required>, level: dept_head|finance|contracts_committee}]
    approval_thresholds: List[dict] = []


class DepartmentAssignRequest(BaseModel):
    department_id: str


class TenderApprovalDecision(BaseModel):
    approved: bool
    notes: Optional[str] = None


class QuestionIn(BaseModel):
    question: str = Field(min_length=3)
    anonymous: bool = True


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1)


class AddendumIn(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class EmdRefundIn(BaseModel):
    forfeit: bool = False
    notes: Optional[str] = None


# ---------- Auth ----------
@api.post("/auth/register")
async def register(payload: RegisterUserRequest, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.role == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot self-register")

    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": payload.role,
        "auth_provider": "password",
        "vendor_status": "pending" if payload.role == "vendor" else None,
        "vendor_profile": None,
        "registration_fee_paid": False,
        "created_at": now_iso(),
    }
    res = await db.users.insert_one(doc)
    user_id = str(res.inserted_id)
    access = create_access_token(user_id, email, payload.role)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    doc["_id"] = res.inserted_id
    # Fire welcome email
    if payload.role == "vendor":
        await send_email(email, "Welcome to PMC Managers · Complete your registration",
                         _email_wrap("Welcome to PMC",
                                     f"<p>Hi {doc['name']},</p><p>Your account has been created. To unlock bidding, please complete your Pre-Tender Registration Form and pay the one-time registration fee.</p>",
                                     "Complete registration", os.environ.get("FRONTEND_URL", "") + "/vendor/profile"))
    return _serialize_user(doc)


@api.post("/auth/login")
async def login(payload: LoginRequest, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_id = str(user["_id"])
    access = create_access_token(user_id, email, user["role"])
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return _serialize_user(user)


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@api.post("/auth/google-callback")
async def google_callback(payload: GoogleCallbackRequest, response: Response):
    """Exchange session_id from Emergent Google OAuth for our JWT session."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(EMERGENT_AUTH_SESSION_URL, headers={"X-Session-ID": payload.session_id})
        if r.status_code >= 400:
            raise HTTPException(status_code=401, detail="Google session invalid")
        data = r.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to verify Google session")

    email = (data.get("email") or "").lower()
    name = data.get("name") or "Google User"
    picture = data.get("picture")
    if not email:
        raise HTTPException(status_code=400, detail="No email returned from provider")

    user = await db.users.find_one({"email": email})
    if not user:
        # Need role to create the account
        if not payload.role or payload.role == "admin":
            # Signal frontend to collect role
            return {"needs_role": True, "email": email, "name": name}
        doc = {
            "email": email, "name": name, "picture": picture,
            "role": payload.role, "auth_provider": "google",
            "vendor_status": "pending" if payload.role == "vendor" else None,
            "vendor_profile": None, "registration_fee_paid": False,
            "created_at": now_iso(),
        }
        res = await db.users.insert_one(doc)
        user_id = str(res.inserted_id)
        role = payload.role
        doc["_id"] = res.inserted_id
        user = doc
    else:
        user_id = str(user["_id"])
        role = user["role"]

    access = create_access_token(user_id, email, role)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return _serialize_user(user)


# ---------- Vendor profile ----------
@api.post("/vendor/profile")
async def upsert_vendor_profile(payload: VendorProfileIn, user: dict = Depends(require_role("vendor"))):
    # Require registration-fee paid before final submission (only if all declarations true)
    all_decl = all([
        payload.decl_conflict_of_interest, payload.decl_integrity, payload.decl_accuracy,
        payload.decl_data_consent, payload.decl_fee, payload.decl_notification,
    ])
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    fee_paid = bool(u.get("registration_fee_paid"))
    if all_decl and not fee_paid:
        raise HTTPException(status_code=402, detail="Registration fee is required before submitting your profile. Please complete payment first.")

    profile = payload.model_dump()
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"vendor_profile": profile, "vendor_status": "pending", "updated_at": now_iso()}},
    )
    async for admin in db.users.find({"role": "admin"}):
        await create_notification(
            str(admin["_id"]),
            "New vendor pending approval",
            f"{profile['company_name']} ({user['email']}) submitted their Pre-Tender Registration Form.",
            "/admin/vendors",
        )
    return {"ok": True, "vendor_status": "pending"}


@api.get("/vendor/profile")
async def get_vendor_profile(user: dict = Depends(require_role("vendor"))):
    doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return {
        "vendor_profile": doc.get("vendor_profile"),
        "vendor_status": doc.get("vendor_status"),
        "registration_fee_paid": bool(doc.get("registration_fee_paid")),
    }


# ---------- Admin: vendor mgmt ----------
@api.get("/admin/vendors")
async def list_vendors(user: dict = Depends(require_role("admin"))):
    return [_serialize_user(u) async for u in db.users.find({"role": "vendor"}).sort("created_at", -1)]


@api.post("/admin/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user: dict = Depends(require_role("admin"))):
    v = await db.users.find_one({"_id": ObjectId(vendor_id), "role": "vendor"})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await db.users.update_one({"_id": ObjectId(vendor_id)}, {"$set": {"vendor_status": "approved"}})
    await create_notification(vendor_id, "Vendor account approved",
                              "Your PMC vendor account has been approved. You can now submit bids.", "/tenders")
    await send_email(v["email"], "PMC Managers — Vendor account approved",
                     _email_wrap("You're approved to bid",
                                 f"<p>Hi {v.get('name')},</p><p>Your registration has been approved by PMC Managers Limited. You can now browse open tenders and submit bids.</p>",
                                 "Browse open tenders", os.environ.get("FRONTEND_URL", "") + "/tenders"))
    return {"ok": True}


@api.post("/admin/vendors/{vendor_id}/reject")
async def reject_vendor(vendor_id: str, user: dict = Depends(require_role("admin"))):
    v = await db.users.find_one({"_id": ObjectId(vendor_id), "role": "vendor"})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await db.users.update_one({"_id": ObjectId(vendor_id)}, {"$set": {"vendor_status": "rejected"}})
    await create_notification(vendor_id, "Vendor application update",
                              "Your vendor application was not approved. Please contact support.", "/vendor")
    await send_email(v["email"], "PMC Managers — Registration update",
                     _email_wrap("Registration update",
                                 f"<p>Hi {v.get('name')},</p><p>Your vendor application was not approved at this time. Please contact PMC Compliance for guidance.</p>"))
    return {"ok": True}


@api.get("/admin/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    return [_serialize_user(u) async for u in db.users.find().sort("created_at", -1)]


@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    return {
        "users": await db.users.count_documents({}),
        "vendors_pending": await db.users.count_documents({"role": "vendor", "vendor_status": "pending"}),
        "vendors_approved": await db.users.count_documents({"role": "vendor", "vendor_status": "approved"}),
        "tenders_open": await db.tenders.count_documents({"status": "open"}),
        "tenders_total": await db.tenders.count_documents({}),
        "bids_total": await db.bids.count_documents({}),
        "fees_collected": await db.payment_transactions.count_documents({"payment_status": "paid"}),
    }


# ---------- Tenders ----------
def _tender_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


@api.post("/tenders")
async def create_tender(payload: TenderIn, user: dict = Depends(require_role("buyer", "admin"))):
    doc = payload.model_dump()
    # Server-side validation for RFP evaluation weights
    if doc.get("document_type") == "rfp":
        criteria = doc.get("evaluation_criteria") or []
        if len(criteria) == 0:
            raise HTTPException(status_code=400, detail="RFP must have at least one evaluation criterion.")
        total = sum(float(c.get("weight") or 0) for c in criteria)
        if abs(total - 100) > 0.001:
            raise HTTPException(status_code=400, detail=f"Evaluation criteria weights must sum to 100 (got {total}).")
    # Auto-attach required KZ licenses from map if delivery_country=KZ
    if (doc.get("delivery_country") or "").upper() == "KZ":
        auto = KZ_CATEGORY_LICENSE_MAP.get(doc["category"], [])
        merged = list({*doc.get("required_licenses", []), *auto})
        doc["required_licenses"] = merged

    # P1 — Multi-level approval workflow
    # Determine approval chain if department has thresholds AND (require_approval OR any budget exceeds a threshold)
    approval_chain: List[dict] = []
    dept_id = doc.get("department_id")
    if dept_id:
        dept = await db.departments.find_one({"_id": ObjectId(dept_id)})
        if dept:
            budget = float(doc.get("budget_amount") or 0)
            thresholds = sorted((dept.get("approval_thresholds") or []),
                                key=lambda t: float(t.get("threshold") or 0))
            for step in thresholds:
                if budget >= float(step.get("threshold") or 0):
                    approval_chain.append({
                        "level": step.get("level"),
                        "threshold": step.get("threshold"),
                        "decision": None,
                        "approver_user_id": None,
                        "decided_at": None,
                        "notes": None,
                    })

    needs_approval = doc.get("require_approval") or bool(approval_chain)
    initial_status = "pending_approval" if needs_approval else "open"
    approval_state = "pending" if needs_approval else "not_required"

    doc.update({
        "status": initial_status,
        "approval_state": approval_state,
        "approval_chain": approval_chain,
        "created_by": user["id"],
        "created_by_name": user.get("name"), "created_by_email": user.get("email"),
        "created_at": now_iso(), "awarded_bid_id": None,
        # P1 — Q&A/addenda default containers
        "addenda": [],
    })
    res = await db.tenders.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Broadcast SSE event to any live subscribers (only if not gated by approval)
    if initial_status == "open":
        await broker.broadcast({"type": "tender.created", "payload": {
            "id": str(res.inserted_id),
            "title": doc.get("title"),
            "description": (doc.get("description") or "")[:220],
            "document_type": doc.get("document_type") or "tender",
            "category": doc.get("category"),
            "status": doc.get("status"),
            "budget_currency": doc.get("budget_currency"),
            "budget_amount": doc.get("budget_amount"),
            "submission_deadline": doc.get("submission_deadline"),
            "delivery_country": doc.get("delivery_country"),
            "created_by_name": doc.get("created_by_name"),
            "created_at": doc.get("created_at"),
        }})

    # Notify approved vendors matching category / no filter — quick MVP fan-out
    # Emails go out in a background task so the POST doesn't block on Resend latency.
    async def _fanout_new_tender(tender_id: str, title: str, category: str, deadline: str):
        async for v in db.users.find({"role": "vendor", "vendor_status": "approved"}):
            await create_notification(str(v["_id"]), "New tender published",
                                      f"{title} — {category}", f"/tenders/{tender_id}")
            try:
                await send_email(v["email"], f"PMC · New tender: {title}",
                                 _email_wrap(title,
                                             f"<p>A new tender has been published on the PMC Global Tender Board.</p>"
                                             f"<p><strong>Category:</strong> {category}<br/>"
                                             f"<strong>Deadline:</strong> {deadline}</p>",
                                             "View tender", os.environ.get("FRONTEND_URL", "") + f"/tenders/{tender_id}"))
            except Exception:
                pass

    asyncio.create_task(_fanout_new_tender(str(res.inserted_id), doc["title"], doc["category"], doc["submission_deadline"]))

    # If pending approval — notify admins as approvers
    if initial_status == "pending_approval":
        async def _notify_approvers(tid: str, title: str):
            async for a in db.users.find({"role": "admin"}):
                await create_notification(str(a["_id"]), "Tender awaits approval",
                                          f"Approve: {title}", f"/tenders/{tid}")
        asyncio.create_task(_notify_approvers(str(res.inserted_id), doc["title"]))

    return _tender_out(doc)


@api.get("/tenders")
async def list_tenders(mine: bool = False, document_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    q: dict = {}
    if document_type:
        q["document_type"] = document_type
    if mine and user["role"] in ("buyer", "admin"):
        q["created_by"] = user["id"]
    elif user["role"] == "vendor":
        q["status"] = "open"
    return [_tender_out(t) async for t in db.tenders.find(q).sort("created_at", -1)]


@api.get("/tenders/{tender_id}")
async def get_tender(tender_id: str, user: dict = Depends(get_current_user)):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    return _tender_out(t)


@api.post("/tenders/{tender_id}/close")
async def close_tender(tender_id: str, user: dict = Depends(require_role("buyer", "admin"))):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    await db.tenders.update_one({"_id": ObjectId(tender_id)}, {"$set": {"status": "closed"}})
    await broker.broadcast({"type": "tender.updated", "payload": {"id": tender_id, "status": "closed"}})
    return {"ok": True}


@api.get("/tenders/{tender_id}/bids/export")
async def export_bids_csv(tender_id: str, user: dict = Depends(require_role("buyer", "admin"))):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    bids = [b async for b in db.bids.find({"tender_id": tender_id}).sort("price_amount", 1)]

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Tender ID", "Tender Title", "Vendor Company", "Vendor Email",
                "Currency", "Price", "Delivery Days", "Status", "Submitted At", "Proposal"])
    for b in bids:
        w.writerow([tender_id, t["title"], b.get("vendor_company"), b.get("vendor_email"),
                    b.get("price_currency"), b.get("price_amount"), b.get("delivery_days"),
                    b.get("status"), b.get("created_at"), (b.get("proposal") or "").replace("\n", " ")])
    buf.seek(0)
    filename = f"tender_{tender_id[-8:]}_bids.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------- Bids ----------
def _bid_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


# ---------- Two-envelope masking ----------
_COMMERCIAL_KEYS = ("price_amount", "price_currency", "commercial_proposal",
                    "line_item_prices", "delivery_days", "proposal")


def _mask_bid_for_two_envelope(bid: dict, tender: dict, viewer_role: str, is_owner: bool) -> dict:
    """Mask commercial/technical envelopes for buyer/admin on two-envelope RFPs.
    Vendors always see their OWN full bid.
    """
    bid = _bid_out(bid)
    if not tender.get("two_envelope"):
        return bid
    if viewer_role == "vendor":
        # Vendors only see their own bids anyway; nothing to mask.
        return bid

    tech_opened = tender.get("technical_opened_at") is not None
    comm_opened = tender.get("commercial_opened_at") is not None
    qualified = bid.get("technical_qualified") is True

    # Technical envelope still sealed → hide technical proposal
    if not tech_opened:
        bid["technical_proposal"] = None
        bid["team_composition"] = None
        bid["_technical_sealed"] = True

    # Commercial envelope conditions:
    # - Never opened → hide commercial for everyone
    # - Opened → only qualified bids reveal commercial
    if not comm_opened or not qualified:
        for k in _COMMERCIAL_KEYS:
            bid[k] = None
        bid["attachments"] = []
        bid["_commercial_sealed"] = True
    return bid


def _envelope_state(tender: dict) -> dict:
    return {
        "two_envelope": bool(tender.get("two_envelope")),
        "technical_opened_at": tender.get("technical_opened_at"),
        "commercial_opened_at": tender.get("commercial_opened_at"),
    }


@api.post("/bids")
async def create_bid(payload: BidIn, user: dict = Depends(require_role("vendor"))):
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if u.get("vendor_status") != "approved":
        raise HTTPException(status_code=403, detail="Your vendor account is not approved yet")
    tender = await db.tenders.find_one({"_id": ObjectId(payload.tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.get("status") != "open":
        raise HTTPException(status_code=400, detail="Tender is not open for bidding")

    # KZ license gate
    required = tender.get("required_licenses") or []
    if required:
        held = set((u.get("vendor_profile") or {}).get("kz_licenses") or [])
        missing = [r for r in required if r not in held]
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing required licenses: {', '.join(missing)}. Update your KYC to include them.")

    if await db.bids.find_one({"tender_id": payload.tender_id, "vendor_id": user["id"]}):
        raise HTTPException(status_code=400, detail="You have already submitted a bid for this tender")

    # EMD requirement gate
    if tender.get("emd_required"):
        if not (payload.emd_reference or payload.emd_payment_intent_id):
            raise HTTPException(status_code=400, detail="This tender requires an Earnest Money Deposit. Provide EMD reference or payment intent id.")

    doc = payload.model_dump()
    doc.update({
        "vendor_id": user["id"], "vendor_email": user.get("email"),
        "vendor_company": (u.get("vendor_profile") or {}).get("company_name"),
        "status": "submitted", "created_at": now_iso(),
        "emd_status": "held" if tender.get("emd_required") else None,
    })
    res = await db.bids.insert_one(doc)
    doc["_id"] = res.inserted_id
    if tender.get("created_by"):
        await create_notification(tender["created_by"], "New bid received",
                                  f"{doc['vendor_company'] or user['email']} bid on '{tender['title']}'",
                                  f"/tenders/{payload.tender_id}")
        if tender.get("created_by_email"):
            await send_email(tender["created_by_email"], f"PMC · New bid on {tender['title']}",
                             _email_wrap("New bid received",
                                         f"<p><strong>{doc['vendor_company'] or user['email']}</strong> submitted a bid:</p>"
                                         f"<p>Price: {payload.price_currency} {payload.price_amount:,.2f} · Delivery: {payload.delivery_days} days</p>",
                                         "Review bid", os.environ.get("FRONTEND_URL", "") + f"/tenders/{payload.tender_id}"))
    return _bid_out(doc)


@api.get("/bids")
async def list_bids(tender_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q: dict = {}
    tender_map: dict = {}
    if tender_id:
        q["tender_id"] = tender_id
        t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
        if not t:
            raise HTTPException(status_code=404, detail="Tender not found")
        tender_map[tender_id] = t
        if user["role"] == "buyer":
            if t.get("created_by") != user["id"]:
                raise HTTPException(status_code=403, detail="Not your tender")
        elif user["role"] == "vendor":
            q["vendor_id"] = user["id"]
    else:
        if user["role"] == "vendor":
            q["vendor_id"] = user["id"]
        elif user["role"] == "buyer":
            my_tender_ids = [str(t["_id"]) async for t in db.tenders.find({"created_by": user["id"]}, {"_id": 1})]
            q["tender_id"] = {"$in": my_tender_ids}
    out = []
    async for b in db.bids.find(q).sort("created_at", -1):
        tid = b.get("tender_id")
        t = tender_map.get(tid) or await db.tenders.find_one({"_id": ObjectId(tid)}) if tid else None
        if tid and t:
            tender_map[tid] = t
        if t and t.get("two_envelope"):
            is_owner = user["role"] == "vendor" and b.get("vendor_id") == user["id"]
            out.append(_mask_bid_for_two_envelope(b, t, user["role"], is_owner))
        else:
            out.append(_bid_out(b))
    return out


@api.post("/bids/{bid_id}/score")
async def score_bid(bid_id: str, payload: RfpScoreRequest, user: dict = Depends(require_role("buyer", "admin"))):
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    tender = await db.tenders.find_one({"_id": ObjectId(bid["tender_id"])})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and tender.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    if tender.get("document_type") != "rfp":
        raise HTTPException(status_code=400, detail="Scoring is only available for RFP")
    if tender.get("two_envelope") and not tender.get("technical_opened_at"):
        raise HTTPException(status_code=400, detail="Open technical envelopes before scoring.")

    criteria = tender.get("evaluation_criteria") or []
    # Compute weighted total: sum(weight * score / 100)
    weighted_total = 0.0
    for c in criteria:
        s = float(payload.scores.get(c["name"], 0) or 0)
        s = max(0.0, min(100.0, s))
        weighted_total += float(c.get("weight") or 0) * s / 100.0
    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {
        "rfp_scores": payload.scores,
        "rfp_notes": payload.notes,
        "rfp_weighted_total": round(weighted_total, 2),
        "scored_by": user["id"],
        "scored_at": now_iso(),
    }})
    return {"ok": True, "weighted_total": round(weighted_total, 2)}


@api.post("/bids/{bid_id}/award")
async def award_bid(bid_id: str, user: dict = Depends(require_role("buyer", "admin"))):
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    tender = await db.tenders.find_one({"_id": ObjectId(bid["tender_id"])})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and tender.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")

    # Two-envelope gate: commercial envelope must be opened and bid must be technically qualified.
    if tender.get("two_envelope"):
        if not tender.get("commercial_opened_at"):
            raise HTTPException(status_code=400, detail="Cannot award — commercial envelopes have not been opened yet.")
        if bid.get("technical_qualified") is not True:
            raise HTTPException(status_code=400, detail="Cannot award — this bid was not technically qualified.")

    await db.tenders.update_one({"_id": ObjectId(bid["tender_id"])},
                                {"$set": {"status": "awarded", "awarded_bid_id": bid_id}})
    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {"status": "awarded"}})
    await db.bids.update_many({"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}},
                              {"$set": {"status": "rejected"}})
    # EMD: mark losing bids' EMD as refundable (buyer/admin can then trigger refund via /emd-refund)
    if tender.get("emd_required"):
        await db.bids.update_many(
            {"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}, "emd_status": {"$nin": ["refunded", "forfeited", "refund_pending"]}},
            {"$set": {"emd_status": "refundable"}}
        )
        # Winner's EMD gets held (converts to performance security typically)
        await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {"emd_status": "held_as_security"}})
    await broker.broadcast({"type": "tender.updated", "payload": {"id": bid["tender_id"], "status": "awarded"}})

    # Notify + email winner
    await create_notification(bid["vendor_id"], "Congratulations — Bid awarded",
                              f"You have been awarded '{tender['title']}'.", f"/tenders/{bid['tender_id']}")
    if bid.get("vendor_email"):
        await send_email(bid["vendor_email"], f"PMC · Bid awarded — {tender['title']}",
                         _email_wrap("Bid awarded",
                                     f"<p>Congratulations — you have been awarded <strong>{tender['title']}</strong>.</p>"
                                     f"<p>PMC Managers will contact you with next steps.</p>",
                                     "View tender", os.environ.get("FRONTEND_URL", "") + f"/tenders/{bid['tender_id']}"))
    async for other in db.bids.find({"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}}):
        await create_notification(other["vendor_id"], "Bid outcome update",
                                  f"Your bid on '{tender['title']}' was not selected.", f"/tenders/{bid['tender_id']}")
        if other.get("vendor_email"):
            await send_email(other["vendor_email"], f"PMC · Bid outcome — {tender['title']}",
                             _email_wrap("Bid outcome",
                                         f"<p>Your bid on <strong>{tender['title']}</strong> was not selected on this occasion. We look forward to your future submissions.</p>"))
    return {"ok": True}


# ---------- Notifications ----------
@api.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    out = []
    async for n in db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).limit(100):
        n["id"] = str(n.pop("_id"))
        out.append(n)
    return out


@api.post("/notifications/mark-all-read")
async def mark_all_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


# ---------- File upload ----------
@api.post("/uploads")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB.")
    encoded = base64.b64encode(data).decode("utf-8")
    return {"name": file.filename, "type": file.content_type, "size": len(data),
            "data": f"data:{file.content_type};base64,{encoded}"}


# ---------- Payments (Stripe Flow B) ----------
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)


@api.post("/payments/checkout")
async def create_checkout(payload: CheckoutRequest, request: Request, user: dict = Depends(require_role("vendor"))):
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if u.get("registration_fee_paid"):
        raise HTTPException(status_code=400, detail="Registration fee already paid.")
    # Whitelist origin_url to FRONTEND_URL to prevent open-redirect via success_url
    allowed_origin = os.environ.get("FRONTEND_URL", "").rstrip("/")
    origin = payload.origin_url.rstrip("/")
    if allowed_origin and origin != allowed_origin:
        origin = allowed_origin
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"), webhook_url=webhook_url)
    success_url = f"{origin}/vendor/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/vendor/payment/cancel"
    req = CheckoutSessionRequest(
        amount=float(REGISTRATION_FEE_USD),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user["id"], "purpose": REGISTRATION_FEE_LOOKUP},
    )
    session: CheckoutSessionResponse = await checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "email": user["email"],
        "amount": float(REGISTRATION_FEE_USD),
        "currency": "usd",
        "purpose": REGISTRATION_FEE_LOOKUP,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


@api.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    record = await db.payment_transactions.find_one({"session_id": session_id})
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if record.get("payment_status") != "paid":
        try:
            checkout = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"), webhook_url="")
            status: CheckoutStatusResponse = await checkout.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}},
                )
                # Flip user's fee flag
                if record.get("user_id"):
                    await db.users.update_one({"_id": ObjectId(record["user_id"])}, {"$set": {"registration_fee_paid": True}})
                record = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception as e:
            logging.exception(f"stripe status check failed: {e}")
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"]}


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        checkout = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"), webhook_url="")
        result = await checkout.handle_webhook(body, sig)
        if getattr(result, "payment_status", None) == "paid":
            await db.payment_transactions.update_one(
                {"session_id": result.session_id, "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}},
            )
            meta = getattr(result, "metadata", {}) or {}
            uid = meta.get("user_id")
            if uid:
                await db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"registration_fee_paid": True}})
    except Exception as e:
        # Log but still ACK with 200 so Stripe doesn't retry forever on transient issues
        logging.exception(f"stripe webhook failed: {e}")
    return {"status": "ok"}


# ---------- Reference data ----------
@api.get("/reference/kz-licenses")
async def get_kz_licenses():
    return {"licenses": KZ_LICENSE_TYPES, "category_map": KZ_CATEGORY_LICENSE_MAP}


# ---------- Two-envelope endpoints (RFP only) ----------
async def _require_two_envelope_owner(tender_id: str, user: dict) -> dict:
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    if not t.get("two_envelope"):
        raise HTTPException(status_code=400, detail="This tender is not a two-envelope RFP")
    return t


@api.post("/tenders/{tender_id}/open-technical")
async def open_technical(tender_id: str, user: dict = Depends(require_role("buyer", "admin"))):
    t = await _require_two_envelope_owner(tender_id, user)
    if t.get("technical_opened_at"):
        return {"ok": True, "already_opened": True, "technical_opened_at": t["technical_opened_at"]}
    ts = now_iso()
    await db.tenders.update_one({"_id": ObjectId(tender_id)}, {"$set": {"technical_opened_at": ts}})
    await broker.broadcast({"type": "tender.updated", "payload": {"id": tender_id, "technical_opened_at": ts}})
    return {"ok": True, "technical_opened_at": ts}


@api.post("/tenders/{tender_id}/open-commercial")
async def open_commercial(tender_id: str, user: dict = Depends(require_role("buyer", "admin"))):
    t = await _require_two_envelope_owner(tender_id, user)
    if not t.get("technical_opened_at"):
        raise HTTPException(status_code=400, detail="Open technical envelopes first.")
    # Require at least one bid to have been qualified.
    qualified_count = await db.bids.count_documents({"tender_id": tender_id, "technical_qualified": True})
    if qualified_count == 0:
        raise HTTPException(status_code=400, detail="Qualify at least one bid before opening commercial envelopes.")
    if t.get("commercial_opened_at"):
        return {"ok": True, "already_opened": True, "commercial_opened_at": t["commercial_opened_at"]}
    ts = now_iso()
    await db.tenders.update_one({"_id": ObjectId(tender_id)}, {"$set": {"commercial_opened_at": ts}})
    await broker.broadcast({"type": "tender.updated", "payload": {"id": tender_id, "commercial_opened_at": ts}})
    return {"ok": True, "commercial_opened_at": ts, "qualified_bids": qualified_count}


class QualifyBidRequest(BaseModel):
    qualified: bool
    notes: Optional[str] = None


@api.post("/bids/{bid_id}/qualify")
async def qualify_bid(bid_id: str, payload: QualifyBidRequest, user: dict = Depends(require_role("buyer", "admin"))):
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    t = await db.tenders.find_one({"_id": ObjectId(bid["tender_id"])})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    if not t.get("two_envelope"):
        raise HTTPException(status_code=400, detail="Not a two-envelope RFP")
    if not t.get("technical_opened_at"):
        raise HTTPException(status_code=400, detail="Technical envelopes are not open yet.")
    if t.get("commercial_opened_at"):
        raise HTTPException(status_code=400, detail="Commercial envelopes already opened — qualification is locked.")
    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {
        "technical_qualified": bool(payload.qualified),
        "technical_qualified_at": now_iso(),
        "technical_qualified_notes": payload.notes,
    }})
    return {"ok": True, "qualified": bool(payload.qualified)}


# ---------- P1: Buyer Orgs & Departments ----------
def _org_out(doc: dict) -> dict:
    doc = dict(doc); doc["id"] = str(doc.pop("_id")); return doc


@api.post("/orgs")
async def create_org(payload: OrgIn, user: dict = Depends(require_role("admin"))):
    if await db.orgs.find_one({"code": payload.code}):
        raise HTTPException(status_code=400, detail="Org code already exists.")
    doc = payload.model_dump()
    doc.update({"created_by": user["id"], "created_at": now_iso()})
    res = await db.orgs.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _org_out(doc)


@api.get("/orgs")
async def list_orgs(user: dict = Depends(get_current_user)):
    return [_org_out(o) async for o in db.orgs.find({}).sort("name", 1)]


@api.post("/departments")
async def create_department(payload: DepartmentIn, user: dict = Depends(require_role("admin"))):
    org = await db.orgs.find_one({"_id": ObjectId(payload.org_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    if await db.departments.find_one({"org_id": payload.org_id, "code": payload.code}):
        raise HTTPException(status_code=400, detail="Department code already exists in this org.")
    # Validate thresholds
    for t in payload.approval_thresholds:
        if t.get("level") not in ("dept_head", "finance", "contracts_committee"):
            raise HTTPException(status_code=400, detail=f"Invalid approval level {t.get('level')}")
    doc = payload.model_dump()
    doc.update({"created_by": user["id"], "created_at": now_iso()})
    res = await db.departments.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _org_out(doc)


@api.get("/departments")
async def list_departments(org_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"org_id": org_id} if org_id else {}
    return [_org_out(d) async for d in db.departments.find(q).sort("name", 1)]


@api.post("/users/me/department")
async def assign_my_department(payload: DepartmentAssignRequest, user: dict = Depends(require_role("buyer", "admin"))):
    dept = await db.departments.find_one({"_id": ObjectId(payload.department_id)})
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.users.update_one({"_id": ObjectId(user["id"])},
                              {"$set": {"department_id": payload.department_id, "org_id": dept.get("org_id")}})
    return {"ok": True, "department_id": payload.department_id, "org_id": dept.get("org_id")}


# ---------- P1: Tender approval workflow ----------
@api.post("/tenders/{tender_id}/approve")
async def approve_tender(tender_id: str, payload: TenderApprovalDecision, user: dict = Depends(require_role("admin"))):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if t.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Tender is not awaiting approval")
    chain = t.get("approval_chain") or []
    # Find first undecided step
    idx = next((i for i, s in enumerate(chain) if not s.get("decision")), -1)
    if chain and idx == -1:
        raise HTTPException(status_code=400, detail="Approval chain already complete")
    ts = now_iso()
    updates: dict = {}
    if chain:
        chain[idx].update({
            "decision": "approved" if payload.approved else "rejected",
            "approver_user_id": user["id"],
            "approver_name": user.get("name"),
            "decided_at": ts,
            "notes": payload.notes,
        })
        updates["approval_chain"] = chain
        remaining = [s for s in chain if not s.get("decision")]
        if not payload.approved:
            updates["approval_state"] = "rejected"
            updates["status"] = "rejected"
        elif not remaining:
            updates["approval_state"] = "approved"
            updates["status"] = "open"
    else:
        # No chain — simple flat approve
        if not payload.approved:
            updates["approval_state"] = "rejected"; updates["status"] = "rejected"
        else:
            updates["approval_state"] = "approved"; updates["status"] = "open"
    await db.tenders.update_one({"_id": ObjectId(tender_id)}, {"$set": updates})
    # Broadcast if opened
    if updates.get("status") == "open":
        await broker.broadcast({"type": "tender.created", "payload": {
            "id": tender_id,
            "title": t.get("title"),
            "description": (t.get("description") or "")[:220],
            "document_type": t.get("document_type") or "tender",
            "category": t.get("category"),
            "status": "open",
            "budget_currency": t.get("budget_currency"),
            "budget_amount": t.get("budget_amount"),
            "submission_deadline": t.get("submission_deadline"),
            "delivery_country": t.get("delivery_country"),
            "created_by_name": t.get("created_by_name"),
            "created_at": t.get("created_at"),
        }})
    return {"ok": True, "status": updates.get("status"), "approval_state": updates.get("approval_state")}


# ---------- P1: Q&A / Clarifications ----------
def _qa_out(doc: dict, viewer_role: str, viewer_id: str) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    # Anonymize vendor identity unless viewer is buyer/admin OR author themselves
    is_author = d.get("asked_by_user_id") == viewer_id
    if viewer_role not in ("buyer", "admin") and not is_author:
        d.pop("asked_by_user_id", None)
        d.pop("asked_by_name", None)
    return d


@api.post("/tenders/{tender_id}/questions")
async def ask_question(tender_id: str, payload: QuestionIn, user: dict = Depends(get_current_user)):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    doc = {
        "tender_id": tender_id,
        "question": payload.question,
        "anonymous": payload.anonymous,
        "asked_by_user_id": user["id"],
        "asked_by_name": user.get("name"),
        "asked_by_role": user["role"],
        "answer": None,
        "answered_by": None,
        "answered_at": None,
        "published": False,  # only visible publicly after buyer answers
        "created_at": now_iso(),
    }
    res = await db.tender_questions.insert_one(doc)
    doc["_id"] = res.inserted_id
    # Notify buyer/admin owner
    if t.get("created_by"):
        await create_notification(t["created_by"], "New tender question",
                                  f"A vendor asked a question on '{t['title']}'.",
                                  f"/tenders/{tender_id}")
    return _qa_out(doc, user["role"], user["id"])


@api.get("/tenders/{tender_id}/questions")
async def list_questions(tender_id: str, user: dict = Depends(get_current_user)):
    q: dict = {"tender_id": tender_id}
    # Vendors see only published (answered) questions + their own
    if user["role"] == "vendor":
        q = {"$and": [{"tender_id": tender_id}, {"$or": [{"published": True}, {"asked_by_user_id": user["id"]}]}]}
    return [_qa_out(d, user["role"], user["id"]) async for d in db.tender_questions.find(q).sort("created_at", -1)]


@api.post("/questions/{qid}/answer")
async def answer_question(qid: str, payload: AnswerIn, user: dict = Depends(require_role("buyer", "admin"))):
    q = await db.tender_questions.find_one({"_id": ObjectId(qid)})
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    t = await db.tenders.find_one({"_id": ObjectId(q["tender_id"])})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    await db.tender_questions.update_one({"_id": ObjectId(qid)}, {"$set": {
        "answer": payload.answer,
        "answered_by": user["id"],
        "answered_by_name": user.get("name"),
        "answered_at": now_iso(),
        "published": True,
    }})
    # Broadcast an update (SSE could carry Q&A later)
    # Notify original asker
    if q.get("asked_by_user_id"):
        await create_notification(q["asked_by_user_id"], "Your question was answered",
                                  f"'{t['title']}' — see the answer.", f"/tenders/{q['tender_id']}")
    return {"ok": True}


@api.post("/tenders/{tender_id}/addenda")
async def publish_addendum(tender_id: str, payload: AddendumIn, user: dict = Depends(require_role("buyer", "admin"))):
    t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    addendum = {
        "id": uuid.uuid4().hex,
        "title": payload.title,
        "body": payload.body,
        "published_by": user["id"],
        "published_by_name": user.get("name"),
        "published_at": now_iso(),
    }
    await db.tenders.update_one({"_id": ObjectId(tender_id)}, {"$push": {"addenda": addendum}})
    # Notify all vendors who have already submitted bids on this tender
    async for b in db.bids.find({"tender_id": tender_id}, {"vendor_id": 1, "vendor_email": 1}):
        await create_notification(b["vendor_id"], "Addendum published",
                                  f"'{t['title']}' — {payload.title}", f"/tenders/{tender_id}")
    return {"ok": True, "addendum": addendum}


# ---------- P1: EMD refund ----------
@api.post("/bids/{bid_id}/emd-refund")
async def emd_refund(bid_id: str, payload: EmdRefundIn, user: dict = Depends(require_role("buyer", "admin"))):
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    t = await db.tenders.find_one({"_id": ObjectId(bid["tender_id"])})
    if not t:
        raise HTTPException(status_code=404, detail="Tender not found")
    if user["role"] != "admin" and t.get("created_by") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your tender")
    if not t.get("emd_required"):
        raise HTTPException(status_code=400, detail="EMD not required on this tender")
    current = bid.get("emd_status") or "held"
    if current in ("refunded", "forfeited"):
        raise HTTPException(status_code=400, detail=f"EMD already {current}")

    new_status = "forfeited" if payload.forfeit else "refunded"
    stripe_refund_id = None
    # Attempt Stripe refund if we have a payment_intent_id and it's an actual refund
    if not payload.forfeit and bid.get("emd_payment_intent_id"):
        try:
            refund = stripe.Refund.create(payment_intent=bid["emd_payment_intent_id"])
            stripe_refund_id = refund.get("id")
        except Exception as e:
            logging.warning(f"Stripe EMD refund failed for bid {bid_id}: {e}")
            # Continue — mark as refund_pending so ops can retry
            new_status = "refund_pending"

    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {
        "emd_status": new_status,
        "emd_refund_id": stripe_refund_id,
        "emd_refund_notes": payload.notes,
        "emd_refunded_at": now_iso(),
    }})
    await create_notification(bid["vendor_id"], f"EMD {new_status}",
                              f"Your EMD for '{t['title']}' has been {new_status}.",
                              f"/tenders/{bid['tender_id']}")
    return {"ok": True, "emd_status": new_status, "stripe_refund_id": stripe_refund_id}



# ---------- SSE broadcaster ----------
class _SseBroker:
    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self.subscribers.remove(q)
        except ValueError:
            pass

    async def broadcast(self, event: dict) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


broker = _SseBroker()


# ---------- Public ----------
@api.get("/public/stats")
async def public_stats():
    return {
        "tenders_open": await db.tenders.count_documents({"status": "open"}),
        "vendors_approved": await db.users.count_documents({"role": "vendor", "vendor_status": "approved"}),
        "total_tenders": await db.tenders.count_documents({}),
    }


@api.get("/feed/tenders")
async def feed_tenders(
    limit: int = 30,
    document_type: Optional[str] = None,
    country: Optional[str] = None,
    unread_only: bool = False,
    user: dict = Depends(get_current_user),
):
    """Real-time cross-role feed of the latest tenders (any doc type). Only open + awarded shown."""
    q: dict = {"status": {"$in": ["open", "awarded"]}}
    if document_type and document_type in ("rfp", "rfq", "tender"):
        q["document_type"] = document_type
    if country:
        q["delivery_country"] = country.upper()
    limit = max(1, min(int(limit), 100))
    u = await db.users.find_one({"_id": ObjectId(user["id"])}, {"read_tender_ids": 1})
    read_set = set((u or {}).get("read_tender_ids") or [])
    out = []
    async for t in db.tenders.find(q).sort("created_at", -1).limit(limit * 3 if unread_only else limit):
        tid = str(t["_id"])
        is_unread = tid not in read_set
        if unread_only and not is_unread:
            continue
        out.append({
            "id": tid,
            "title": t.get("title"),
            "description": (t.get("description") or "")[:220],
            "document_type": t.get("document_type") or "tender",
            "category": t.get("category"),
            "status": t.get("status"),
            "budget_currency": t.get("budget_currency"),
            "budget_amount": t.get("budget_amount"),
            "submission_deadline": t.get("submission_deadline"),
            "delivery_country": t.get("delivery_country"),
            "created_by_name": t.get("created_by_name"),
            "created_at": t.get("created_at"),
            "unread": is_unread,
        })
        if len(out) >= limit:
            break
    return out


@api.get("/feed/unread-count")
async def feed_unread_count(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"_id": ObjectId(user["id"])}, {"read_tender_ids": 1})
    read_set = set((u or {}).get("read_tender_ids") or [])
    total_open = await db.tenders.count_documents({"status": {"$in": ["open", "awarded"]}})
    # Count how many tender ids exist that are NOT read
    unread = 0
    if total_open:
        async for t in db.tenders.find({"status": {"$in": ["open", "awarded"]}}, {"_id": 1}):
            if str(t["_id"]) not in read_set:
                unread += 1
    return {"unread": unread, "total": total_open}


@api.post("/feed/mark-read/{tender_id}")
async def feed_mark_read(tender_id: str, user: dict = Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$addToSet": {"read_tender_ids": tender_id}})
    return {"ok": True}


@api.post("/feed/mark-all-read")
async def feed_mark_all_read(user: dict = Depends(get_current_user)):
    ids = [str(t["_id"]) async for t in db.tenders.find({"status": {"$in": ["open", "awarded"]}}, {"_id": 1})]
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$addToSet": {"read_tender_ids": {"$each": ids}}})
    return {"ok": True, "marked": len(ids)}


@api.get("/feed/stream")
async def feed_stream(request: Request):
    """Server-Sent Events stream for real-time tender feed updates."""
    # Auth from cookie or query token (EventSource can't set headers reliably)
    token = request.cookies.get("access_token") or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    q = await broker.subscribe()

    async def gen():
        try:
            # Initial hello
            yield f"event: connected\ndata: {_json.dumps({'user_id': user_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"event: {ev.get('type', 'message')}\ndata: {_json.dumps(ev.get('payload'))}\n\n"
                except asyncio.TimeoutError:
                    # keep-alive
                    yield ": keep-alive\n\n"
        finally:
            broker.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@api.get("/health")
async def health():
    return {"ok": True, "service": "pmc-tender-api"}


# ---------- Startup ----------
async def seed_admin_and_demo():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@pmcmanagers.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email, "password_hash": hash_password(admin_password),
            "name": "PMC Administrator", "role": "admin", "auth_provider": "password",
            "vendor_status": None, "vendor_profile": None, "registration_fee_paid": False,
            "created_at": now_iso(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

    for extra in [
        {"email": "buyer@pmcmanagers.com", "password": "Buyer@123", "name": "Sarah Buyer", "role": "buyer"},
        {"email": "vendor@example.com", "password": "Vendor@123", "name": "Global Supplies Inc.", "role": "vendor"},
    ]:
        if not await db.users.find_one({"email": extra["email"]}):
            await db.users.insert_one({
                "email": extra["email"], "password_hash": hash_password(extra["password"]),
                "name": extra["name"], "role": extra["role"], "auth_provider": "password",
                "vendor_status": "pending" if extra["role"] == "vendor" else None,
                "vendor_profile": None, "registration_fee_paid": False,
                "created_at": now_iso(),
            })

    # Seed default Buyer Org + Departments for P1 approval workflow
    org = await db.orgs.find_one({"code": "PMC-GLOBAL"})
    if not org:
        r = await db.orgs.insert_one({
            "name": "PMC Managers Global", "code": "PMC-GLOBAL", "country": "KZ",
            "description": "Default org for demo tenders.",
            "created_by": None, "created_at": now_iso(),
        })
        org_id = str(r.inserted_id)
    else:
        org_id = str(org["_id"])

    default_depts = [
        {"code": "MED", "name": "Medical Facilities",
         "approval_thresholds": [
             {"threshold": 10000, "level": "dept_head"},
             {"threshold": 100000, "level": "contracts_committee"},
         ]},
        {"code": "GEN", "name": "General Procurement",
         "approval_thresholds": [
             {"threshold": 50000, "level": "dept_head"},
             {"threshold": 250000, "level": "contracts_committee"},
         ]},
    ]
    for d in default_depts:
        if not await db.departments.find_one({"org_id": org_id, "code": d["code"]}):
            await db.departments.insert_one({
                "org_id": org_id, "code": d["code"], "name": d["name"],
                "head_user_id": None, "approval_thresholds": d["approval_thresholds"],
                "created_by": None, "created_at": now_iso(),
            })


@app.on_event("startup")
async def on_start():
    await db.users.create_index("email", unique=True)
    await db.tenders.create_index("created_by")
    await db.bids.create_index([("tender_id", 1), ("vendor_id", 1)], unique=True)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await seed_admin_and_demo()


@app.on_event("shutdown")
async def on_stop():
    client.close()


# ---------- Register router & CORS ----------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
