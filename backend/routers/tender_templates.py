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
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/tender-templates", tags=["tender-templates"])


class SectionBlock(BaseModel):
    code: str
    kind: str = Field(default="section", description="section | annexure | form")
    title: str
    hint: Optional[str] = None
    body: Optional[str] = ""
    order: int


class TenderTemplateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    kind: str = Field(default="tender", description="tender | rfp | rfq")
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


async def seed_master_templates(force: bool = False) -> int:
    """Idempotent — creates the built-in master library on first boot."""
    existing = await db.tender_templates.count_documents({"is_master": True})
    if existing and not force:
        return 0
    if force:
        await db.tender_templates.delete_many({"is_master": True, "seed": True})
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
    return 1


@router.get("")
async def list_templates(kind: Optional[str] = None,
                         admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """List every saved template (master + user-cloned)."""
    q = {}
    if kind:
        q["kind"] = kind
    return [_out(d) async for d in db.tender_templates.find(q).sort("created_at", -1)]


@router.get("/{tid}")
async def get_template(tid: str, admin=Depends(require_role("admin", "reviewer", "auditor"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return _out(doc)


@router.post("")
async def create_from_master(payload: TenderTemplateIn,
                             admin=Depends(require_role("admin"))):
    """Clone a master into a working draft (or accept a fully custom one)."""
    doc = payload.model_dump()
    doc["is_master"] = False
    doc["seed"] = False
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    res = await db.tender_templates.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("tender_template.create", admin, "tender_template", str(res.inserted_id),
                    {"name": payload.name, "sections": len(payload.sections)})
    return _out(doc)


@router.patch("/{tid}")
async def patch_template(tid: str, payload: TenderTemplateIn,
                         admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    # Never let a user flip is_master via PATCH
    body.pop("is_master", None)
    body["updated_at"] = now_iso()
    r = await db.tender_templates.update_one({"_id": ObjectId(tid)}, {"$set": body})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("tender_template.update", admin, "tender_template", tid,
                    {"name": payload.name})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


@router.delete("/{tid}")
async def delete_template(tid: str, admin=Depends(require_role("admin"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("is_master"):
        raise HTTPException(status_code=403, detail="Master templates cannot be deleted")
    await db.tender_templates.delete_one({"_id": ObjectId(tid)})
    await audit_log("tender_template.delete", admin, "tender_template", tid, {})
    return {"ok": True}


@router.post("/seed")
async def reseed(admin=Depends(require_role("admin"))):
    """Admin-triggered re-seed of the master template library."""
    n = await seed_master_templates(force=True)
    return {"ok": True, "created": n}
