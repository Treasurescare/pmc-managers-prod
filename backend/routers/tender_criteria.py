"""Tender Criteria Builder — structured pass/fail and scored criteria per tender, answered by suppliers in the bid."""
import json
import re
import secrets
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from audit import audit_log
from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor
from security import require_role

router = APIRouter(prefix="/api/v1/tender-criteria", tags=["tender-criteria"])

PREFILL_FIELDS = {"country": "Country of registration", "registration_number": "Company registration number",
                  "year_established": "Year established", "annual_turnover": "Annual turnover"}

TEMPLATES = [
    {"title": "Average annual turnover", "category": "financial", "answer_type": "number", "operator": "gte",
     "threshold": 1000000, "unit": "USD", "period": "Last 3 financial years",
     "proof": "Audited financial statements for each year", "proof_required": True, "kind": "must_pass",
     "consortium_rule": "lead", "prefill_field": "annual_turnover"},
    {"title": "Net worth", "category": "financial", "answer_type": "number", "operator": "gte", "threshold": 0,
     "unit": "USD", "period": "Last audited year", "proof": "Audited balance sheet", "proof_required": True,
     "kind": "must_pass", "consortium_rule": "lead"},
    {"title": "Similar projects completed", "category": "experience", "answer_type": "number", "operator": "gte",
     "threshold": 3, "unit": "projects", "period": "Last 5 years", "proof": "Completion certificates or client letters",
     "proof_required": True, "kind": "must_pass", "consortium_rule": "lead"},
    {"title": "Value of largest similar project", "category": "experience", "answer_type": "number", "operator": "gte",
     "threshold": 500000, "unit": "USD", "period": "Last 5 years", "proof": "Contract or completion certificate",
     "proof_required": True, "kind": "must_pass", "consortium_rule": "lead"},
    {"title": "Years in business", "category": "legal", "answer_type": "number", "operator": "gte", "threshold": 3,
     "unit": "years", "proof": "Certificate of incorporation", "proof_required": True, "kind": "must_pass",
     "consortium_rule": "each"},
    {"title": "ISO 9001 quality certification", "category": "technical", "answer_type": "yes_no",
     "proof": "Valid certificate", "proof_required": True, "kind": "must_pass", "consortium_rule": "combined"},
    {"title": "Qualified key staff", "category": "technical", "answer_type": "number", "operator": "gte",
     "threshold": 5, "unit": "staff", "proof": "CVs of key staff", "proof_required": True, "kind": "scored",
     "max_points": 10, "scoring": "auto", "full_points_at": 15, "consortium_rule": "combined"},
    {"title": "Methodology and work plan", "category": "technical", "answer_type": "text",
     "proof": "Methodology document", "proof_required": True, "kind": "scored", "max_points": 20,
     "scoring": "evaluator", "consortium_rule": "combined"},
]


class CriterionIn(BaseModel):
    id: Optional[str] = None
    title: str = Field(min_length=3, max_length=200)
    category: Literal["financial", "experience", "technical", "legal", "other"] = "other"
    answer_type: Literal["number", "yes_no", "text"]
    operator: Optional[Literal["gte", "lte", "eq"]] = None
    threshold: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=40)
    period: Optional[str] = Field(default=None, max_length=120)
    proof: Optional[str] = Field(default=None, max_length=300)
    proof_required: bool = False
    kind: Literal["must_pass", "scored"]
    max_points: Optional[float] = None
    scoring: Optional[Literal["auto", "evaluator"]] = None
    full_points_at: Optional[float] = None
    consortium_rule: Literal["lead", "combined", "each"] = "each"
    prefill_field: Optional[str] = None

    @model_validator(mode="after")
    def _check(self):
        t = self.title
        if self.answer_type == "number":
            if not self.operator or self.threshold is None or not (self.unit or "").strip():
                raise ValueError(f"'{t}': a number criterion needs a rule, a value and a unit/currency")
        if self.answer_type == "text" and self.kind == "must_pass":
            raise ValueError(f"'{t}': a written answer can't be pass/fail — make it scored by evaluators, or use yes/no")
        if self.kind == "scored":
            if not self.max_points or self.max_points <= 0:
                raise ValueError(f"'{t}': a scored criterion needs maximum points")
            if self.answer_type == "text":
                self.scoring = "evaluator"
            self.scoring = self.scoring or "evaluator"
            if self.scoring == "auto":
                if self.answer_type != "number" or self.full_points_at is None:
                    raise ValueError(f"'{t}': automatic scoring needs a number answer and the value that earns full points")
        if self.prefill_field and self.prefill_field not in PREFILL_FIELDS:
            self.prefill_field = None
        self.id = self.id or secrets.token_hex(6)
        return self


class CriteriaIn(BaseModel):
    criteria: List[CriterionIn] = Field(max_length=60)
    fx_rule: Optional[str] = Field(default=None, max_length=300)


async def _notice(ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": ref}, {"notice_ref": 1, "is_published": 1, "tender_criteria": 1,
                                                        "criteria_fx_rule": 1, "title": 1, "description": 1,
                                                        "primary_document": 1, "budget_currency": 1})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    return n


def _view(n: dict) -> dict:
    return {"notice_ref": n["notice_ref"], "criteria": n.get("tender_criteria") or [],
            "fx_rule": n.get("criteria_fx_rule"), "locked": bool(n.get("is_published"))}


def has_must_pass(n: dict) -> bool:
    return any(c.get("kind") == "must_pass" for c in (n.get("tender_criteria") or []))


@router.get("/templates")
async def templates(_=Depends(require_role("admin", "reviewer"))):
    return {"templates": TEMPLATES, "prefill_fields": PREFILL_FIELDS}


@router.get("/{ref}")
async def public_criteria(ref: str):
    n = await _notice(ref)
    if not n.get("is_published"):
        raise HTTPException(status_code=404, detail="Tender not found")
    return _view(n)


@router.get("/{ref}/admin")
async def admin_criteria(ref: str, _=Depends(require_role("admin", "reviewer"))):
    return _view(await _notice(ref))


@router.put("/{ref}")
async def save_criteria(ref: str, body: CriteriaIn, admin=Depends(require_role("admin"))):
    n = await _notice(ref)
    if n.get("is_published"):
        raise HTTPException(status_code=409, detail="This tender is live. Criteria can only change through a corrigendum sent to all suppliers.")
    crit = [c.model_dump() for c in body.criteria]
    ids = [c["id"] for c in crit]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Two criteria share the same id")
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {"tender_criteria": crit, "criteria_fx_rule": body.fx_rule,
                                                             "criteria_updated_at": now_iso()}})
    await audit_log("tender.criteria_saved", admin, "notice", ref, {"count": len(crit),
                    "must_pass": sum(1 for c in crit if c["kind"] == "must_pass")})
    n.update({"tender_criteria": crit, "criteria_fx_rule": body.fx_rule})
    return _view(n)


async def _tender_text(n: dict) -> str:
    text = f"Title: {n.get('title') or ''}\n\n{n.get('description') or ''}"
    key = (n.get("primary_document") or {}).get("key")
    if key:
        up = await db.uploads.find_one({"key": key}, {"data_b64": 1, "sealed": 1})
        if up and up.get("data_b64") and not up.get("sealed"):
            import base64
            from routers.tender_pro import _extract_text_from_upload
            try:
                text += "\n\n" + _extract_text_from_upload(key, base64.b64decode(up["data_b64"]))
            except Exception:
                pass
    return text[:60000]


_AI_SYSTEM = (
    "You extract bidder qualification criteria from tender documents. Return ONLY JSON: "
    '{"criteria":[{"title":str,"category":"financial|experience|technical|legal|other","answer_type":"number|yes_no|text",'
    '"operator":"gte|lte|eq|null","threshold":number|null,"unit":str|null,"period":str|null,"proof":str|null,'
    '"proof_required":bool,"kind":"must_pass|scored","max_points":number|null,"scoring":"auto|evaluator|null",'
    '"full_points_at":number|null,"consortium_rule":"lead|combined|each"}]}. '
    "Only include criteria actually stated in the document; never invent thresholds. If a figure is missing, set threshold null. "
    "Use ISO currency codes as unit for money. Written/qualitative items must be kind=scored, scoring=evaluator. "
    "If there are none, return {\"criteria\":[]}."
)


@router.post("/{ref}/ai-suggest")
async def ai_suggest(ref: str, admin=Depends(require_role("admin"))):
    n = await _notice(ref)
    text = await _tender_text(n)
    if len(text.strip()) < 80:
        return {"criteria": [], "note": "There isn't enough tender text to read criteria from. Add them below."}
    from routers.tender_pro import _llm_complete
    raw = await _llm_complete(_AI_SYSTEM, text)
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        items = json.loads(m.group(0)).get("criteria", []) if m else []
    except (ValueError, AttributeError):
        items = []
    out = []
    for it in items[:40]:
        if not isinstance(it, dict) or not it.get("title"):
            continue
        it = {k: (None if v in ("null", "") else v) for k, v in it.items()}
        it["id"] = secrets.token_hex(6)
        it["needs_review"] = it.get("answer_type") == "number" and (it.get("threshold") is None or not it.get("unit"))
        out.append(it)
    await audit_log("tender.criteria_ai_suggest", admin, "notice", ref, {"found": len(out)})
    return {"criteria": out, "note": None if out else "No clear criteria were found in the tender document. Add them below."}


async def _vendor_profile(vendor_id: str, email: str) -> dict:
    v = await db.vendors.find_one({"_id": ObjectId(vendor_id)}) if ObjectId.is_valid(vendor_id) else None
    r = await db.registrations.find_one({"email": email, "status": "approved"}) or {}
    src = {**r, **(v or {})}
    return {k: src.get(k) for k in PREFILL_FIELDS if src.get(k) not in (None, "")}


@router.get("/{ref}/prefill")
async def prefill(ref: str, vendor=Depends(current_vendor)):
    n = await _notice(ref)
    prof = await _vendor_profile(vendor["id"], vendor["email"])
    out = {}
    for c in n.get("tender_criteria") or []:
        f = c.get("prefill_field")
        if f and f in prof:
            out[c["id"]] = prof[f]
    return {"values": out}


def _num(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def clean_answers(criteria: list, answers: list, docs: list) -> list:
    """Validate supplier answers against the tender's criteria. Raises 422 listing what's missing."""
    by_id = {a.get("criterion_id"): a for a in answers or [] if isinstance(a, dict)}
    proof_for = {d.get("criterion_id") for d in docs or [] if d.get("criterion_id")}
    out, missing = [], []
    for c in criteria:
        a = by_id.get(c["id"]) or {}
        v = a.get("value")
        if c["answer_type"] == "number":
            v = _num(v)
        elif c["answer_type"] == "yes_no":
            v = v if isinstance(v, bool) else (str(v).lower() in ("yes", "true", "1") if v not in (None, "") else None)
        else:
            v = (str(v).strip()[:4000] or None) if v is not None else None
        if v is None:
            if c["kind"] == "must_pass" or c.get("scoring") == "auto":
                missing.append(f"{c['title']} (answer)")
        if c.get("proof_required") and c["id"] not in proof_for:
            missing.append(f"{c['title']} (proof)")
        out.append({"criterion_id": c["id"], "value": v})
    if missing:
        raise HTTPException(status_code=422, detail="Please answer every tender criterion: " + "; ".join(missing))
    return out
