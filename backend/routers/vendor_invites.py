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
from typing import Optional, List, Literal
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


class AdminActivateIn(BaseModel):
    """Admin-side activation for an already-existing vendor stub.

    mode=resend_link  Regenerate magic token and re-email the verify link.
    mode=set_password Force-activate immediately (admin provides password).
    """
    mode: Literal["resend_link", "set_password"] = "resend_link"
    password: Optional[str] = Field(default=None, min_length=8)


@router.post("/{vendor_ref}/activate")
async def admin_activate_vendor(vendor_ref: str, payload: "AdminActivateIn",
                                  admin=Depends(require_role("admin"))):
    """Admin re-activates an existing inactive vendor.

    Bug v44 fix — previously the only way to activate a vendor was via the
    magic-link the vendor never clicked. Admins now have a one-click path
    to either resend the verify email or force-set a password themselves.
    """
    v = await db.vendors.find_one({"vendor_ref": vendor_ref,
                                     "tenant_id": admin["tenant_id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if v.get("is_active") and v.get("email_verified"):
        raise HTTPException(status_code=400, detail="Vendor is already active")

    if payload.mode == "set_password":
        if not payload.password:
            raise HTTPException(status_code=400,
                                 detail="password is required when mode=set_password")
        await db.vendors.update_one(
            {"_id": v["_id"]},
            {"$set": {"password_hash": hash_password(payload.password),
                      "email_verified": True, "is_active": True,
                      "must_change_password": True,
                      "email_verified_at": now_iso(),
                      "activated_by": admin["id"], "activated_at": now_iso()},
             "$unset": {"magic_token": ""}},
        )
        asyncio.create_task(send_email(
            v["email"], f"PMC Managers — Vendor account activated · {vendor_ref}",
            wrap(f"Welcome to PMC · {vendor_ref}",
                 f"<p>Your PMC vendor account has been activated by our team. "
                 f"Please sign in and change your password on first login.</p>"
                 f"<p><strong>Login email:</strong> {v['email']}</p>",
                 "Sign in", f"{config.FRONTEND_URL}/login")))
        await audit_log("vendor.admin_activate", admin, "vendor", vendor_ref,
                        {"mode": "set_password", "email": v["email"]})
        return {"ok": True, "vendor_ref": vendor_ref, "mode": "set_password",
                "email": v["email"], "is_active": True}

    # Default: resend magic-link
    token = new_magic_token()
    await db.vendors.update_one(
        {"_id": v["_id"]},
        {"$set": {"magic_token": token, "invited_at": now_iso()}},
    )
    verify_url = f"{config.FRONTEND_URL}/vendor/verify/{token}"
    asyncio.create_task(send_email(
        v["email"], "PMC Managers — Vendor activation link (resent)",
        wrap(f"Activate your account · {vendor_ref}",
             f"<p>Your PMC vendor invitation has been re-issued. Please verify "
             f"your email and set a password to activate your account.</p>",
             "Verify email & set password", verify_url)))
    await audit_log("vendor.admin_activate", admin, "vendor", vendor_ref,
                    {"mode": "resend_link", "email": v["email"]})
    return {"ok": True, "vendor_ref": vendor_ref, "mode": "resend_link",
            "email": v["email"], "verify_url": verify_url}


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
async def download_registration_template(inline: bool = True):
    """PUBLIC — vendors download/view the blank form for reference.
    Bug #4 fix — if no template has been uploaded yet, generate a rich
    fallback PDF so this endpoint never 404s.
    v48c fix — default to `inline` disposition so browsers open the PDF
    in-tab (works via `<a target='_blank'>`) instead of forcing a save
    that some browsers then flag as "cannot open". Force `?inline=false`
    to keep the classic download behavior."""
    from fastapi.responses import Response
    disp_type = "inline" if inline else "attachment"
    doc = await db.vendor_templates.find_one({"kind": "registration_template"})
    if doc:
        body = base64.b64decode(doc["data_b64"])
        ct = doc.get("content_type", "application/octet-stream")
        fn = doc.get("file_name", "registration-template")
        # DOCX etc. must always be attachment
        if ct != "application/pdf":
            disp_type = "attachment"
        return Response(content=body, media_type=ct,
                        headers={"Content-Disposition": f'{disp_type}; filename="{fn}"',
                                 "Cache-Control": "no-store"})
    # Fallback — build a printable PDF with header, sections A/B/C, checklist,
    # signature block. Fully self-contained; opens cleanly in every viewer.
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import HexColor
        from io import BytesIO
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setTitle("PMC Managers Vendor Registration Form")
        c.setAuthor("PMC Managers Limited")
        c.setSubject("Vendor Registration – Blank Form")
        w, h = A4
        NAVY = HexColor("#0F3B2E")
        GOLD = HexColor("#7A5F1E")
        MUTED = HexColor("#4F5C55")

        # --- Letterhead ---
        c.setFillColor(NAVY); c.rect(0, h - 90, w, 90, stroke=0, fill=1)
        c.setFillColor(HexColor("#F3EFE4"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, h - 45, "PMC Managers Limited")
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 62, "Global Tender Board  |  Vendor Registration Form")
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
        c.drawString(50, h - 78, "REV 1.0  ·  BLANK FORM  ·  PRINT · COMPLETE · SIGN · UPLOAD")

        # --- Intro ---
        y = h - 120; c.setFillColor(HexColor("#14261F")); c.setFont("Helvetica", 10)
        for line in ("Complete this form in block letters. Upload the signed & scanned copy to your",
                     "registration record along with the supporting documents listed in Section C."):
            c.drawString(50, y, line); y -= 14

        def section_header(label):
            nonlocal y
            y -= 10; c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 7)
            c.drawString(50, y, "SECTION"); c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 13)
            c.drawString(90, y, label); y -= 4
            c.setStrokeColor(GOLD); c.setLineWidth(0.4); c.line(50, y, w - 50, y); y -= 16

        def field(label):
            nonlocal y
            c.setFillColor(MUTED); c.setFont("Helvetica", 9)
            c.drawString(50, y, label)
            c.setStrokeColor(HexColor("#C9C1AA")); c.setLineWidth(0.4)
            c.line(200, y - 1, w - 50, y - 1); y -= 22

        section_header("A  —  COMPANY DETAILS")
        for lbl in ("Legal Name", "Trade Name", "Country of registration",
                    "Registration / Trade Licence No.", "Legal entity type",
                    "Primary sector", "Website", "Employees (headcount)"):
            field(lbl)

        section_header("B  —  CONTACT DETAILS")
        for lbl in ("Contact Name", "Contact Email", "Office phone", "Mobile",
                    "HQ address (line 1)", "HQ address (line 2)", "City / State", "Postal code"):
            field(lbl)

        c.showPage()
        y = h - 60
        section_header("C  —  DOCUMENTS TO ATTACH")
        c.setFillColor(HexColor("#14261F")); c.setFont("Helvetica", 10)
        for lbl in ("Certificate of incorporation",
                    "Registered address proof (utility bill / lease)",
                    "TIN / VAT / GST proof",
                    "Audited financial statements (last 3 fiscal years)",
                    "Previous works & client references",
                    "ISO 9001 / 14001 / 45001 certifications (as applicable)",
                    "Trade licences / sector-specific permits",
                    "Articles of incorporation / MoA",
                    "Bank reference letter",
                    "Power of Attorney (if signatory ≠ director)",
                    "Product data-sheets / catalogues",
                    "Insurance certificates (Public liability, EAR/CAR)"):
            c.rect(50, y - 4, 10, 10, stroke=1, fill=0)
            c.drawString(68, y, lbl); y -= 20

        section_header("D  —  DECLARATION")
        c.setFillColor(HexColor("#14261F")); c.setFont("Helvetica", 9.5)
        for line in ("1. All information supplied above is true and correct to the best of my knowledge.",
                     "2. I understand that any misrepresentation may lead to disqualification and permanent debarment.",
                     "3. I authorise PMC Managers Limited to verify these details with any third party.",
                     "4. I have read and accept the Global Tender Board Bidder Terms of Use."):
            c.drawString(50, y, line); y -= 16
        y -= 20
        c.setFillColor(MUTED); c.setFont("Helvetica", 9)
        c.drawString(50, y, "Authorised signatory (name in block letters):")
        c.line(300, y - 1, w - 50, y - 1); y -= 28
        c.drawString(50, y, "Designation:"); c.line(140, y - 1, 320, y - 1)
        c.drawString(340, y, "Date:"); c.line(380, y - 1, w - 50, y - 1); y -= 28
        c.drawString(50, y, "Signature & company seal:")
        c.rect(50, y - 110, w - 100, 100, stroke=1, fill=0); y -= 130
        c.setFillColor(GOLD); c.setFont("Helvetica", 7)
        c.drawString(50, 30, "PMC Managers Limited  ·  Global Tender Board  ·  Generated blank form (no template uploaded yet by admin)")

        c.save()
        return Response(content=buf.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": f'{disp_type}; filename="pmc-registration-form.pdf"',
                                 "Cache-Control": "no-store"})
    except Exception as e:
        import logging as _lg
        _lg.exception(f"registration-template PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build blank form PDF: {e}")


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
