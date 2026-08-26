"""Admin-initiated vendor onboarding.

Flow:
1. Admin creates a stub vendor record via POST /vendors/invite (email + optional company_name + optional prefilled_registration).
2. Backend generates a magic token, emails the vendor a link to `/vendor/verify/{token}`.
3. Vendor visits the link, sets a password, and lands on the vendor portal.
4. If the admin uploaded a completed registration form on their behalf, it's attached to the vendor's profile.

The admin can also upload a *template* blank registration form which vendors can download for reference.
"""
import secrets
import base64
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

import config
from db import db, next_sequence
from models.base import BaseDocument, now_iso
from security import require_role, hash_password, new_magic_token
from emails import send_email, wrap
from audit import audit_log

router = APIRouter(prefix="/api/v1/vendors", tags=["vendor-invites"])


class VendorInviteIn(BaseModel):
    email: EmailStr
    company_name: Optional[str] = None
    country: str = "KZ"
    contact_name: Optional[str] = None
    prefilled_registration: Optional[dict] = None  # { section_a: {...}, section_b: {...}, ... }


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    d.pop("password_hash", None)
    d.pop("magic_token", None)
    return d


@router.post("/invite")
async def invite_vendor(payload: VendorInviteIn, admin=Depends(require_role("admin"))):
    """Admin creates a vendor stub and emails them a verify+set-password link."""
    existing = await db.vendors.find_one({"email": payload.email.lower()})
    if existing and existing.get("is_active"):
        raise HTTPException(status_code=409, detail="Vendor with this email already active")

    token = new_magic_token()
    seq = await next_sequence("vendor_seq")
    vendor_ref = f"PMC-SUP-{seq:06d}"
    doc = {
        "vendor_ref": vendor_ref,
        "email": payload.email.lower(),
        "company_name": payload.company_name,
        "country": payload.country,
        "contact_name": payload.contact_name,
        "profile": payload.prefilled_registration or {},
        "tenant_id": admin["tenant_id"],
        "invited_by": admin["id"],
        "invited_at": now_iso(),
        "email_verified": False,
        "magic_token": token,
        "is_active": False,   # only becomes true after email verify + password set
        "created_at": now_iso(),
    }
    if existing:
        await db.vendors.update_one({"_id": existing["_id"]}, {"$set": doc})
    else:
        await db.vendors.insert_one(doc)

    verify_url = f"{config.FRONTEND_URL}/vendor/verify/{token}"
    asyncio.create_task(send_email(
        payload.email, "PMC Managers — You've been invited as a vendor",
        wrap(f"Welcome to PMC · {vendor_ref}",
             f"<p>The PMC Managers procurement team has pre-registered your company "
             f"<strong>{payload.company_name or payload.email}</strong> as a vendor "
             f"on the Global Tender Board.</p>"
             f"<p>To activate your account, please verify your email and set a password:</p>",
             "Verify email & set password", verify_url)))
    await audit_log("vendor.invite", admin, "vendor", vendor_ref,
                    {"email": payload.email, "company_name": payload.company_name})
    return {"vendor_ref": vendor_ref, "email": payload.email, "verify_url": verify_url}


class BulkInviteIn(BaseModel):
    csv_text: str  # newline-separated "email,company_name,country,contact_name"


@router.post("/invite-bulk")
async def invite_vendors_bulk(payload: BulkInviteIn, admin=Depends(require_role("admin"))):
    """Parse a CSV of vendor rows and invite each one. Returns per-row status."""
    import csv, io
    results = []
    reader = csv.DictReader(io.StringIO(payload.csv_text))
    if not reader.fieldnames or "email" not in [f.lower().strip() for f in reader.fieldnames]:
        raise HTTPException(status_code=400,
                             detail="CSV must have header row with at least an 'email' column")
    header_map = {name.lower().strip(): name for name in reader.fieldnames}
    def col(row, k):
        real = header_map.get(k)
        return (row.get(real) or "").strip() if real else ""
    for i, row in enumerate(reader, start=2):
        email = col(row, "email").lower()
        if not email or "@" not in email:
            results.append({"row": i, "email": email, "status": "skipped", "reason": "invalid email"})
            continue
        existing = await db.vendors.find_one({"email": email})
        if existing and existing.get("is_active"):
            results.append({"row": i, "email": email, "status": "skipped", "reason": "already active"})
            continue
        token = new_magic_token()
        seq = await next_sequence("vendor_seq")
        vendor_ref = f"PMC-SUP-{seq:06d}"
        doc = {
            "vendor_ref": vendor_ref, "email": email,
            "company_name": col(row, "company_name") or col(row, "company") or None,
            "country": col(row, "country") or "KZ",
            "contact_name": col(row, "contact_name") or None,
            "tenant_id": admin["tenant_id"],
            "invited_by": admin["id"], "invited_at": now_iso(),
            "email_verified": False, "magic_token": token,
            "is_active": False, "created_at": now_iso(),
        }
        if existing:
            await db.vendors.update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            await db.vendors.insert_one(doc)
        verify_url = f"{config.FRONTEND_URL}/vendor/verify/{token}"
        asyncio.create_task(send_email(
            email, "PMC Managers — You've been invited as a vendor",
            wrap(f"Welcome to PMC · {vendor_ref}",
                 f"<p>You've been pre-registered as a vendor. Please verify your email and set a password.</p>",
                 "Verify email & set password", verify_url)))
        results.append({"row": i, "email": email, "status": "invited", "vendor_ref": vendor_ref})
    await audit_log("vendor.invite_bulk", admin, "vendor", "csv",
                    {"total": len(results),
                     "invited": sum(1 for r in results if r["status"] == "invited")})
    return {"total": len(results),
            "invited": sum(1 for r in results if r["status"] == "invited"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "results": results}


class VerifySetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.get("/verify/{token}")
async def verify_token_info(token: str):
    """PUBLIC — resolve a token to a vendor stub (safe fields only)."""
    v = await db.vendors.find_one({"magic_token": token})
    if not v:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    return {
        "vendor_ref": v.get("vendor_ref"),
        "email": v.get("email"),
        "company_name": v.get("company_name"),
        "email_verified": v.get("email_verified", False),
    }


@router.post("/verify/{token}/complete")
async def complete_verify(token: str, payload: VerifySetPasswordIn):
    """PUBLIC — vendor sets password, activates account. One-time token."""
    v = await db.vendors.find_one({"magic_token": token})
    if not v:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if v.get("email_verified") and v.get("is_active"):
        raise HTTPException(status_code=400, detail="Account already active — please sign in")
    await db.vendors.update_one(
        {"_id": v["_id"]},
        {"$set": {"password_hash": hash_password(payload.password),
                  "email_verified": True, "is_active": True,
                  "must_change_password": False,
                  "email_verified_at": now_iso()},
         "$unset": {"magic_token": ""}},
    )
    await audit_log("vendor.email_verify", None, "vendor", v.get("vendor_ref"),
                    {"email": v.get("email")})
    return {"ok": True, "vendor_ref": v.get("vendor_ref"), "email": v.get("email")}


# ---------- Registration template (blank form vendors download) ----------

@router.post("/registration-template")
async def upload_registration_template(file: UploadFile = File(...),
                                         admin=Depends(require_role("admin"))):
    """Admin uploads a blank registration form template (PDF/DOCX). Overwrites the previous one."""
    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds pilot upload limit")
    b64 = base64.b64encode(body).decode("ascii")
    doc = {
        "kind": "registration_template",
        "file_name": file.filename,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(body),
        "data_b64": b64,
        "uploaded_by": admin["id"],
        "uploaded_at": now_iso(),
    }
    await db.vendor_templates.update_one({"kind": "registration_template"},
                                          {"$set": doc}, upsert=True)
    await audit_log("vendor.template_upload", admin, "template", "registration",
                    {"file_name": file.filename, "size": len(body)})
    return {"file_name": file.filename, "size_bytes": len(body),
            "download_url": "/api/v1/vendors/registration-template"}


@router.get("/registration-template")
async def download_registration_template():
    """PUBLIC — vendors download the blank form for reference.
    Bug #4 fix — if no template has been uploaded yet, generate a minimal
    fallback PDF so this endpoint never 404s."""
    from fastapi.responses import Response
    doc = await db.vendor_templates.find_one({"kind": "registration_template"})
    if doc:
        body = base64.b64decode(doc["data_b64"])
        return Response(content=body,
                        media_type=doc.get("content_type", "application/octet-stream"),
                        headers={"Content-Disposition": f'attachment; filename="{doc.get("file_name","registration-template")}"'})
    # Fallback — build a simple PDF listing every DOC_SLOT so the vendor has
    # a printable checklist to fill in manually.
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from io import BytesIO
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, h - 60, "PMC Managers — Vendor Registration Form")
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 82, "Print, complete, sign and upload to your registration record.")
        c.setFont("Helvetica-Bold", 12)
        y = h - 120
        c.drawString(50, y, "SECTION A — Company Details"); y -= 20
        c.setFont("Helvetica", 10)
        for lbl in ("Legal Name:", "Trade Name:", "Country:", "Registration Number:",
                    "Legal Entity Type:", "Primary Sector:", "Website:", "Employees Count:"):
            c.drawString(60, y, lbl); c.line(190, y, w - 60, y); y -= 20
        y -= 6; c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "SECTION B — Contact Details"); y -= 20
        c.setFont("Helvetica", 10)
        for lbl in ("Contact Name:", "Contact Email:", "Office Phone:", "Mobile:",
                    "HQ Address (line 1):", "HQ Address (line 2):", "City / State:", "Postal Code:"):
            c.drawString(60, y, lbl); c.line(190, y, w - 60, y); y -= 20
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        y = h - 60
        c.drawString(50, y, "SECTION C — Documents to Attach"); y -= 20
        c.setFont("Helvetica", 10)
        for lbl in ("Incorporation Certificate", "Address Proof",
                    "TIN / VAT Proof", "Audited Financials (3 years)",
                    "Previous Works", "ISO / Quality Certifications",
                    "Licenses / Permits", "Articles of Incorporation",
                    "Bank Reference", "Power of Attorney", "Other Supporting"):
            c.drawString(60, y, f"[ ]  {lbl}"); y -= 18
        y -= 20; c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "DECLARATION"); y -= 18
        c.setFont("Helvetica", 9)
        for line in ("I certify that the information supplied is true and correct.",
                     "I understand that misrepresentation may lead to disqualification.",
                     "Signature: ______________________   Date: ____________________",
                     "Name in block letters: ________________________________________"):
            c.drawString(60, y, line); y -= 18
        c.save()
        return Response(content=buf.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="pmc-registration-form.pdf"'})
    except Exception:
        raise HTTPException(status_code=404, detail="No template uploaded yet")


@router.get("/registration-template/meta")
async def registration_template_meta():
    """PUBLIC — is a template available? Used to show/hide the download button.
    Bug #4 fix — we always have SOMETHING to serve (a generated fallback PDF
    if the admin hasn't uploaded one), so this always reports available."""
    doc = await db.vendor_templates.find_one({"kind": "registration_template"})
    if not doc:
        return {"available": True, "file_name": "pmc-registration-form.pdf",
                "size_bytes": 0, "uploaded_at": None, "fallback": True}
    return {"available": True, "file_name": doc.get("file_name"),
            "size_bytes": doc.get("size_bytes"), "uploaded_at": doc.get("uploaded_at")}
