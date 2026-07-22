from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
import base64
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from starlette.middleware.cors import CORSMiddleware

# ---------- Constants ----------
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 24  # 1 day for dev convenience
REFRESH_TOKEN_TTL_DAYS = 7
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per file

# ---------- Mongo ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

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
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MIN),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "type": "refresh",
    }
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
        "user_id": user_id,
        "title": title,
        "body": body,
        "link": link,
        "read": False,
        "created_at": now_iso(),
    })


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


class VendorProfileIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Section A: Identity
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
    # Primary contact
    contact_name: str
    contact_title: str
    contact_office_phone: str
    contact_mobile: Optional[str] = None
    contact_email: EmailStr
    # Authorized signatory
    signatory_name: str
    signatory_title: str
    signatory_contact: Optional[str] = None
    # Bank
    bank_name: str
    bank_branch: Optional[str] = None
    bank_account_number: str
    bank_swift: str
    bank_address: Optional[str] = None
    # Section B
    primary_sector: str
    business_description: str
    operating_regions: List[str] = []
    business_categories: List[str] = []
    turnover_year1: Optional[float] = None
    turnover_year2: Optional[float] = None
    turnover_year3: Optional[float] = None
    turnover_currency: Optional[str] = "USD"
    previous_projects: List[dict] = []  # [{name, client, value, currency, period}]
    references: List[dict] = []  # [{name, position, phone, email, company}]
    iso_certifications: Optional[str] = None
    licenses_permits: Optional[str] = None
    insurance_details: Optional[str] = None
    litigation_history: Optional[str] = None
    # Section C: documents
    documents: List[dict] = []
    # Section D: Declarations (all must be True)
    decl_conflict_of_interest: bool = False
    decl_integrity: bool = False
    decl_accuracy: bool = False
    decl_data_consent: bool = False
    decl_fee: bool = False
    decl_notification: bool = False
    # Section E: Signature
    signature_name: Optional[str] = None
    signature_title: Optional[str] = None
    signature_date: Optional[str] = None
    signature_company_seal: Optional[str] = None  # optional data-url stamp


class TenderIn(BaseModel):
    title: str
    description: str
    category: str
    budget_currency: str = "USD"
    budget_amount: Optional[float] = None
    submission_deadline: str  # ISO datetime
    delivery_location: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    attachments: List[dict] = []


class BidIn(BaseModel):
    tender_id: str
    price_currency: str = "USD"
    price_amount: float
    delivery_days: int
    proposal: str
    attachments: List[dict] = []


# ---------- Auth ----------
@api.post("/auth/register")
async def register(payload: RegisterUserRequest, response: Response):
    email = payload.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.role == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot self-register")

    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": payload.role,
        "vendor_status": "pending" if payload.role == "vendor" else None,
        "vendor_profile": None,
        "created_at": now_iso(),
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    access = create_access_token(user_id, email, payload.role)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    doc["_id"] = result.inserted_id
    return _serialize_user(doc)


@api.post("/auth/login")
async def login(payload: LoginRequest, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
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


# ---------- Vendor profile ----------
@api.post("/vendor/profile")
async def upsert_vendor_profile(payload: VendorProfileIn, user: dict = Depends(require_role("vendor"))):
    profile = payload.model_dump()
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"vendor_profile": profile, "vendor_status": "pending", "updated_at": now_iso()}},
    )
    # Notify admins
    async for admin in db.users.find({"role": "admin"}):
        await create_notification(
            str(admin["_id"]),
            "New vendor pending approval",
            f"{profile['company_name']} ({user['email']}) submitted their vendor profile.",
            "/admin/vendors",
        )
    return {"ok": True, "vendor_status": "pending"}


@api.get("/vendor/profile")
async def get_vendor_profile(user: dict = Depends(require_role("vendor"))):
    doc = await db.users.find_one({"_id": ObjectId(user["id"])}, {"vendor_profile": 1, "vendor_status": 1})
    return {"vendor_profile": doc.get("vendor_profile"), "vendor_status": doc.get("vendor_status")}


# ---------- Admin: vendor mgmt ----------
@api.get("/admin/vendors")
async def list_vendors(user: dict = Depends(require_role("admin"))):
    cursor = db.users.find({"role": "vendor"}).sort("created_at", -1)
    out = []
    async for u in cursor:
        out.append(_serialize_user(u))
    return out


@api.post("/admin/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user: dict = Depends(require_role("admin"))):
    r = await db.users.update_one({"_id": ObjectId(vendor_id), "role": "vendor"}, {"$set": {"vendor_status": "approved"}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await create_notification(vendor_id, "Vendor account approved", "Your PMC vendor account has been approved. You can now submit bids.", "/tenders")
    return {"ok": True}


@api.post("/admin/vendors/{vendor_id}/reject")
async def reject_vendor(vendor_id: str, user: dict = Depends(require_role("admin"))):
    r = await db.users.update_one({"_id": ObjectId(vendor_id), "role": "vendor"}, {"$set": {"vendor_status": "rejected"}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await create_notification(vendor_id, "Vendor application update", "Your vendor application was not approved. Please contact support.", "/vendor")
    return {"ok": True}


@api.get("/admin/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    out = []
    async for u in db.users.find().sort("created_at", -1):
        out.append(_serialize_user(u))
    return out


@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    users_count = await db.users.count_documents({})
    vendors_pending = await db.users.count_documents({"role": "vendor", "vendor_status": "pending"})
    vendors_approved = await db.users.count_documents({"role": "vendor", "vendor_status": "approved"})
    tenders_open = await db.tenders.count_documents({"status": "open"})
    tenders_total = await db.tenders.count_documents({})
    bids_total = await db.bids.count_documents({})
    return {
        "users": users_count,
        "vendors_pending": vendors_pending,
        "vendors_approved": vendors_approved,
        "tenders_open": tenders_open,
        "tenders_total": tenders_total,
        "bids_total": bids_total,
    }


# ---------- Tenders ----------
def _tender_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


@api.post("/tenders")
async def create_tender(payload: TenderIn, user: dict = Depends(require_role("buyer", "admin"))):
    doc = payload.model_dump()
    doc.update({
        "status": "open",
        "created_by": user["id"],
        "created_by_name": user.get("name"),
        "created_by_email": user.get("email"),
        "created_at": now_iso(),
        "awarded_bid_id": None,
    })
    res = await db.tenders.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _tender_out(doc)


@api.get("/tenders")
async def list_tenders(mine: bool = False, user: dict = Depends(get_current_user)):
    q: dict = {}
    if mine and user["role"] in ("buyer", "admin"):
        q["created_by"] = user["id"]
    elif user["role"] == "vendor":
        # vendors only see open tenders in the general list
        q["status"] = "open"
    out = []
    async for t in db.tenders.find(q).sort("created_at", -1):
        out.append(_tender_out(t))
    return out


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


# ---------- Bids ----------
def _bid_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


@api.post("/bids")
async def create_bid(payload: BidIn, user: dict = Depends(require_role("vendor"))):
    # Vendor must be approved
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if u.get("vendor_status") != "approved":
        raise HTTPException(status_code=403, detail="Your vendor account is not approved yet")
    tender = await db.tenders.find_one({"_id": ObjectId(payload.tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.get("status") != "open":
        raise HTTPException(status_code=400, detail="Tender is not open for bidding")

    existing = await db.bids.find_one({"tender_id": payload.tender_id, "vendor_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted a bid for this tender")

    doc = payload.model_dump()
    doc.update({
        "vendor_id": user["id"],
        "vendor_email": user.get("email"),
        "vendor_company": (u.get("vendor_profile") or {}).get("company_name"),
        "status": "submitted",
        "created_at": now_iso(),
    })
    res = await db.bids.insert_one(doc)
    # Notify buyer
    if tender.get("created_by"):
        await create_notification(
            tender["created_by"],
            "New bid received",
            f"{doc['vendor_company'] or user['email']} submitted a bid on '{tender['title']}'",
            f"/tenders/{payload.tender_id}",
        )
    doc["_id"] = res.inserted_id
    return _bid_out(doc)


@api.get("/bids")
async def list_bids(tender_id: Optional[str] = None, mine: bool = False, user: dict = Depends(get_current_user)):
    q: dict = {}
    if tender_id:
        q["tender_id"] = tender_id
        # If buyer, must own tender OR admin
        if user["role"] == "buyer":
            t = await db.tenders.find_one({"_id": ObjectId(tender_id)})
            if not t or t.get("created_by") != user["id"]:
                raise HTTPException(status_code=403, detail="Not your tender")
        elif user["role"] == "vendor":
            q["vendor_id"] = user["id"]
    else:
        if user["role"] == "vendor" or mine:
            q["vendor_id"] = user["id"] if user["role"] == "vendor" else None
        if user["role"] == "buyer":
            # buyer sees bids on their tenders
            my_tender_ids = [str(t["_id"]) async for t in db.tenders.find({"created_by": user["id"]}, {"_id": 1})]
            q["tender_id"] = {"$in": my_tender_ids}
    out = []
    async for b in db.bids.find(q).sort("created_at", -1):
        out.append(_bid_out(b))
    return out


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

    await db.tenders.update_one({"_id": ObjectId(bid["tender_id"])}, {"$set": {"status": "awarded", "awarded_bid_id": bid_id}})
    await db.bids.update_one({"_id": ObjectId(bid_id)}, {"$set": {"status": "awarded"}})
    await db.bids.update_many(
        {"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}},
        {"$set": {"status": "rejected"}},
    )

    # Notify winner and losers
    await create_notification(bid["vendor_id"], "Congratulations - Bid awarded", f"You have been awarded the tender '{tender['title']}'.", f"/tenders/{bid['tender_id']}")
    async for other in db.bids.find({"tender_id": bid["tender_id"], "_id": {"$ne": ObjectId(bid_id)}}):
        await create_notification(other["vendor_id"], "Bid outcome update", f"Your bid on '{tender['title']}' was not selected.", f"/tenders/{bid['tender_id']}")
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


# ---------- File upload (base64 stored) ----------
@api.post("/uploads")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB.")
    encoded = base64.b64encode(data).decode("utf-8")
    return {
        "name": file.filename,
        "type": file.content_type,
        "size": len(data),
        "data": f"data:{file.content_type};base64,{encoded}",
    }


# ---------- Public ----------
@api.get("/public/stats")
async def public_stats():
    tenders_open = await db.tenders.count_documents({"status": "open"})
    vendors_approved = await db.users.count_documents({"role": "vendor", "vendor_status": "approved"})
    total_tenders = await db.tenders.count_documents({})
    return {"tenders_open": tenders_open, "vendors_approved": vendors_approved, "total_tenders": total_tenders}


@api.get("/health")
async def health():
    return {"ok": True, "service": "pmc-tender-api"}


# ---------- Startup ----------
async def seed_admin_and_demo():
    # Admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@pmcmanagers.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "PMC Administrator",
            "role": "admin",
            "vendor_status": None,
            "vendor_profile": None,
            "created_at": now_iso(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

    # Demo buyer
    buyer_email = "buyer@pmcmanagers.com"
    if not await db.users.find_one({"email": buyer_email}):
        await db.users.insert_one({
            "email": buyer_email,
            "password_hash": hash_password("Buyer@123"),
            "name": "Sarah Buyer",
            "role": "buyer",
            "vendor_status": None,
            "vendor_profile": None,
            "created_at": now_iso(),
        })

    # Demo vendor (unapproved)
    vendor_email = "vendor@example.com"
    if not await db.users.find_one({"email": vendor_email}):
        await db.users.insert_one({
            "email": vendor_email,
            "password_hash": hash_password("Vendor@123"),
            "name": "Global Supplies Inc.",
            "role": "vendor",
            "vendor_status": "pending",
            "vendor_profile": None,
            "created_at": now_iso(),
        })


@app.on_event("startup")
async def on_start():
    await db.users.create_index("email", unique=True)
    await db.tenders.create_index("created_by")
    await db.bids.create_index([("tender_id", 1), ("vendor_id", 1)], unique=True)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
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
