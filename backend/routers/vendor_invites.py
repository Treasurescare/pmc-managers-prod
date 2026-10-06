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
from pydantic import BaseModel, EmailStr, Field, ConfigDict
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
        # v51aa — surface the matching vendor_ref so the admin UI can offer
        # "Open vendor" / "Edit full profile" instead of a dead-end 409.
        raise HTTPException(status_code=409, detail={
            "code": "vendor_already_active",
            "message": "Vendor with this email already active",
            "vendor_ref": existing.get("vendor_ref"),
            "company_name": existing.get("company_name"),
            "email": existing.get("email"),
        })

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
    csv_text: str  # CSV header row + one vendor per row (Sections A–E supported)


# v51aa — every column the Sections A–E registration form writes. Admin-pasted
# bulk CSV can prefill ALL of them so the invited vendor sees their profile
# already drafted on first login. Columns not listed below are silently
# accepted and stored under `profile.extras`.
_SECTION_FIELDS = {
    # A — Identity (lives on the vendor doc itself; mapped below)
    "company_name", "trade_name", "registered_address", "mailing_address",
    "country", "registration_number", "incorporation_date", "tax_id",
    "legal_entity_type", "website", "employees_count",
    # B — Contact & Signatory
    "contact_name", "contact_title", "contact_office_phone", "contact_mobile",
    "contact_email", "signatory_name", "signatory_title", "signatory_contact",
    # C — Banking & Financial
    "bank_name", "bank_branch", "bank_account_number", "bank_swift", "bank_address",
    "turnover_year1", "turnover_year2", "turnover_year3", "turnover_currency",
    # D — Business Profile
    "primary_sector", "business_description", "operating_regions",
    "business_categories", "iso_certifications", "licenses_permits",
    "insurance_details", "litigation_history", "kz_licenses",
    # E — Declarations & Signature
    "decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
    "decl_data_consent", "decl_fee", "decl_notification",
    "signature_name", "signature_title", "signature_date",
}
_TOP_LEVEL_FIELDS = {"company_name", "country", "contact_name"}  # kept on the vendor doc for list/search
_LIST_FIELDS = {"operating_regions", "business_categories", "kz_licenses"}
_INT_FIELDS = {"employees_count"}
_FLOAT_FIELDS = {"turnover_year1", "turnover_year2", "turnover_year3"}
_BOOL_FIELDS = {k for k in _SECTION_FIELDS if k.startswith("decl_")}


def _coerce_cell(key: str, raw: str):
    s = (raw or "").strip()
    if s == "":
        return None
    if key in _BOOL_FIELDS:
        return s.lower() in ("1", "true", "yes", "y", "x", "✓")
    if key in _INT_FIELDS:
        try: return int(float(s))
        except Exception: return None
    if key in _FLOAT_FIELDS:
        try: return float(s)
        except Exception: return None
    if key in _LIST_FIELDS:
        # pipe / semicolon separated so a comma stays inside the cell
        return [p.strip() for p in s.replace(";", "|").split("|") if p.strip()]
    return s


@router.post("/invite-bulk")
async def invite_vendors_bulk(payload: BulkInviteIn, admin=Depends(require_role("admin"))):
    """Parse a CSV of vendor rows and invite each one. Returns per-row status.

    v51aa — supports the full Sections A–E column set (see _SECTION_FIELDS).
    Any extra column is still accepted and stored under `profile.extras`.
    Required column: `email`.
    """
    import csv, io
    results = []
    reader = csv.DictReader(io.StringIO(payload.csv_text))
    if not reader.fieldnames or "email" not in [f.lower().strip() for f in reader.fieldnames]:
        raise HTTPException(status_code=400,
                             detail="CSV must have header row with at least an 'email' column")
    header_map = {name.lower().strip(): name for name in reader.fieldnames}
    def col(row, k):
        real = header_map.get(k)
        return (row.get(real) or "") if real else ""
    for i, row in enumerate(reader, start=2):
        email = col(row, "email").strip().lower()
        if not email or "@" not in email:
            results.append({"row": i, "email": email, "status": "skipped", "reason": "invalid email"})
            continue
        existing = await db.vendors.find_one({"email": email})
        if existing and existing.get("is_active"):
            results.append({"row": i, "email": email, "status": "skipped",
                             "reason": "already active", "vendor_ref": existing.get("vendor_ref")})
            continue

        # Build the Sections-A–E profile dict from the row.
        profile = {}
        extras = {}
        for header in (reader.fieldnames or []):
            key = header.lower().strip()
            if key == "email":
                continue
            val = _coerce_cell(key, row.get(header))
            if val is None:
                continue
            if key in _SECTION_FIELDS:
                profile[key] = val
            else:
                extras[key] = val
        if extras:
            profile["extras"] = extras

        token = new_magic_token()
        seq = await next_sequence("vendor_seq")
        vendor_ref = f"PMC-SUP-{seq:06d}"
        doc = {
            "vendor_ref": vendor_ref, "email": email,
            # Keep a few hot fields on the vendor doc itself so list/search works
            "company_name": profile.get("company_name"),
            "country": profile.get("country") or "KZ",
            "contact_name": profile.get("contact_name"),
            "profile": profile,
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
                 f"<p>You've been pre-registered as a vendor. Please verify your "
                 f"email and set a password. Your draft profile has been pre-filled "
                 f"with the details our team already captured for you.</p>",
                 "Verify email & set password", verify_url)))
        results.append({"row": i, "email": email, "status": "invited",
                         "vendor_ref": vendor_ref,
                         "profile_fields": len([k for k in profile if k != "extras"])})
    await audit_log("vendor.invite_bulk", admin, "vendor", "csv",
                    {"total": len(results),
                     "invited": sum(1 for r in results if r["status"] == "invited")})
    return {"total": len(results),
            "invited": sum(1 for r in results if r["status"] == "invited"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "results": results}


# v51aa — downloadable CSV template that mirrors every Section A–E field.
# Served by the admin UI's "Download rich template" link so admins never have
# to hand-build the header row.
@router.get("/invite-bulk/template")
async def bulk_invite_template(admin=Depends(require_role("admin"))):
    from fastapi.responses import Response
    headers = ["email"] + sorted(_SECTION_FIELDS)
    sample = [
        "vendor1@example.com", "Alpha Traders LLC", "Alpha", "123 Market St, Almaty",
        "123 Market St, Almaty", "KZ", "KZ-2024-10234", "2015-04-18", "TIN-900123",
        "LLC", "https://alpha.example", "42",
        "Askar Ismailov", "Procurement Director", "+7-7272-000-000", "+7-700-123-4567",
        "procurement@alpha.example", "Askar Ismailov", "Director", "+7-700-123-4567",
        "Halyk Bank", "Almaty Central", "KZ123456789", "HLKZKZKX", "Almaty, KZ",
        "1200000", "1500000", "1800000", "USD",
        "Industrial supply", "Supplier of valves and pumps",
        "KZ|UZ|KG", "Industrial equipment|Spare parts",
        "ISO 9001:2015", "Trade licence L-998", "Public liability $2M", "None",
        "SMK-2024|OTK-2023",
        "true", "true", "true", "true", "true", "true",
        "Askar Ismailov", "Director", "2026-10-06",
    ]
    # Pad sample to match sorted header length (fields may re-order on edit)
    body = ",".join(headers) + "\n"
    row = {h: "" for h in headers}
    row["email"] = sample[0]
    for h, v in zip(headers[1:], sample[1:]):
        row[h] = v
    body += ",".join(f'"{row[h]}"' for h in headers) + "\n"
    return Response(content=body, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="pmc_vendor_bulk_template.csv"',
                             "Cache-Control": "no-store"})


# v51aa — fetch the full raw vendor doc for the admin edit screen (includes
# `profile` sub-dict with Sections A–E answers).
@router.get("/admin/{vendor_ref}/full")
async def admin_get_vendor_full(vendor_ref: str, admin=Depends(require_role("admin", "reviewer"))):
    v = await db.vendors.find_one({"vendor_ref": vendor_ref,
                                     "tenant_id": admin["tenant_id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _out(v)


class VendorProfilePatchIn(BaseModel):
    """Admin edits any subset of the Sections A–E vendor profile."""
    model_config = ConfigDict(extra="allow")

    company_name: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    profile: Optional[dict] = None  # entire sections A–E payload


@router.patch("/admin/{vendor_ref}/full")
async def admin_update_vendor_full(vendor_ref: str, payload: "VendorProfilePatchIn",
                                     admin=Depends(require_role("admin"))):
    """Admin updates the full vendor profile (Sections A–E).

    v51aa — "all vendors created and unpublished — edit field for the entire
    vendor portal". Open to vendors in any status; the admin is authoritative.
    """
    v = await db.vendors.find_one({"vendor_ref": vendor_ref,
                                     "tenant_id": admin["tenant_id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    updates = {}
    for k in ("company_name", "country", "contact_name"):
        val = getattr(payload, k, None)
        if val is not None:
            updates[k] = val or None
    # Merge-patch the profile sub-doc rather than replacing it, so partial
    # section saves don't wipe fields the admin didn't touch.
    if payload.profile is not None:
        current = dict(v.get("profile") or {})
        current.update({k: val for k, val in payload.profile.items() if val is not None})
        updates["profile"] = current
    # Extras pass-through for forward-compat fields the Admin UI may send.
    for k, val in (payload.model_extra or {}).items():
        if k in ("id", "_id", "password_hash", "magic_token", "tenant_id",
                 "created_at", "vendor_ref", "email"):
            continue
        updates[k] = val
    if not updates:
        return {"ok": True, "vendor_ref": vendor_ref, "updated": 0}
    updates["profile_updated_at"] = now_iso()
    updates["profile_updated_by"] = admin["id"]
    await db.vendors.update_one({"_id": v["_id"]}, {"$set": updates})
    await audit_log("vendor.admin_update_full", admin, "vendor", vendor_ref,
                    {"keys": sorted(updates.keys())})
    doc = await db.vendors.find_one({"_id": v["_id"]})
    return _out(doc)


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
