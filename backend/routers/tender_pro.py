"""v45 — Tender Pro: DPR-driven auto-generation, AI-fill-all, masters, filters.

Adds four capability bundles on top of tender_templates:
  Phase C — DPR upload → structured extract → prefilled draft
            + one-shot AI fill-all across every section
  Phase A — Auto tender-reference generator (COUNTRY-IND-KIND-YY-SEQ)
            per-section save endpoint
  Phase B — EMD/fee master (country + industry + slabs)
            "Save as master" promotion of a draft
  Phase D — Vendor rating criteria master + multi-rater aggregate scoring
"""
import base64
import re
import os
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db, next_sequence
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/tender-pro", tags=["tender-pro"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# =============================================================================
# PHASE C — DPR upload + AI fill-all
# =============================================================================

class DprAnalyzeResult(BaseModel):
    header: dict
    section_bodies: dict  # {section_code: html_body}
    warnings: List[str]


def _extract_text_from_upload(name: str, body: bytes) -> str:
    """Best-effort text extraction. PDF via pypdf, DOCX via python-docx.
    Falls back to raw utf-8 decode for txt."""
    name_lower = (name or "").lower()
    if name_lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(body))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF parse failed: {type(e).__name__}")
    if name_lower.endswith(".docx"):
        try:
            from docx import Document as _Doc
            from io import BytesIO
            d = _Doc(BytesIO(body))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DOCX parse failed: {type(e).__name__}")
    try:
        return body.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported file type — upload PDF, DOCX or TXT")


def _llm_key() -> str:
    key = os.environ.get("LLM_API_KEY") or os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("LEGACY_LLM_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="AI copilot is not configured (missing LLM_API_KEY)")
    return key


async def _llm_complete(system: str, user: str) -> str:
    """Single-shot LLM completion with correct proxy routing.

    sk-managed-*  → white-label production proxy (INTEGRATION_PROXY_URL or
                    https://api.pmcmanagers.com/llm) — same path the vendored
                    pmc_lib uses on AWS.
    sk-emergent-* → Emergent integrations proxy (preview / local dev).
    anything else → direct OpenAI-compatible call.
    """
    import litellm
    key = _llm_key()
    params = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        "api_key": key,
    }
    if key.startswith("sk-managed-"):
        proxy = os.environ.get("INTEGRATION_PROXY_URL") or "https://api.pmcmanagers.com"
        params["api_base"] = proxy.rstrip("/") + "/llm"
        params["custom_llm_provider"] = "openai"
    elif key.startswith("sk-emergent-"):
        params["api_base"] = "https://integrations.emergentagent.com/llm"
        params["custom_llm_provider"] = "openai"
    try:
        resp = await litellm.acompletion(**params)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__} {str(e)[:200]}")
    return resp.choices[0].message.content or ""


@router.post("/dpr/analyze")
async def analyze_dpr(file: UploadFile = File(...),
                       kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                       admin=Depends(require_role("admin", "reviewer"))):
    """Upload a DPR / project brief. LLM extracts structured fields for the
    Tender Builder header and drafts a body for each canonical section.

    Returns a preview payload that the frontend can review before cloning
    a working draft. Nothing is written to Mongo here.
    """
    body_bytes = await file.read()
    if len(body_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="DPR exceeds 15 MB limit")
    text = _extract_text_from_upload(file.filename, body_bytes)
    if len(text.strip()) < 60:
        raise HTTPException(status_code=422, detail="Could not extract readable text from the uploaded DPR")

    # Truncate to keep LLM context manageable
    excerpt = text[:16000]
    system_msg = (
        "You are a public-procurement copilot. Given a Detailed Project Report (DPR) excerpt, "
        f"produce a JSON object suitable for a {kind.upper()} pack with EXACTLY these keys: "
        "{\"header\": {work_title, work_description, tender_value, budget_currency, period_days, "
        "location, product_category, sub_category, contract_type, eligibility, evaluation_method, "
        "bid_validity_days, emd_amount, emd_type, emd_percentage, tender_fee_amount}, "
        "\"section_bodies\": {sec-1, sec-2, sec-3, sec-4, annex-III}, "
        "\"warnings\": [fields you could not confidently extract]}. "
        "section_bodies values MUST be short HTML using only <p><br><b><i><ul><ol><li>. "
        "Return valid JSON only — no prose, no code fences."
    )
    resp = await _llm_complete(system_msg, f"DPR excerpt:\n{excerpt}")

    import json as _json
    raw = str(resp).strip()
    # Strip accidental code fences the model sometimes wraps around JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
    try:
        parsed = _json.loads(raw)
    except Exception:
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON — retry")

    parsed.setdefault("header", {})
    parsed.setdefault("section_bodies", {})
    parsed.setdefault("warnings", [])
    await audit_log("tender_pro.dpr_analyze", admin, "dpr", file.filename,
                    {"chars_in": len(text), "sections_out": len(parsed.get("section_bodies") or {})})
    return parsed


class AiFillAllIn(BaseModel):
    tone: Optional[str] = "formal"
    length: Optional[str] = "medium"
    only_empty: bool = True   # skip sections that already have body content


@router.post("/templates/{tid}/ai-fill-all")
async def ai_fill_all_sections(tid: str, payload: AiFillAllIn = AiFillAllIn(),
                                admin=Depends(require_role("admin"))):
    """Draft EVERY section body in one pass. Returns the updated template
    doc so the frontend can replace state atomically. Existing bodies are
    preserved when only_empty=True (default)."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    header = doc.get("header") or {}
    updated = 0
    words = {"short": 120, "medium": 240, "long": 420}.get(payload.length or "medium", 240)

    sections = list(doc.get("sections") or [])
    for i, sec in enumerate(sections):
        if payload.only_empty and (sec.get("body") or "").strip():
            continue
        system_msg = (
            "You are a public-procurement drafting copilot. Draft the body of ONE tender-document "
            "section based on the section title, hint and tender header. Return valid HTML using "
            "ONLY these tags: <p><br><b><i><ul><ol><li><h3>. Do not include the title. "
            f"Aim for approximately {words} words. Do not invent numbers not present in the context."
        )
        ctx = {"section_title": sec.get("title"), "section_kind": sec.get("kind"),
               "hint": sec.get("hint"),
               "header": {k: header.get(k) for k in
                          ("work_title", "budget_amount", "tender_value", "budget_currency",
                           "period_days", "product_category", "location", "eligibility",
                           "evaluation_method", "emd_amount", "sub_end", "country", "industry")
                          if header.get(k)}}
        try:
            body_html = (await _llm_complete(system_msg, f"Draft the body. Context: {ctx}")).strip()
            if body_html.startswith("```"):
                body_html = re.sub(r"^```(?:html)?", "", body_html).rstrip("`").strip()
            sections[i] = {**sec, "body": body_html}
            updated += 1
        except HTTPException:
            continue

    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections,
                                                    "updated_at": now_iso()}})
    await audit_log("tender_pro.ai_fill_all", admin, "tender_template", tid,
                    {"updated_sections": updated})
    fresh = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    return {"updated": updated, "template": _out(fresh)}


# =============================================================================
# PHASE A — Auto tender-ref + per-section save
# =============================================================================

@router.post("/next-reference")
async def next_tender_reference(country: str = Query(..., min_length=2, max_length=3),
                                 industry: str = Query("GEN"),
                                 kind: str = Query("tender", regex="^(tender|rfp|rfq)$"),
                                 admin=Depends(require_role("admin"))):
    """Generate PMC-{COUNTRY}-{IND}-{KIND}-{YY}-{SEQ} auto reference.
    Sequence is per (country, kind) to keep numbers small and predictable."""
    yy = datetime.now(timezone.utc).strftime("%y")
    seq = await next_sequence(f"tref_{country.upper()}_{kind}")
    ind_code = re.sub(r"[^A-Z0-9]", "", (industry or "GEN").upper())[:4] or "GEN"
    ref = f"PMC-{country.upper()}-{ind_code}-{kind.upper()}-{yy}-{seq:05d}"
    return {"reference": ref, "sequence": seq, "generated_at": now_iso()}


class SectionPatchIn(BaseModel):
    body: Optional[str] = None
    title: Optional[str] = None
    hint: Optional[str] = None
    order: Optional[int] = None


@router.patch("/templates/{tid}/sections/{code}")
async def patch_one_section(tid: str, code: str, payload: SectionPatchIn,
                             admin=Depends(require_role("admin"))):
    """v45 — Save a single section without rewriting the whole document.
    Bypasses the versions-array append that the full PATCH triggers, so users
    can hit "Save section" after every keystroke burst without polluting history."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    sections = doc.get("sections") or []
    idx = next((i for i, s in enumerate(sections) if s.get("code") == code), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Section not found")
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    sections[idx] = {**sections[idx], **patch}
    await db.tender_templates.update_one({"_id": ObjectId(tid)},
                                          {"$set": {"sections": sections,
                                                    "updated_at": now_iso()}})
    await audit_log("tender_pro.section_save", admin, "tender_template", tid,
                    {"code": code, "keys": list(patch.keys())})
    return {"ok": True, "section": sections[idx]}


# =============================================================================
# PHASE B — Country field on templates, save-as-master, EMD master
# =============================================================================

class SaveAsMasterIn(BaseModel):
    country: str = Field(min_length=2, max_length=3)
    industry: str = Field(min_length=2, max_length=80)
    name: Optional[str] = None


@router.post("/templates/{tid}/save-as-master")
async def save_as_master(tid: str, payload: SaveAsMasterIn,
                          admin=Depends(require_role("admin"))):
    """Promote a working draft to the master library under a specific
    (country, industry) so the same organisation can reuse it later."""
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    clone = {k: v for k, v in doc.items() if k != "_id"}
    clone["is_master"] = True
    clone["seed"] = False
    clone["country"] = payload.country.upper()
    clone["industry"] = payload.industry
    clone["name"] = payload.name or f"{doc.get('name', 'Untitled')} · {payload.country.upper()} master"
    clone["created_at"] = now_iso()
    clone["created_by"] = admin["id"]
    clone.pop("versions", None)
    clone.pop("version", None)
    for sec in clone.get("sections") or []:
        sec.pop("attachment", None)  # masters ship with no per-clone files
    res = await db.tender_templates.insert_one(clone)
    await audit_log("tender_pro.save_as_master", admin, "tender_template", str(res.inserted_id),
                    {"source": tid, "country": clone["country"], "industry": clone["industry"]})
    return _out(await db.tender_templates.find_one({"_id": res.inserted_id}))


# ---------- EMD / Fee master ----------

class EmdSlabIn(BaseModel):
    tender_value_min: float = 0.0
    tender_value_max: Optional[float] = None  # null = infinity
    fee_type: Literal["fixed", "percentage"] = "percentage"
    fixed_amount: Optional[float] = None
    percentage: Optional[float] = None
    pct_min: Optional[float] = None
    pct_max: Optional[float] = None


class EmdMasterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country: str = Field(min_length=2, max_length=3)
    industry: Optional[str] = None
    kind: Literal["tender_fee", "emd"] = "emd"
    currency: str = "USD"
    slabs: List[EmdSlabIn] = Field(default_factory=list)
    is_active: bool = True
    notes: Optional[str] = None


@router.get("/emd-masters")
async def list_emd_masters(country: Optional[str] = None, kind: Optional[str] = None,
                            admin=Depends(require_role("admin", "reviewer"))):
    q = {}
    if country: q["country"] = country.upper()
    if kind:    q["kind"] = kind
    return [_out(d) async for d in db.emd_masters.find(q).sort("name", 1)]


@router.post("/emd-masters")
async def create_emd_master(payload: EmdMasterIn,
                             admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["country"] = doc["country"].upper()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    res = await db.emd_masters.insert_one(doc)
    await audit_log("tender_pro.emd_master_create", admin, "emd_master", str(res.inserted_id),
                    {"name": doc["name"], "country": doc["country"], "kind": doc["kind"]})
    return _out(await db.emd_masters.find_one({"_id": res.inserted_id}))


@router.patch("/emd-masters/{eid}")
async def update_emd_master(eid: str, payload: EmdMasterIn,
                             admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body["country"] = body["country"].upper()
    body["updated_at"] = now_iso()
    r = await db.emd_masters.update_one({"_id": ObjectId(eid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="EMD master not found")
    return _out(await db.emd_masters.find_one({"_id": ObjectId(eid)}))


@router.delete("/emd-masters/{eid}")
async def delete_emd_master(eid: str, admin=Depends(require_role("admin"))):
    await db.emd_masters.delete_one({"_id": ObjectId(eid)})
    return {"ok": True}


class EmdComputeIn(BaseModel):
    master_id: str
    tender_value: float


@router.post("/emd-masters/compute")
async def compute_emd(payload: EmdComputeIn,
                       admin=Depends(require_role("admin", "reviewer"))):
    """Given a master id + tender value, return the applicable slab + amount."""
    m = await db.emd_masters.find_one({"_id": ObjectId(payload.master_id)})
    if not m:
        raise HTTPException(status_code=404, detail="EMD master not found")
    v = payload.tender_value
    for slab in (m.get("slabs") or []):
        lo = slab.get("tender_value_min") or 0
        hi = slab.get("tender_value_max")
        if v >= lo and (hi is None or v < hi):
            if slab["fee_type"] == "fixed":
                amount = float(slab.get("fixed_amount") or 0)
                return {"amount": amount, "type": "fixed", "slab": slab, "currency": m.get("currency", "USD")}
            pct = float(slab.get("percentage") or 0)
            amount = round(v * pct / 100.0, 2)
            return {"amount": amount, "type": "percentage", "percentage": pct, "slab": slab,
                    "currency": m.get("currency", "USD")}
    raise HTTPException(status_code=422, detail="No slab matches this tender value")


# =============================================================================
# PHASE D — Vendor rating criteria master + multi-rater aggregate
# =============================================================================

class RatingCriterionIn(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    weight: float = 1.0  # relative
    scale_min: int = 1
    scale_max: int = 5


class RatingCriteriaSetIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country: Optional[str] = None
    industry: Optional[str] = None
    criteria: List[RatingCriterionIn]
    is_default: bool = False
    is_active: bool = True


@router.get("/rating-criteria")
async def list_criteria_sets(admin=Depends(require_role("admin", "reviewer"))):
    return [_out(d) async for d in db.rating_criteria_sets.find({}).sort("name", 1)]


@router.post("/rating-criteria")
async def create_criteria_set(payload: RatingCriteriaSetIn,
                                admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    if doc.get("is_default"):
        await db.rating_criteria_sets.update_many({}, {"$set": {"is_default": False}})
    res = await db.rating_criteria_sets.insert_one(doc)
    return _out(await db.rating_criteria_sets.find_one({"_id": res.inserted_id}))


@router.patch("/rating-criteria/{sid}")
async def update_criteria_set(sid: str, payload: RatingCriteriaSetIn,
                                admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body["updated_at"] = now_iso()
    if body.get("is_default"):
        await db.rating_criteria_sets.update_many({"_id": {"$ne": ObjectId(sid)}},
                                                    {"$set": {"is_default": False}})
    r = await db.rating_criteria_sets.update_one({"_id": ObjectId(sid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Criteria set not found")
    return _out(await db.rating_criteria_sets.find_one({"_id": ObjectId(sid)}))


@router.delete("/rating-criteria/{sid}")
async def delete_criteria_set(sid: str, admin=Depends(require_role("admin"))):
    await db.rating_criteria_sets.delete_one({"_id": ObjectId(sid)})
    return {"ok": True}


class MultiRatingIn(BaseModel):
    vendor_ref: str
    criteria_set_id: str
    rater_type: Literal["admin", "vendor", "platform"] = "admin"
    rater_email: Optional[str] = None
    rater_vendor_ref: Optional[str] = None    # if rater_type=vendor (blind)
    scores: dict                              # {criterion_code: int}
    comment: Optional[str] = None


@router.post("/ratings/multi")
async def submit_multi_rating(payload: MultiRatingIn,
                                admin=Depends(require_role("admin", "reviewer"))):
    """Record one rating event with per-criterion scores. Aggregate is
    recomputed on read (see /ratings/aggregate/{vendor_ref})."""
    s = await db.rating_criteria_sets.find_one({"_id": ObjectId(payload.criteria_set_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Criteria set not found")
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    # Normalise: enforce scale bounds
    scale_by_code = {c["code"]: (c["scale_min"], c["scale_max"], float(c.get("weight") or 1))
                      for c in s.get("criteria") or []}
    weighted_total = 0.0
    weight_sum = 0.0
    for code, val in (doc.get("scores") or {}).items():
        if code not in scale_by_code:
            continue
        lo, hi, w = scale_by_code[code]
        v = max(lo, min(hi, float(val)))
        # normalise to 0..1 then weight
        span = max(1, hi - lo)
        weighted_total += ((v - lo) / span) * w
        weight_sum += w
    doc["score_out_of_100"] = round((weighted_total / weight_sum) * 100, 2) if weight_sum else 0
    res = await db.vendor_multi_ratings.insert_one(doc)
    return _out(await db.vendor_multi_ratings.find_one({"_id": res.inserted_id}))


@router.get("/ratings/aggregate/{vendor_ref}")
async def rating_aggregate(vendor_ref: str,
                             admin=Depends(require_role("admin", "reviewer", "auditor"))):
    rows = [r async for r in db.vendor_multi_ratings.find({"vendor_ref": vendor_ref})]
    if not rows:
        return {"vendor_ref": vendor_ref, "count": 0, "average_score": None, "raters": []}
    avg = round(sum(r.get("score_out_of_100") or 0 for r in rows) / len(rows), 2)
    return {"vendor_ref": vendor_ref, "count": len(rows), "average_score": avg,
            "raters": [{"type": r.get("rater_type"),
                         "score": r.get("score_out_of_100"),
                         "created_at": r.get("created_at")} for r in rows]}
