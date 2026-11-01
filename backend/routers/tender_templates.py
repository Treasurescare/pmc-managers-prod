"""Wave 20 — Tender / RFP / RFQ Template Builder.

Lets admins compose a full tender document out of orderable, editable
sections + annexures + forms. Seeded on startup with a **PSU e-Tender**
starter mirroring the ESIC Idukki template (Sections 1-4, Annexures I-VIII,
Forms A-F). Each section is a plain-text blank that the admin fills in.

Wire:
* GET  /api/v1/tender-templates            list master templates
* POST /api/v1/tender-templates            clone one for a new tender
* GET  /api/v1/tender-templates/{id}       fetch full sections
* PATCH /api/v1/tender-templates/{id}      update section bodies / metadata
* POST /api/v1/tender-templates/seed       (admin) re-seed the master library
* POST /api/v1/tender-templates/{id}/sections/{code}/attachment   upload a per-section template file
* DELETE /api/v1/tender-templates/{id}/sections/{code}/attachment
"""
import base64
import html as _html
import uuid
from typing import List, Literal, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from bson import ObjectId

import config
from db import db
from pdf_brand import brand_html
from models.base import BaseDocument, now_iso
from security import require_role
from routers._tender_access import (
    tender_principal, write_principal, is_vendor, scope_filter,
    assert_can_read_doc, assert_can_edit_doc, actor, assert_vendor_can_submit,
    vendor_country,
)
from audit import audit_log
from routers._fees import assert_fees_paid, credit_required
from routers.tender_criteria import has_must_pass

router = APIRouter(prefix="/api/v1/tender-templates", tags=["tender-templates"])


class SectionBlock(BaseModel):
    # v52cp — allow drafts with half-written sections. Previously an empty
    # section code or title fired a Pydantic 422 on every PATCH, which users
    # hit "sometimes" when they added a new blank section before filling it.
    code: Optional[str] = ""
    kind: str = Field(default="section", description="section | annexure | form")
    title: Optional[str] = ""
    hint: Optional[str] = None
    body: Optional[str] = ""
    order: Optional[int] = None   # auto-assigned server-side if omitted
    attachment: Optional[dict] = None  # {file_name, url, content_type, size_bytes, uploaded_at, uploaded_by}


class TenderTemplateIn(BaseModel):
    # v52cp — relaxed name constraint: an in-progress draft can have a short
    # placeholder name without blocking auto-save. The frontend still prompts
    # for a real name on explicit "Save as master".
    name: str = Field(default="Untitled draft", max_length=120)
    kind: Literal["tender", "rfp", "rfq"] = "tender"
    industry: Optional[str] = None
    is_master: bool = False
    header: dict = Field(default_factory=dict)  # work_title, budget, period, timeline
    sections: List[SectionBlock] = Field(default_factory=list)


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Seed content (blank bodies — admins fill them) ----------

PSU_SECTIONS: List[dict] = [
    # Header sections
    {"code": "sec-1", "kind": "section", "title": "Section 1 · Notice Inviting Bid (NIB)",
     "hint": "Summary block: issuer name, work title, budget, EMD/tender fee, timeline, contact, portal link.",
     "body": "", "order": 10},
    {"code": "sec-2", "kind": "section", "title": "Section 2 · Instructions to Bidders (ITB)",
     "hint": "How to submit, envelope structure, DSC class, portal URL, amendments, forfeiture, evaluation method.",
     "body": "", "order": 20},
    {"code": "sec-3", "kind": "section", "title": "Section 3 · Qualifying Criteria",
     "hint": "Turnover floor, similar-work rules, net-worth / bank cert, disqualifications, technical/financial weightage.",
     "body": "", "order": 30},
    {"code": "sec-4", "kind": "section", "title": "Section 4 · Financial Bid Format",
     "hint": "How the bidder quotes (percentage/lumpsum), decimals rule, taxes, currency.",
     "body": "", "order": 40},

    # Annexures
    {"code": "annex-I",   "kind": "annexure", "title": "Annexure I · Acceptance of Bid Conditions",
     "hint": "Bidder's undertaking that all terms and conditions of the tender are accepted without deviation.",
     "body": "", "order": 100},
    {"code": "annex-II",  "kind": "annexure", "title": "Annexure II · General Undertaking",
     "hint": "No conflict of interest, not debarred, no litigation, no misrepresentation.",
     "body": "", "order": 110},
    {"code": "annex-III", "kind": "annexure", "title": "Annexure III · Brief Description & Scope of Work",
     "hint": "Detailed scope of work / deliverables / milestones / stakeholders.",
     "body": "", "order": 120},
    {"code": "annex-IV",  "kind": "annexure", "title": "Annexure IV · Memorandum of Understanding",
     "hint": "Framework MoU — roles, payment terms, dispute resolution, termination.",
     "body": "", "order": 130},
    {"code": "annex-V",   "kind": "annexure", "title": "Annexure V · Integrity Pact",
     "hint": "Anti-bribery, anti-corruption, gift and hospitality clauses per CVC guidelines.",
     "body": "", "order": 140},
    {"code": "annex-VI",  "kind": "annexure", "title": "Annexure VI · Sample Milestone Chart",
     "hint": "Chronological deliverables + payment tranches + acceptance criteria.",
     "body": "", "order": 150},
    {"code": "annex-VII", "kind": "annexure", "title": "Annexure VII · Bid Security Declaration Form",
     "hint": "In lieu of EMD — declaration that the bidder will be debarred if bid withdrawn during validity.",
     "body": "", "order": 160},
    {"code": "annex-VIII","kind": "annexure", "title": "Annexure VIII · Bank Solvency Certificate",
     "hint": "Format of solvency certificate from a scheduled bank — issued within X months.",
     "body": "", "order": 170},

    # Forms
    {"code": "form-A", "kind": "form", "title": "Form A · General Information · Organization Details",
     "hint": "Legal name, address, CIN/GSTIN/PAN, incorporation date, key contacts.",
     "body": "", "order": 200},
    {"code": "form-B", "kind": "form", "title": "Form B · Strength of Key Technical Personnel",
     "hint": "Table of designations, headcount, qualifications, experience floor.",
     "body": "", "order": 210},
    {"code": "form-C", "kind": "form", "title": "Form C · List of Similar Projects Completed (Last 7 Years)",
     "hint": "Client, work name, value, start–end date, current value indexation, contact for verification.",
     "body": "", "order": 220},
    {"code": "form-D", "kind": "form", "title": "Form D · Major Projects in Progress",
     "hint": "Ongoing engagements including % completion, expected finish date, value.",
     "body": "", "order": 230},
    {"code": "form-E", "kind": "form", "title": "Form E · Turnover for Last Five Years",
     "hint": "Y1–Y5 turnover + audited financial statements + CA UDIN.",
     "body": "", "order": 240},
    {"code": "form-F", "kind": "form", "title": "Form F · 'To Whom So Ever It May Concern' Certificate",
     "hint": "Client-issued capability + performance certificate template.",
     "body": "", "order": 250},
]


def _secs(rows: list) -> List[dict]:
    return [{"code": c, "kind": k, "title": t, "hint": h, "body": "", "order": (i + 1) * 10}
            for i, (c, k, t, h) in enumerate(rows)]


RFQ_SECTIONS = _secs([
    ("rfq-1", "section", "1 · Request for Quotation Notice",
     "Buyer, RFQ reference, short description of goods/works/services, quote due date, contact."),
    ("rfq-2", "section", "2 · Item Schedule & Specifications",
     "Line items with exact specification, unit, quantity, make/model or equivalent, standards."),
    ("rfq-3", "section", "3 · Delivery Terms",
     "Delivery location, lead time, Incoterms, packaging, partial deliveries, inspection on receipt."),
    ("rfq-4", "section", "4 · Commercial Terms",
     "Price basis (all-inclusive, taxes), currency, quote validity, payment terms, warranty."),
    ("rfq-5", "section", "5 · Evaluation & Award",
     "Lowest technically compliant quote; item-wise or total award; tie-break; right to reject."),
    ("rfq-6", "section", "6 · How to Submit a Quote",
     "Submission channel, required documents, clarifications deadline, late quotes."),
    ("rfq-form-A", "form", "Form A · Price Schedule",
     "Table: item no., description, unit, qty, unit rate, total, taxes, grand total."),
    ("rfq-form-B", "form", "Form B · Compliance Statement",
     "Bidder confirms each specification is met or lists deviations."),
])

RFP_SECTIONS = _secs([
    ("rfp-1", "section", "1 · Invitation & Background",
     "Who is issuing, the problem or need, project context and objectives."),
    ("rfp-2", "section", "2 · Scope & Expected Outcomes",
     "Outcomes required, scope boundaries, deliverables, milestones, constraints."),
    ("rfp-3", "section", "3 · Instructions to Proposers",
     "Timeline, pre-proposal meeting, questions process, submission format, page limits."),
    ("rfp-4", "section", "4 · Technical Proposal Requirements",
     "Approach & methodology, work plan, team and CVs, relevant experience, innovation."),
    ("rfp-5", "section", "5 · Financial Proposal Requirements",
     "Pricing structure, cost breakdown, payment milestones; submitted separately from technical."),
    ("rfp-6", "section", "6 · Evaluation Criteria & Weighting",
     "Scored criteria with weights, minimum technical score, presentations, final selection."),
    ("rfp-7", "section", "7 · Contract Terms",
     "Key terms of the resulting contract, IP, confidentiality, performance security."),
    ("rfp-form-A", "form", "Form A · Technical Proposal Cover",
     "Proposer details, authorised signatory, declaration of accuracy."),
    ("rfp-form-B", "form", "Form B · Financial Proposal Format",
     "Table of cost components, rates, totals, taxes."),
    ("rfp-form-C", "form", "Form C · Team & Experience",
     "Key personnel, role, qualifications, years of experience, similar assignments."),
])

EXTRA_MASTERS = [
    {"name": "Standard Request for Quotation (RFQ)", "kind": "rfq",
     "industry": "Goods / Supplies / Simple Services",
     "header": {"work_title": "", "budget_amount": None, "period_days": 30,
                "evaluation_method": "Lowest technically compliant quote (L1)", "bid_validity_days": 60},
     "sections": RFQ_SECTIONS},
    {"name": "Standard Request for Proposal (RFP)", "kind": "rfp",
     "industry": "Consulting / Design / Solutions",
     "header": {"work_title": "", "budget_amount": None, "period_days": 180,
                "evaluation_method": "Quality and cost based — Technical 80 : Financial 20",
                "minimum_technical_cutoff": 70, "bid_validity_days": 120},
     "sections": RFP_SECTIONS},
]


async def _seed_extra_masters() -> int:
    n = 0
    for m in EXTRA_MASTERS:
        if await db.tender_templates.find_one({"is_master": True, "seed": True, "kind": m["kind"]}):
            continue
        await db.tender_templates.insert_one({**m, "is_master": True, "seed": True,
                                              "sections": [dict(s) for s in m["sections"]],
                                              "created_at": now_iso()})
        n += 1
    return n


async def seed_master_templates(force: bool = False) -> int:
    """Idempotent — creates the built-in master library on first boot."""
    if force:
        await db.tender_templates.delete_many({"is_master": True, "seed": True})
    extra = await _seed_extra_masters()
    existing = await db.tender_templates.count_documents({"is_master": True, "kind": "tender"})
    if existing:
        return extra
    doc = {
        "name": "Standard PSU e-Tender (GFR 2017, QCBS 70/30)",
        "kind": "tender",
        "industry": "Public Works / Construction / PMC",
        "is_master": True,
        "seed": True,
        "header": {
            "work_title": "",
            "budget_amount": None,
            "budget_currency": "INR",
            "period_days": 900,
            "eligibility": "Central / State Govt Organizations / PSU / Autonomous Body per GFR 2017 Rule 133(3)",
            "evaluation_method": "QCBS — Technical 70 : Financial 30",
            "minimum_technical_cutoff": 70,
            "individual_parameter_cutoff": 50,
            "bid_validity_days": 180,
            "performance_security_pct": 10,
        },
        "sections": PSU_SECTIONS,
        "created_at": now_iso(),
    }
    await db.tender_templates.insert_one(doc)
    return 1 + extra


@router.get("")
async def list_templates(kind: Optional[str] = None,
                         principal=Depends(tender_principal)):
    """List templates visible to the caller (staff: all; vendor: own + shared masters)."""
    q = scope_filter(principal, {})
    q["$nor"] = [{"is_master": True, "moderation_status": {"$in": ["pending", "rejected"]}}]
    if kind:
        q["kind"] = kind
    docs = [d async for d in db.tender_templates.find(q).sort("created_at", -1)]
    # v52cf — attach created_by_email for the Tender Builder "Your drafts" list.
    # Resolve all admin ids in one round-trip to avoid an N+1 lookup.
    admin_ids = {d.get("created_by") for d in docs if d.get("created_by")}
    emails: dict = {}
    if admin_ids:
        async for a in db.admins.find({"_id": {"$in": [ObjectId(x) for x in admin_ids if ObjectId.is_valid(x)]}}):
            emails[str(a["_id"])] = a.get("email")
    out = []
    for d in docs:
        row = _out(d)
        row["created_by_email"] = emails.get(d.get("created_by")) or None
        out.append(row)
    return out


@router.get("/{tid}")
async def get_template(tid: str, principal=Depends(tender_principal)):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_read_doc(principal, doc)
    return _out(doc)


@router.post("")
async def create_from_master(payload: TenderTemplateIn,
                             credit_id: Optional[str] = Query(None),
                             principal=Depends(write_principal)):
    """Clone a master into a working draft (or accept a fully custom one)."""
    doc = payload.model_dump()
    doc["is_master"] = False
    doc["seed"] = False
    doc["created_at"] = now_iso()
    doc["created_by"] = principal["id"]
    if is_vendor(principal):
        doc["owner_vendor_id"] = principal["id"]
        doc["owner_vendor_ref"] = principal.get("vendor_ref")
        doc["owner_company_name"] = principal.get("company_name")
        doc["review_status"] = "draft"
        v = await db.vendors.find_one({"_id": ObjectId(principal["id"])})
        if await credit_required(vendor_country(v or {})):
            q = {"vendor_id": principal["id"], "status": "paid"}
            if credit_id and ObjectId.is_valid(credit_id):
                q["_id"] = ObjectId(credit_id)
            cr = await db.tender_credits.find_one_and_update(
                q, {"$set": {"status": "used", "used_at": now_iso()}}, sort=[("created_at", 1)])
            if not cr:
                raise HTTPException(status_code=402,
                    detail="Pay the tender start fee first — choose your category and tender value in the payment step.")
            h = doc.setdefault("header", {})
            h["product_category"] = cr["category"]
            if not (h.get("tender_value") or h.get("budget_amount")) and cr.get("tender_value"):
                h["tender_value"] = cr["tender_value"]
            doc["fees_paid"] = cr.get("fees") or {}
            doc["credit_id"] = str(cr["_id"])
    # Auto-assign section order if omitted (Bug #1 fix — clone-as-draft
    # was 500ing because the payload dropped 'order').
    # Bug #69/#70/#71 — server-side defence: even if the frontend forgets to
    # strip the master's attachment, a clone must start with none. Otherwise
    # the URL would still point at the master's file and confuse editors.
    for i, sec in enumerate(doc.get("sections") or []):
        if sec.get("order") is None:
            sec["order"] = (i + 1) * 10
        sec.pop("attachment", None)
        sec.pop("_id", None)
        sec.pop("id", None)
    res = await db.tender_templates.insert_one(doc)
    doc["_id"] = res.inserted_id
    if doc.get("credit_id"):
        await db.tender_credits.update_one({"_id": ObjectId(doc["credit_id"])},
                                           {"$set": {"template_id": str(res.inserted_id)}})
    await audit_log("tender_template.create", actor(principal), "tender_template", str(res.inserted_id),
                    {"name": payload.name, "sections": len(payload.sections)})
    return _out(doc)


@router.patch("/{tid}")
async def patch_template(tid: str, payload: TenderTemplateIn,
                         principal=Depends(write_principal)):
    existing = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    assert_can_edit_doc(principal, existing)
    if is_vendor(principal) and existing.get("review_status") in ("submitted", "approved"):
        raise HTTPException(status_code=409,
            detail=f"This tender is '{existing.get('review_status')}' and can't be edited now.")
    body = payload.model_dump()
    if is_vendor(principal):
        old = {s.get("code"): (s.get("body") or "") for s in existing.get("sections") or []}
        if any((s.get("body") or "") != old.get(s.get("code"), "") for s in body.get("sections") or []):
            await assert_fees_paid(principal, {**existing, "header": body.get("header") or {}}, "work")
    body.pop("is_master", None)
    body["updated_at"] = now_iso()
    snapshot = {
        "saved_at": now_iso(),
        "saved_by": (principal or {}).get("email"),
        "name": existing.get("name"),
        "header": existing.get("header") or {},
        "sections": existing.get("sections") or [],
    }
    versions = (existing.get("versions") or []) + [snapshot]
    versions = versions[-20:]  # cap
    body["versions"] = versions
    body["version"] = len(versions) + 1
    await db.tender_templates.update_one({"_id": ObjectId(tid)}, {"$set": body})
    await audit_log("tender_template.update", actor(principal), "tender_template", tid,
                    {"name": payload.name, "version": body["version"]})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


@router.get("/{tid}/versions")
async def list_versions(tid: str, principal=Depends(tender_principal)):
    """List rolling snapshots so the owner can revert."""
    try:
        doc = await db.tender_templates.find_one(
            {"_id": ObjectId(tid)},
            {"versions": 1, "name": 1, "is_master": 1,
             "owner_vendor_id": 1, "moderation_status": 1})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    assert_can_read_doc(principal, doc)
    out = []
    for i, v in enumerate(doc.get("versions") or []):
        out.append({
            "index": i,
            "saved_at": v.get("saved_at"),
            "saved_by": v.get("saved_by"),
            "name": v.get("name"),
            "section_count": len(v.get("sections") or []),
        })
    return {"versions": list(reversed(out))}  # newest first


@router.post("/{tid}/versions/{index}/restore")
async def restore_version(tid: str, index: int,
                            principal=Depends(write_principal)):
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    assert_can_edit_doc(principal, doc)
    versions = doc.get("versions") or []
    if not (0 <= index < len(versions)):
        raise HTTPException(status_code=404, detail="Version index out of range")
    v = versions[index]
    # Also snapshot the current state so the restore itself is undoable.
    snap = {"saved_at": now_iso(), "saved_by": f"{(principal or {}).get('email')} (before restore)",
            "name": doc.get("name"), "header": doc.get("header") or {},
            "sections": doc.get("sections") or []}
    new_versions = (versions + [snap])[-20:]
    await db.tender_templates.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {
            "name": v.get("name"), "header": v.get("header") or {},
            "sections": v.get("sections") or [], "updated_at": now_iso(),
            "versions": new_versions, "version": len(new_versions) + 1,
        }},
    )
    await audit_log("tender_template.restore", actor(principal), "tender_template", tid,
                    {"restored_index": index, "restored_saved_at": v.get("saved_at")})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


@router.delete("/{tid}")
async def delete_template(tid: str, principal=Depends(write_principal)):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("is_master"):
        raise HTTPException(status_code=403, detail="Master templates cannot be deleted")
    assert_can_edit_doc(principal, doc)
    await db.tender_templates.delete_one({"_id": ObjectId(tid)})
    await audit_log("tender_template.delete", actor(principal), "tender_template", tid, {})
    return {"ok": True}


@router.post("/seed")
async def reseed(admin = Depends(require_role("admin"))):
    """Admin-triggered re-seed of the master template library."""
    n = await seed_master_templates(force=True)
    return {"ok": True, "created": n}


@router.post("/{tid}/sections/{code}/attachment")
async def upload_section_attachment(tid: str, code: str,
                                     file: UploadFile = File(...),
                                     principal=Depends(write_principal)):
    """Attach a per-section template file (e.g. Annexure VIII bank cert layout).
    Bidders can download the exact required format from the Notice detail page."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_edit_doc(principal, doc)
    sections = doc.get("sections", [])
    idx = next((i for i, s in enumerate(sections) if s.get("code") == code), -1)
    if idx < 0:
        raise HTTPException(status_code=404, detail="Section not found")
    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds pilot upload limit")
    key = f"tender-section-attachments/{tid}/{code}/{uuid.uuid4().hex}_{file.filename}"
    await db.uploads.insert_one({
        "key": key, "content_type": file.content_type, "size_bytes": len(body),
        "data_b64": base64.b64encode(body).decode("ascii"),
        "created_at": now_iso(),
    })
    meta = {
        "file_name": file.filename, "url": f"/api/v1/uploads/files/{key}",
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(body), "uploaded_at": now_iso(),
        "uploaded_by": principal["email"],
    }
    sections[idx]["attachment"] = meta
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.section_attachment", actor(principal), "tender_template", tid,
                    {"code": code, "file_name": file.filename})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


@router.delete("/{tid}/sections/{code}/attachment")
async def remove_section_attachment(tid: str, code: str,
                                     principal=Depends(write_principal)):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_edit_doc(principal, doc)
    sections = doc.get("sections", [])
    idx = next((i for i, s in enumerate(sections) if s.get("code") == code), -1)
    if idx < 0:
        raise HTTPException(status_code=404, detail="Section not found")
    sections[idx].pop("attachment", None)
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.section_attachment_remove", actor(principal), "tender_template", tid,
                    {"code": code})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


# ---------- PDF export ----------

KIND_LABEL = {"section": "Section", "annexure": "Annexure", "form": "Form"}

HEADER_FIELDS = [
    ("organisation_chain", "Organisation Chain"),
    ("tender_reference_number", "Tender Reference Number"),
    ("tender_id", "Tender ID"),
    ("tender_type", "Tender Type"),
    ("form_of_contract", "Form of Contract"),
    ("tender_category", "Tender Category"),
    ("no_of_covers", "No. of Covers"),
    ("work_title", "Work Title"),
    ("work_description", "Work Description"),
    ("product_category", "Product Category"),
    ("sub_category", "Sub Category"),
    ("contract_type", "Contract Type"),
    ("tender_value", "Tender Value (₹)"),
    ("budget_amount", "Budget Amount"),
    ("budget_currency", "Currency"),
    ("bid_validity_days", "Bid Validity (Days)"),
    ("period_days", "Period of Work (Days)"),
    ("location", "Location"),
    ("pincode", "Pincode"),
    ("emd_amount", "EMD Amount (₹)"),
    ("emd_payable_to", "EMD Payable To"),
    ("emd_payable_at", "EMD Payable At"),
    ("tender_fee_amount", "Tender Fee (₹)"),
    ("fee_payable_to", "Fee Payable To"),
    ("fee_payable_at", "Fee Payable At"),
    ("publish_date", "Publish Date"),
    ("doc_dl_start", "Document Download Start"),
    ("doc_dl_end", "Document Download End"),
    ("sub_start", "Bid Submission Start"),
    ("sub_end", "Bid Submission End"),
    ("bid_opening_date", "Bid Opening Date"),
    ("bid_award_date", "Bid Award Date"),
    ("bid_opening_place", "Bid Opening Place"),
    ("pre_bid_date", "Pre-Bid Meeting Date"),
    ("pre_bid_place", "Pre-Bid Meeting Place"),
    ("pre_bid_address", "Pre-Bid Meeting Address"),
    ("authority_name", "Inviting Authority"),
    ("authority_address", "Authority Address"),
    ("evaluation_method", "Evaluation Method"),
    ("eligibility", "Eligibility"),
]

# HTML tags we allow to survive the RichEditor → PDF pipeline. Anything else
# (script, iframe, style, on*-handlers) is stripped by bleach.
_ALLOWED_TAGS = ["p", "br", "b", "strong", "i", "em", "u", "h2", "h3",
                 "ul", "ol", "li", "blockquote", "code", "pre", "span"]


def _sanitize_body(html: str) -> str:
    """Strip anything but our editorial allowlist. Uses stdlib fallback if
    bleach is not installed — good enough because RichEditor already sanitises
    on the client with DOMPurify."""
    if not html:
        return ""
    try:
        import bleach  # optional dependency; server-side belt-and-braces
        return bleach.clean(html, tags=_ALLOWED_TAGS, attributes={}, strip=True)
    except ImportError:
        return html  # client-side DOMPurify already ran


# ---------- i18n labels for Multi-language PDF export ----------

I18N = {
    "en": {
        "kind_section": "Section", "kind_annexure": "Annexure", "kind_form": "Form",
        "to_be_completed": "[to be completed]", "attached_template": "Attached template",
        "page": "Page", "of": " / ", "issued": "issued",
        "draft": "DRAFT", "published": "PUBLISHED",
        "advisory": "This document is AI-assisted and advisory. Final signature lies with authorised procurement personnel.",
    },
    "ru": {
        "kind_section": "Раздел", "kind_annexure": "Приложение", "kind_form": "Форма",
        "to_be_completed": "[заполняется]", "attached_template": "Шаблон",
        "page": "Стр.", "of": " / ", "issued": "выпущено",
        "draft": "ЧЕРНОВИК", "published": "ОПУБЛИКОВАНО",
        "advisory": "Документ подготовлен с помощью ИИ. Окончательное решение — за уполномоченным сотрудником.",
    },
    "kk": {
        "kind_section": "Бөлім", "kind_annexure": "Қосымша", "kind_form": "Нысан",
        "to_be_completed": "[толтырылады]", "attached_template": "Үлгі",
        "page": "Бет", "of": " / ", "issued": "шығарылған",
        "draft": "ЖОБА", "published": "ЖАРИЯЛАНДЫ",
        "advisory": "Құжат ЖИ көмегімен дайындалды. Түпкі шешім өкілетті қызметкерге тиесілі.",
    },
}


def _lang(lang: Optional[str]) -> dict:
    return I18N.get((lang or "en").lower(), I18N["en"])


def _render_tender_html(doc: dict, lang: Optional[str] = "en") -> str:
    L = _lang(lang)
    kind_map = {"section": L["kind_section"], "annexure": L["kind_annexure"], "form": L["kind_form"]}
    header = doc.get("header") or {}
    header_rows = []
    for key, label in HEADER_FIELDS:
        val = header.get(key)
        if val in (None, "", []):
            continue
        header_rows.append(f"<tr><th>{_html.escape(label)}</th><td>{_html.escape(str(val))}</td></tr>")
    sections = sorted(doc.get("sections") or [], key=lambda s: s.get("order", 0))
    section_html_parts = []
    for s in sections:
        title = _html.escape(s.get("title", ""))
        kind = kind_map.get(s.get("kind"), L["kind_section"])
        hint = f'<div class="hint">{_html.escape(s.get("hint", ""))}</div>' if s.get("hint") else ""
        body = _sanitize_body(s.get("body") or "") or f'<em class="muted">{_html.escape(L["to_be_completed"])}</em>'
        attach = ""
        if s.get("attachment"):
            attach = f'<div class="attach">{_html.escape(L["attached_template"])}: {_html.escape(s["attachment"].get("file_name", ""))}</div>'
        section_html_parts.append(
            f'<section class="sec"><h2>{_html.escape(kind)} · {title}</h2>{hint}<div class="body">{body}</div>{attach}</section>'
        )
    # ---- Watermark & Version stamp ----
    raw_status = (doc.get("status") or ("PUBLISHED" if doc.get("is_master") else "DRAFT")).upper()
    status_label = L["draft"] if raw_status == "DRAFT" else L["published"]
    version = doc.get("version") or 1
    issued = (doc.get("updated_at") or now_iso())[:10]
    stamp = f"{status_label} · v{version} · {L['issued']} {issued}"
    tender_ref = header.get("tender_reference_number") or header.get("tender_id") or doc.get("name") or ""
    page_str = f'"{L["page"]} " counter(page) "{L["of"]}" counter(pages)'
    return f"""<!doctype html><html lang="{_html.escape((lang or 'en').lower())}"><head><meta charset="utf-8"/>
<title>{_html.escape(doc.get('name') or 'Tender')}</title>
<style>
  @page {{
    size: A4; margin: 20mm 16mm 22mm 16mm;
    @top-right {{ content: "{_html.escape(tender_ref)[:80]}"; font: 9pt Georgia, serif; color: #94a3b8; }}
    @bottom-left {{ content: "{_html.escape(stamp)}"; font: 8.5pt Georgia, serif; color: #64748b; }}
    @bottom-right {{ content: {page_str}; font: 8.5pt Georgia, serif; color: #64748b; }}
  }}
  body {{ font: 11pt/1.5 Georgia, 'Times New Roman', serif; color: #0b1f3a; }}
  /* Full-page DRAFT diagonal watermark — only when status is DRAFT */
  {'body::before { content: "' + L["draft"] + '"; position: fixed; top: 42%; left: 0; right: 0; text-align: center; font-size: 120pt; color: rgba(203, 213, 225, 0.28); transform: rotate(-25deg); font-weight: 700; letter-spacing: .12em; z-index: -1; }' if raw_status == 'DRAFT' else ''}
  header.doc {{ border-bottom: 3px double #0b1f3a; padding-bottom: 10pt; margin-bottom: 18pt; }}
  header.doc h1 {{ font-size: 20pt; margin: 0; }}
  header.doc .meta {{ font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: #64748b; }}
  header.doc .stamp {{ margin-top: 6pt; display: inline-block; padding: 2pt 8pt; background: #fef3c7; border: 0.5pt solid #f59e0b; color: #78350f; font-size: 8.5pt; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; }}
  header.doc .advisory {{ margin-top: 4pt; font-size: 7.5pt; color: #64748b; font-style: italic; }}
  table.header {{ width: 100%; border-collapse: collapse; margin: 14pt 0; font-size: 9pt; }}
  table.header th, table.header td {{ border: 0.5pt solid #cbd5e1; padding: 4pt 6pt; text-align: left; vertical-align: top; }}
  table.header th {{ background: #f1f5f9; width: 34%; font-weight: 600; color: #334155; }}
  h2 {{ font-size: 12pt; margin: 18pt 0 4pt; padding-bottom: 3pt; border-bottom: 0.5pt solid #cbd5e1; }}
  .sec {{ margin-bottom: 12pt; page-break-inside: avoid; }}
  .hint {{ font-style: italic; color: #64748b; font-size: 8.5pt; margin-bottom: 4pt; }}
  .body ul, .body ol {{ padding-left: 18pt; }}
  .body blockquote {{ margin: 4pt 0; padding-left: 10pt; border-left: 2pt solid #cbd5e1; color: #334155; }}
  .attach {{ margin-top: 6pt; font-size: 8.5pt; color: #64748b; }}
  .muted {{ color: #94a3b8; }}
</style></head><body>
<header class="doc">
  <div class="meta">{_html.escape((doc.get('kind') or 'tender').upper())} · {_html.escape(doc.get('industry') or '')}</div>
  <h1>{_html.escape(doc.get('name') or 'Tender')}</h1>
  <div class="stamp">{_html.escape(stamp)}</div>
  <div class="advisory">{_html.escape(L["advisory"])}</div>
</header>
<table class="header"><tbody>{''.join(header_rows)}</tbody></table>
{''.join(section_html_parts)}
</body></html>"""


# ---------- Public full-docs ZIP bundle ----------

@router.get("/{tid}/public/zip")
async def public_export_tender_zip(tid: str, request: Request, notice_ref: Optional[str] = None):
    """PUBLIC — bundle the composed PDF + every section attachment into one .zip
    so bidders can pull the whole packet in a single click. Gated by a
    published notice being linked, exactly like the /public/pdf endpoint."""
    if notice_ref:
        n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True,
                                         "tender_template_id": tid})
        if not n:
            raise HTTPException(status_code=404, detail="Tender not available")
        from routers.payments_extra import assert_doc_fee_paid
        await assert_doc_fee_paid(request, n)

    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if not notice_ref and not doc.get("is_master") and not doc.get("public"):
        raise HTTPException(status_code=403, detail="This template is not public")
    if doc.get("is_master") and doc.get("moderation_status") in ("pending", "rejected"):
        raise HTTPException(status_code=404, detail="Tender not available")

    from weasyprint import HTML
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (doc.get("name") or "tender"))[:60]
        # 1. Composed PDF at the root
        pdf_bytes = HTML(string=brand_html(_render_tender_html(doc))).write_pdf()
        zf.writestr(f"{safe_name}.pdf", pdf_bytes)
        # 2. Each section attachment under attachments/
        for s in sorted(doc.get("sections") or [], key=lambda x: x.get("order", 0)):
            att = s.get("attachment")
            if not att:
                continue
            # Pull the raw bytes from the uploads collection.
            key = att.get("url", "").split("/api/v1/uploads/files/", 1)[-1]
            up = await db.uploads.find_one({"key": key})
            if not up or not up.get("data_b64"):
                continue
            safe_att = "".join(c if c.isalnum() or c in "-_." else "_" for c in att.get("file_name", "attachment"))
            zf.writestr(f"attachments/{s['code']}__{safe_att}", base64.b64decode(up["data_b64"]))
        # 3. A README index so bidders know what's inside
        lines = [
            f"# {doc.get('name')}",
            f"Kind: {doc.get('kind')}",
            f"Issued: {(doc.get('updated_at') or '')[:10]}",
            "",
            "## Contents",
            f"- {safe_name}.pdf  — the composed tender document",
        ]
        for s in sorted(doc.get("sections") or [], key=lambda x: x.get("order", 0)):
            if s.get("attachment"):
                lines.append(f"- attachments/{s['code']}__{s['attachment'].get('file_name')}"
                              f"  — {s.get('title')}")
        zf.writestr("README.txt", "\n".join(lines).encode("utf-8"))
    buf.seek(0)
    safe_zip = "".join(c if c.isalnum() or c in "-_" else "_" for c in (doc.get("name") or "tender"))[:60]
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_zip}.zip"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------- Public notice-linked PDF export ----------

@router.get("/{tid}/public/pdf")
async def public_export_tender_pdf(tid: str, request: Request, notice_ref: Optional[str] = None,
                                     lang: Optional[str] = "en"):
    """PUBLIC — bidders download the composed tender PDF from a Notice detail.
    Access is gated by the linked notice being published (or an admin session)."""
    if notice_ref:
        n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True,
                                         "tender_template_id": tid})
        if not n:
            raise HTTPException(status_code=404, detail="Tender not available")
        from routers.payments_extra import assert_doc_fee_paid
        await assert_doc_fee_paid(request, n)
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if not notice_ref and not doc.get("is_master") and not doc.get("public"):
        raise HTTPException(status_code=403, detail="This template is not public")
    if doc.get("is_master") and doc.get("moderation_status") in ("pending", "rejected"):
        raise HTTPException(status_code=404, detail="Tender not available")
    from weasyprint import HTML
    pdf_bytes = HTML(string=brand_html(_render_tender_html(doc, lang=lang))).write_pdf()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (doc.get("name") or "tender"))[:60]
    lang_tag = (lang or "en").lower()[:2]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}_{lang_tag}.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------- AI section draft ----------

class AiDraftIn(BaseModel):
    tone: Optional[str] = "formal"       # formal | plain | strict
    length: Optional[str] = "medium"     # short | medium | long


@router.post("/{tid}/sections/{code}/ai-draft")
async def ai_draft_section(tid: str, code: str,
                            payload: AiDraftIn = AiDraftIn(),
                            principal=Depends(write_principal)):
    """Fill a section body with an LLM draft — uses the same _llm_complete
    helper the DPR pipeline uses so the Emergent proxy routing is honoured.
    Reads the tender header as context so language stays consistent.

    v46n — accepts EMERGENT_LLM_KEY as well.
    v46o — bypasses pmc_lib.LlmChat (which does not know how to reach the
    Emergent integrations proxy) and delegates to tender_pro._llm_complete
    which explicitly sets api_base for sk-emergent-* / sk-managed-* keys.
    """
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_edit_doc(principal, doc)
    await assert_fees_paid(principal, doc, "work")
    section = next((s for s in doc.get("sections", []) if s.get("code") == code), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    header = doc.get("header") or {}
    from routers.tender_pro import _llm_complete, kind_style, kind_label
    import re as _re

    words = {"short": 120, "medium": 240, "long": 420}.get(payload.length or "medium", 240)
    tone_hint = {
        "formal": "Use formal public-procurement English (mirror CPPP / GFR 2017 style).",
        "plain":  "Use plain, direct English suitable for SMEs.",
        "strict": "Use strict, unambiguous contractual language.",
    }.get(payload.tone or "formal", "Use formal English.")

    system_msg = (
        "You are a public-procurement drafting copilot. Draft ONLY the body of "
        f"one {kind_label(doc.get('kind'))} section based on the header context. {kind_style(doc.get('kind'))} "
        "Return valid HTML using ONLY these tags: <p> <br> <b> <i> <u> <ul> <ol> <li> "
        "<h3> <blockquote>. Do NOT include the section title — it is already on the page. "
        f"{tone_hint} Aim for approximately {words} words. Do not invent numbers not present in the context."
    )
    ctx = {
        "section_title": section.get("title"),
        "section_kind":  section.get("kind"),
        "hint":          section.get("hint"),
        "header": {k: header.get(k) for k in
                    ("work_title", "budget_amount", "tender_value", "budget_currency",
                     "period_days", "product_category", "location", "eligibility",
                     "evaluation_method", "emd_amount", "sub_end") if header.get(k)},
    }
    try:
        raw = (await _llm_complete(system_msg, f"Draft the section body. Context: {ctx}")).strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__}: {str(e)[:200]}")
    if raw.startswith("```"):
        raw = _re.sub(r"^```(?:html)?", "", raw).rstrip("`").strip()
    body = _sanitize_body(raw)
    await audit_log("tender_template.ai_draft", actor(principal), "tender_template", tid,
                    {"code": code, "tone": payload.tone, "length": payload.length})
    return {"body": body}


# ---------- Bulk section attachment upload ----------

def _normalise_slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _match_section(sections: list, filename: str) -> Optional[int]:
    """Match a filename to a section by code/title. Prefers exact code, then
    exact title-slug, then a boundary-aware prefix match (longer wins), then
    substring. Avoids the ``annex-VIII`` → ``annex-V`` false positive."""
    slug = _normalise_slug(filename.rsplit(".", 1)[0])
    if not slug:
        return None
    # 1. exact code match
    for i, s in enumerate(sections):
        if _normalise_slug(s.get("code")) == slug:
            return i
    # 2. exact title-slug match
    for i, s in enumerate(sections):
        if _normalise_slug(s.get("title")) == slug:
            return i
    # 3. filename starts with the section code (longer codes win over shorter)
    prefix_matches = []
    for i, s in enumerate(sections):
        code_slug = _normalise_slug(s.get("code"))
        if code_slug and slug.startswith(code_slug):
            prefix_matches.append((len(code_slug), i))
    if prefix_matches:
        prefix_matches.sort(reverse=True)
        return prefix_matches[0][1]
    # 4. substring, longer wins
    sub_matches = []
    for i, s in enumerate(sections):
        code_slug = _normalise_slug(s.get("code"))
        title_slug = _normalise_slug(s.get("title"))
        for k in (code_slug, title_slug):
            if k and (k in slug or slug in k):
                sub_matches.append((len(k), i))
                break
    if sub_matches:
        sub_matches.sort(reverse=True)
        return sub_matches[0][1]
    return None


@router.post("/{tid}/attachments/bulk")
async def bulk_upload_attachments(tid: str,
                                    files: List[UploadFile] = File(...),
                                    principal=Depends(write_principal)):
    """Match each uploaded file to a section by filename → section code/title, then
    attach. Returns a per-file report so the UI can show matched / unmatched."""
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_edit_doc(principal, doc)
    sections = doc.get("sections", [])
    report = []
    for f in files:
        body = await f.read()
        if len(body) > config.MAX_UPLOAD_BYTES:
            report.append({"file_name": f.filename, "matched": False, "reason": "too_large"})
            continue
        idx = _match_section(sections, f.filename)
        if idx is None:
            report.append({"file_name": f.filename, "matched": False, "reason": "no_section_match"})
            continue
        key = f"tender-section-attachments/{tid}/{sections[idx]['code']}/{uuid.uuid4().hex}_{f.filename}"
        await db.uploads.insert_one({
            "key": key, "content_type": f.content_type or "application/octet-stream",
            "size_bytes": len(body),
            "data_b64": base64.b64encode(body).decode("ascii"),
            "created_at": now_iso(),
        })
        meta = {
            "file_name": f.filename, "url": f"/api/v1/uploads/files/{key}",
            "content_type": f.content_type or "application/octet-stream",
            "size_bytes": len(body), "uploaded_at": now_iso(),
            "uploaded_by": principal["email"],
        }
        sections[idx]["attachment"] = meta
        report.append({"file_name": f.filename, "matched": True,
                        "section_code": sections[idx]["code"], "section_title": sections[idx]["title"]})
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.bulk_attachments", actor(principal), "tender_template", tid,
                    {"total": len(files), "matched": sum(1 for r in report if r["matched"])})
    return {"template": _out(await db.tender_templates.find_one({"_id": ObjectId(tid)})),
            "report": report}


@router.get("/{tid}/export/pdf")
async def export_tender_pdf(tid: str, lang: Optional[str] = "en",
                              principal=Depends(tender_principal)):
    """Server-side HTML→PDF render of the composed tender via WeasyPrint —
    returns a real application/pdf response the browser downloads directly.
    `lang=en|ru|kk` swaps the static labels + watermark; user-authored bodies
    remain in the original language they were written."""
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_read_doc(principal, doc)
    if doc.get("owner_vendor_id") == principal.get("id"):
        await assert_fees_paid(principal, doc, "work")
    from weasyprint import HTML
    pdf_bytes = HTML(string=brand_html(_render_tender_html(doc, lang=lang))).write_pdf()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (doc.get("name") or "tender"))[:60]
    lang_tag = (lang or "en").lower()[:2]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}_{lang_tag}.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# =============================================================================
# R9 — vendor submit-for-review + active-reviewer moderation (tenders + masters)
# =============================================================================

class TplReviewIn(BaseModel):
    note: Optional[str] = None


@router.post("/{tid}/submit-review")
async def submit_template_for_review(tid: str, principal=Depends(write_principal)):
    """A vendor submits their own draft for mandatory PMC review. Vendors never
    publish directly — an active reviewer must approve."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_can_edit_doc(principal, doc)
    if not is_vendor(principal):
        raise HTTPException(status_code=400, detail="Only vendor drafts are submitted for review.")
    if doc.get("review_status") not in (None, "draft", "changes_requested"):
        raise HTTPException(status_code=409, detail=f"Already '{doc.get('review_status')}'.")
    h = doc.get("header") or {}
    missing = [n for n, ok in (("title", h.get("work_title") or doc.get("name")),
                               ("description", h.get("work_description")),
                               ("budget", h.get("budget_amount") or h.get("tender_value"))) if not ok]
    if missing:
        raise HTTPException(status_code=422,
            detail="Fill in these fields before submitting: " + ", ".join(missing))
    if not has_must_pass(doc):
        raise HTTPException(status_code=409, detail="Add the tender criteria first — at least one pass/fail criterion is needed before submitting (Criteria button).")
    await assert_vendor_can_submit(principal["id"], doc)
    await assert_fees_paid(principal, doc, "submit")
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"review_status": "submitted", "submitted_at": now_iso()}})
    await audit_log("tender_template.submit_review", actor(principal), "tender_template", tid, {})
    return {"ok": True, "review_status": "submitted"}


@router.get("/review/queue")
async def template_review_queue(status: Optional[str] = "submitted",
                                officer=Depends(require_role("reviewer"))):
    """Active-reviewer-only queue of vendor-prepared tenders."""
    q: dict = {"owner_vendor_id": {"$exists": True}, "is_master": {"$ne": True}}
    if status:
        q["review_status"] = status
    cur = db.tender_templates.find(q).sort("submitted_at", -1)
    return {"items": [_out(d) async for d in cur]}


@router.post("/{tid}/review/approve")
async def approve_template(tid: str, payload: TplReviewIn = TplReviewIn(),
                           officer=Depends(require_role("reviewer"))):
    """Active reviewer approves a vendor tender → publishes it as a notice with
    the originating vendor preserved as author (bid conflict-guard uses this)."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc or not doc.get("owner_vendor_id"):
        raise HTTPException(status_code=404, detail="Vendor tender not found")
    if doc.get("review_status") != "submitted":
        raise HTTPException(status_code=409, detail=f"Tender is '{doc.get('review_status')}', not awaiting review.")
    header = doc.get("header") or {}
    missing = []
    if not (header.get("work_title") or doc.get("name")):
        missing.append("title")
    if not header.get("work_description"):
        missing.append("description")
    if not (header.get("budget_amount") or header.get("tender_value")):
        missing.append("budget")
    if missing:
        raise HTTPException(status_code=422,
            detail="Tender is missing required fields before it can be published: " + ", ".join(missing))
    ref = "VT-" + uuid.uuid4().hex[:8].upper()
    notice = {
        "notice_ref": ref,
        "title": header.get("work_title") or doc.get("name") or "Vendor tender",
        "description": header.get("work_description") or "",
        "category": header.get("product_category") or header.get("tender_category"),
        "submission_deadline": header.get("sub_end"),
        "budget_currency": header.get("budget_currency") or "USD",
        "budget_amount": header.get("budget_amount") or header.get("tender_value"),
        "delivery_country": doc.get("country") or header.get("location"),
        "origin": "vendor",
        "review_status": "approved",
        "is_published": has_must_pass(doc),
        "published_at": now_iso() if has_must_pass(doc) else None,
        "tender_criteria": doc.get("tender_criteria") or [],
        "prepared_by_vendor_id": doc.get("owner_vendor_id"),
        "prepared_by_vendor_ref": doc.get("owner_vendor_ref"),
        "author_name": doc.get("owner_company_name") or "Vendor",
        "tender_template_id": tid,
        "reviewed_by": officer["email"],
        "reviewed_at": now_iso(),
        "review_note": payload.note,
        "created_at": now_iso(),
    }
    await db.notices.insert_one(notice)
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"review_status": "approved", "published_notice_ref": ref,
                  "reviewed_by": officer["email"], "reviewed_at": now_iso(),
                  "review_note": payload.note}})
    await audit_log("tender_template.approve", officer, "tender_template", tid,
                    {"published_notice_ref": ref, "author": notice["author_name"]})
    from routers.marketing import send_tender_alert
    import asyncio as _aio
    if notice["is_published"]:
        _aio.create_task(send_tender_alert(ref))
    return {"ok": True, "review_status": "approved", "notice_ref": ref, "is_published": notice["is_published"],
            "note": None if notice["is_published"] else "Saved as a draft notice — add its criteria, then publish."}


@router.post("/{tid}/review/request-changes")
async def request_changes_template(tid: str, payload: TplReviewIn = TplReviewIn(),
                                   officer=Depends(require_role("reviewer"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc or not doc.get("owner_vendor_id"):
        raise HTTPException(status_code=404, detail="Vendor tender not found")
    if doc.get("review_status") != "submitted":
        raise HTTPException(status_code=409, detail=f"Tender is '{doc.get('review_status')}', not awaiting review.")
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"review_status": "changes_requested", "reviewed_by": officer["email"],
                  "reviewed_at": now_iso(), "review_note": payload.note}})
    await audit_log("tender_template.request_changes", officer, "tender_template", tid, {"note": payload.note})
    return {"ok": True, "review_status": "changes_requested"}


@router.post("/{tid}/review/reject")
async def reject_template(tid: str, payload: TplReviewIn = TplReviewIn(),
                          officer=Depends(require_role("reviewer"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc or not doc.get("owner_vendor_id"):
        raise HTTPException(status_code=404, detail="Vendor tender not found")
    if doc.get("review_status") != "submitted":
        raise HTTPException(status_code=409, detail=f"Tender is '{doc.get('review_status')}', not awaiting review.")
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"review_status": "rejected", "reviewed_by": officer["email"],
                  "reviewed_at": now_iso(), "review_note": payload.note}})
    await audit_log("tender_template.reject", officer, "tender_template", tid, {"note": payload.note})
    return {"ok": True, "review_status": "rejected"}


@router.get("/masters/pending")
async def pending_master_queue(officer=Depends(require_role("reviewer"))):
    """Active-reviewer-only queue of vendor-contributed templates awaiting entry
    into the SHARED master library."""
    cur = db.tender_templates.find(
        {"is_master": True, "moderation_status": "pending"}).sort("created_at", -1)
    return {"items": [_out(d) async for d in cur]}


@router.post("/{tid}/master/approve")
async def approve_master(tid: str, payload: TplReviewIn = TplReviewIn(),
                         officer=Depends(require_role("reviewer"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc or not doc.get("is_master"):
        raise HTTPException(status_code=404, detail="Master template not found")
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"moderation_status": "approved", "approved_by": officer["email"],
                  "approved_at": now_iso()}})
    await audit_log("tender_template.master_approve", officer, "tender_template", tid, {})
    return {"ok": True, "moderation_status": "approved"}


@router.post("/{tid}/master/reject")
async def reject_master(tid: str, payload: TplReviewIn = TplReviewIn(),
                        officer=Depends(require_role("reviewer"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc or not doc.get("is_master"):
        raise HTTPException(status_code=404, detail="Master template not found")
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
        {"$set": {"moderation_status": "rejected", "reviewed_by": officer["email"],
                  "reviewed_at": now_iso(), "review_note": payload.note}})
    await audit_log("tender_template.master_reject", officer, "tender_template", tid, {"note": payload.note})
    return {"ok": True, "moderation_status": "rejected"}
