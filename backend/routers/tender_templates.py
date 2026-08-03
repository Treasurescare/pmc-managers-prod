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
    # ---- Watermark & Version stamp ----
    from datetime import datetime, timezone
    status = (doc.get("status") or ("PUBLISHED" if doc.get("is_master") else "DRAFT")).upper()
    version = doc.get("version") or 1
    issued = (doc.get("updated_at") or now_iso())[:10]
    stamp = f"{status} · v{version} · issued {issued}"
    tender_ref = header.get("tender_reference_number") or header.get("tender_id") or doc.get("name") or ""
    return f"""<!doctype html><html><head><meta charset="utf-8"/>
<title>{_html.escape(doc.get('name') or 'Tender')}</title>
<style>
  @page {{
    size: A4; margin: 20mm 16mm 22mm 16mm;
    @top-right {{ content: "{_html.escape(tender_ref)[:80]}"; font: 9pt Georgia, serif; color: #94a3b8; }}
    @bottom-left {{ content: "{_html.escape(stamp)}"; font: 8.5pt Georgia, serif; color: #64748b; }}
    @bottom-right {{ content: "Page " counter(page) " / " counter(pages); font: 8.5pt Georgia, serif; color: #64748b; }}
  }}
  body {{ font: 11pt/1.5 Georgia, 'Times New Roman', serif; color: #0b1f3a; }}
  /* Full-page DRAFT diagonal watermark — only when status is DRAFT */
  {'body::before { content: "DRAFT"; position: fixed; top: 42%; left: 0; right: 0; text-align: center; font-size: 120pt; color: rgba(203, 213, 225, 0.28); transform: rotate(-25deg); font-weight: 700; letter-spacing: .12em; z-index: -1; }' if status == 'DRAFT' else ''}
  header.doc {{ border-bottom: 3px double #0b1f3a; padding-bottom: 10pt; margin-bottom: 18pt; }}
  header.doc h1 {{ font-size: 20pt; margin: 0; }}
  header.doc .meta {{ font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: #64748b; }}
  header.doc .stamp {{ margin-top: 6pt; display: inline-block; padding: 2pt 8pt; background: #fef3c7; border: 0.5pt solid #f59e0b; color: #78350f; font-size: 8.5pt; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; }}
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
</header>
<table class="header"><tbody>{''.join(header_rows)}</tbody></table>
{''.join(section_html_parts)}
</body></html>"""


# ---------- Public notice-linked PDF export ----------

@router.get("/{tid}/public/pdf")
async def public_export_tender_pdf(tid: str, notice_ref: Optional[str] = None):
    """PUBLIC — bidders download the composed tender PDF from a Notice detail.
    Access is gated by the linked notice being published (or an admin session)."""
    if notice_ref:
        n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True,
                                         "tender_template_id": tid})
        if not n:
            raise HTTPException(status_code=404, detail="Tender not available")
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if not notice_ref and not doc.get("is_master") and not doc.get("public"):
        raise HTTPException(status_code=403, detail="This template is not public")
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


# ---------- AI section draft ----------

class AiDraftIn(BaseModel):
    tone: Optional[str] = "formal"       # formal | plain | strict
    length: Optional[str] = "medium"     # short | medium | long


@router.post("/{tid}/sections/{code}/ai-draft")
async def ai_draft_section(tid: str, code: str,
                            payload: AiDraftIn = AiDraftIn(),
                            admin=Depends(require_role("admin", "reviewer"))):
    """Fill a section body with an LLM draft — uses Emergent LLM key + emergentintegrations.
    Reads the tender header (title, budget, category, timeline) as context so the
    generated language is consistent with the rest of the document."""
    import os
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="AI copilot is not configured (missing EMERGENT_LLM_KEY)")
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    section = next((s for s in doc.get("sections", []) if s.get("code") == code), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    header = doc.get("header") or {}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM SDK unavailable: {type(e).__name__}")

    words = {"short": 120, "medium": 240, "long": 420}.get(payload.length or "medium", 240)
    tone_hint = {
        "formal": "Use formal Indian public-procurement English (mirror CPPP / GFR 2017 style).",
        "plain":  "Use plain, direct English suitable for SMEs.",
        "strict": "Use strict, unambiguous contractual language.",
    }.get(payload.tone or "formal", "Use formal English.")

    chat = LlmChat(
        api_key=key,
        session_id=f"tender-ai-{tid}-{code}",
        system_message=(
            "You are a public-procurement drafting copilot. Draft ONLY the body of "
            "one tender-document section based on the header context. "
            "Return valid HTML using ONLY these tags: <p> <br> <b> <i> <u> <ul> <ol> <li> "
            "<h3> <blockquote>. Do NOT include the section title — it is already on the page. "
            f"{tone_hint} Aim for approximately {words} words. Do not invent numbers not present in the context."
        ),
    )
    chat.with_model("openai", "gpt-4o-mini")
    ctx = {
        "section_title": section.get("title"),
        "section_kind": section.get("kind"),
        "hint": section.get("hint"),
        "header": {k: header.get(k) for k in
                    ("work_title", "budget_amount", "tender_value", "budget_currency",
                     "period_days", "product_category", "location", "eligibility",
                     "evaluation_method", "emd_amount", "sub_end") if header.get(k)},
    }
    try:
        resp = await chat.send_message(UserMessage(text=f"Draft the section body. Context: {ctx}"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__}")
    body = _sanitize_body(str(resp))
    await audit_log("tender_template.ai_draft", admin, "tender_template", tid,
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
                                    admin=Depends(require_role("admin"))):
    """Match each uploaded file to a section by filename → section code/title, then
    attach. Returns a per-file report so the UI can show matched / unmatched."""
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed template id")
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
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
            "uploaded_by": admin["email"],
        }
        sections[idx]["attachment"] = meta
        report.append({"file_name": f.filename, "matched": True,
                        "section_code": sections[idx]["code"], "section_title": sections[idx]["title"]})
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections, "updated_at": now_iso()}})
    await audit_log("tender_template.bulk_attachments", admin, "tender_template", tid,
                    {"total": len(files), "matched": sum(1 for r in report if r["matched"])})
    return {"template": _out(await db.tender_templates.find_one({"_id": ObjectId(tid)})),
            "report": report}


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
