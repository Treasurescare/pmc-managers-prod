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
from fastapi.responses import StreamingResponse
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
    title: str
    description: str
    category: str
    budget_currency: str = "USD"
    budget_amount: Optional[float] = None
    submission_deadline: str
    delivery_location: Optional[str] = None
    delivery_country: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    required_licenses: List[str] = []  # KZ license types required
    attachments: List[dict] = []


class BidIn(BaseModel):
    tender_id: str
    price_currency: str = "USD"
    price_amount: float
    delivery_days: int
    proposal: str
    attachments: List[dict] = []


class CheckoutRequest(BaseModel):
    origin_url: str


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
    # Auto-attach required KZ licenses from map if delivery_country=KZ
    if (doc.get("delivery_country") or "").upper() == "KZ":
        auto = KZ_CATEGORY_LICENSE_MAP.get(doc["category"], [])
        merged = list({*doc.get("required_licenses", []), *auto})
        doc["required_licenses"] = merged
    doc.update({
        "status": "open", "created_by": user["id"],
        "created_by_name": user.get("name"), "created_by_email": user.get("email"),
        "created_at": now_iso(), "awarded_bid_id": None,
    })
    res = await db.tenders.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Notify approved vendors matching category / no filter — quick MVP fan-out
    async for v in db.users.find({"role": "vendor", "vendor_status": "approved"}):
        await create_notification(str(v["_id"]), "New tender published",
                                  f"{doc['title']} — {doc['category']}", f"/tenders/{res.inserted_id}")
        # Best-effort email (don't await queue for very long)
        try:
            await send_email(v["email"], f"PMC · New tender: {doc['title']}",
                             _email_wrap(doc["title"],
                                         f"<p>A new tender has been published on the PMC Global Tender Board.</p>"
                                         f"<p><strong>Category:</strong> {doc['category']}<br/>"
                                         f"<strong>Deadline:</strong> {doc['submission_deadline']}</p>",
                                         "View tender", os.environ.get("FRONTEND_URL", "") + f"/tenders/{res.inserted_id}"))
        except Exception:
            pass
    return _tender_out(doc)


@api.get("/tenders")
async def list_tenders(mine: bool = False, user: dict = Depends(get_current_user)):
    q: dict = {}
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

    doc = payload.model_dump()
    doc.update({
        "vendor_id": user["id"], "vendor_email": user.get("email"),
        "vendor_company": (u.get("vendor_profile") or {}).get("company_name"),
        "status": "submitted", "created_at": now_iso(),
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
    if tender_id:
        q["tender_id"] = tender_id
        if user["role"] == "buyer":
            t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
            if not t or t.get("created_by") != user["id"]:
                raise HTTPException(status_code=403, detail="Not your tender")
        elif user["role"] == "vendor":
            q["vendor_id"] = user["id"]
    else:
        if user["role"] == "vendor":
            q["vendor_id"] = user["id"]
        elif user["role"] == "buyer":
            my_tender_ids = [str(t["_id"]) async for t in db.tenders.find({"created_by": user["id"]}, {"_id": 1})]
            q["tender_id"] = {"$in": my_tender_ids}
    return [_bid_out(b) async for b in db.bids.find(q).sort("created_at", -1)]


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

    await db.tenders.update_one({"_id": ObjectId(bid["tender_id"])},
                                {"$set": {"status": "awarded", "awarded_bid_id": bid_id}})
    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {"status": "awarded"}})
    await db.bids.update_many({"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}},
                              {"$set": {"status": "rejected"}})

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
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"), webhook_url=webhook_url)
    success_url = f"{payload.origin_url}/vendor/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{payload.origin_url}/vendor/payment/cancel"
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
        logging.exception(f"stripe webhook failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    return {"status": "ok"}


# ---------- Reference data ----------
@api.get("/reference/kz-licenses")
async def get_kz_licenses():
    return {"licenses": KZ_LICENSE_TYPES, "category_map": KZ_CATEGORY_LICENSE_MAP}


# ---------- Public ----------
@api.get("/public/stats")
async def public_stats():
    return {
        "tenders_open": await db.tenders.count_documents({"status": "open"}),
        "vendors_approved": await db.users.count_documents({"role": "vendor", "vendor_status": "approved"}),
        "total_tenders": await db.tenders.count_documents({}),
    }


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
