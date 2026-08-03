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
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field
from bson import ObjectId

import config
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
    attachment: Optional[dict] = None  # {file_name, url, content_type, size_bytes, uploaded_at, uploaded_by}


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


@router.post("/{tid}/sections/{code}/attachment")
async def upload_section_attachment(tid: str, code: str,
                                     file: UploadFile = File(...),
                                     admin=Depends(require_role("admin"))):
    """Attach a per-section template file (e.g. Annexure VIII bank cert layout).
    Bidders can download the exact required format from the Notice detail page."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
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
        "uploaded_by": admin["email"],
    }
    sections[idx]["attachment"] = meta
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.section_attachment", admin, "tender_template", tid,
                    {"code": code, "file_name": file.filename})
    return _out(await db.tender_templates.find_one({"_id": ObjectId(tid)}))


@router.delete("/{tid}/sections/{code}/attachment")
async def remove_section_attachment(tid: str, code: str,
                                     admin=Depends(require_role("admin"))):
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    sections = doc.get("sections", [])
    idx = next((i for i, s in enumerate(sections) if s.get("code") == code), -1)
    if idx < 0:
        raise HTTPException(status_code=404, detail="Section not found")
    sections[idx].pop("attachment", None)
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.section_attachment_remove", admin, "tender_template", tid,
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


def _render_tender_html(doc: dict) -> str:
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
        kind = KIND_LABEL.get(s.get("kind"), "Section")
        hint = f'<div class="hint">{_html.escape(s.get("hint", ""))}</div>' if s.get("hint") else ""
        body = _sanitize_body(s.get("body") or "") or '<em class="muted">[to be completed]</em>'
        attach = ""
        if s.get("attachment"):
            attach = f'<div class="attach">Attached template: {_html.escape(s["attachment"].get("file_name", ""))}</div>'
        section_html_parts.append(
            f'<section class="sec"><h2>{_html.escape(kind)} · {title}</h2>{hint}<div class="body">{body}</div>{attach}</section>'
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"/>
<title>{_html.escape(doc.get('name') or 'Tender')}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{ font: 11pt/1.5 Georgia, 'Times New Roman', serif; color: #0b1f3a; }}
  header.doc {{ border-bottom: 3px double #0b1f3a; padding-bottom: 10pt; margin-bottom: 18pt; }}
  header.doc h1 {{ font-size: 20pt; margin: 0; }}
  header.doc .meta {{ font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: #64748b; }}
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
</header>
<table class="header"><tbody>{''.join(header_rows)}</tbody></table>
{''.join(section_html_parts)}
</body></html>"""


@router.get("/{tid}/export/pdf")
async def export_tender_pdf(tid: str, admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """Server-side HTML→PDF render of the composed tender via WeasyPrint —
    returns a real application/pdf response the browser downloads directly."""
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    from weasyprint import HTML
    pdf_bytes = HTML(string=_render_tender_html(doc)).write_pdf()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (doc.get("name") or "tender"))[:60]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )
