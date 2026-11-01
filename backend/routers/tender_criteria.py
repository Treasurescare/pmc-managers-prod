"""Tender Criteria Builder — structured pass/fail and scored criteria per tender, answered by suppliers in the bid."""
import json
import re
import secrets
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
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
        if self.proof_required and not (self.proof or "").strip():
            self.proof = "Supporting document"
        self.id = self.id or secrets.token_hex(6)
        return self


class CriteriaIn(BaseModel):
    criteria: List[CriterionIn] = Field(max_length=60)
    fx_rule: Optional[str] = Field(default=None, max_length=300)


async def _notice(ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": ref}, {"notice_ref": 1, "is_published": 1, "tender_criteria": 1,
                                                        "criteria_fx_rule": 1, "title": 1, "description": 1,
                                                        "primary_document": 1, "budget_currency": 1, "origin": 1,
                                                        "prepared_by_vendor_id": 1, "review_status": 1,
                                                        "criteria_ai_check": 1})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    return n


def _view(n: dict) -> dict:
    return {"notice_ref": n["notice_ref"], "criteria": n.get("tender_criteria") or [],
            "fx_rule": n.get("criteria_fx_rule"), "locked": bool(n.get("is_published")),
            "ai_check": n.get("criteria_ai_check")}


def has_must_pass(n: dict) -> bool:
    return any(c.get("kind") == "must_pass" for c in (n.get("tender_criteria") or []))


@router.get("/templates")
async def templates():
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
    return await _store(n, body, admin)


async def _store(n: dict, body: "CriteriaIn", actor: dict) -> dict:
    ref = n["notice_ref"]
    crit = [c.model_dump() for c in body.criteria]
    ids = [c["id"] for c in crit]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Two criteria share the same id")
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {"tender_criteria": crit, "criteria_fx_rule": body.fx_rule,
                                                             "criteria_updated_at": now_iso()},
                                                    "$unset": {"criteria_ai_check": ""}})
    await audit_log("tender.criteria_saved", actor, "notice", ref, {"count": len(crit),
                    "must_pass": sum(1 for c in crit if c["kind"] == "must_pass")})
    n.update({"tender_criteria": crit, "criteria_fx_rule": body.fx_rule})
    n.pop("criteria_ai_check", None)
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
    return await _suggest(await _notice(ref), admin)


async def _suggest(n: dict, actor: dict) -> dict:
    ref = n["notice_ref"]
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
        if it.get("answer_type") != "number":
            it.update({"operator": None, "threshold": None, "full_points_at": None})
            if it.get("kind") == "scored":
                it["scoring"] = "evaluator"
        it["needs_review"] = it.get("answer_type") == "number" and (it.get("threshold") is None or not it.get("unit"))
        out.append(it)
    await audit_log("tender.criteria_ai_suggest", actor, "notice", ref, {"found": len(out)})
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



# ---------- supplier-prepared tenders: the preparing supplier enters criteria before review ----------

async def _own_vendor_tender(ref: str, vendor: dict) -> dict:
    n = await _notice(ref)
    if n.get("origin") != "vendor" or n.get("prepared_by_vendor_id") != vendor["id"]:
        raise HTTPException(status_code=403, detail="This is not your tender.")
    return n


@router.get("/{ref}/mine")
async def vendor_get(ref: str, vendor=Depends(current_vendor)):
    return _view(await _own_vendor_tender(ref, vendor))


@router.put("/{ref}/mine")
async def vendor_save(ref: str, body: CriteriaIn, vendor=Depends(current_vendor)):
    n = await _own_vendor_tender(ref, vendor)
    if n.get("review_status") not in ("draft", "changes_requested") or n.get("is_published"):
        raise HTTPException(status_code=409, detail="Criteria can only be changed while the tender is a draft or returned for changes.")
    return await _store(n, body, vendor)


@router.post("/{ref}/mine/ai-suggest")
async def vendor_suggest(ref: str, vendor=Depends(current_vendor)):
    return await _suggest(await _own_vendor_tender(ref, vendor), vendor)


# ---------- AI consistency check: do the criteria match the tender document? ----------

_CHECK_SYSTEM = (
    "You compare a tender document with the structured bidder criteria entered for it. Return ONLY JSON: "
    '{"verdict":"match|issues","issues":[{"criterion":str|null,"problem":str,"document_says":str|null}],'
    '"missing_from_criteria":[str]}. Report: thresholds, units, currencies or periods that differ from the document; '
    "criteria not supported by the document; requirements stated in the document but missing from the criteria. "
    "Be specific and short. Do not invent requirements."
)


@router.post("/{ref}/ai-check")
async def ai_check(ref: str, admin=Depends(require_role("admin", "reviewer"))):
    n = await _notice(ref)
    crit = n.get("tender_criteria") or []
    if not crit:
        raise HTTPException(status_code=409, detail="No criteria have been entered for this tender yet.")
    text = await _tender_text(n)
    if len(text.strip()) < 80:
        raise HTTPException(status_code=409, detail="There isn't enough tender text to check the criteria against.")
    from routers.tender_pro import _llm_complete
    slim = [{k: c.get(k) for k in ("title", "kind", "answer_type", "operator", "threshold", "unit", "period", "proof")} for c in crit]
    raw = await _llm_complete(_CHECK_SYSTEM, f"TENDER DOCUMENT:\n{text}\n\nCRITERIA ENTERED:\n{json.dumps(slim)}")
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        res = json.loads(m.group(0)) if m else None
    except ValueError:
        res = None
    if not isinstance(res, dict) or "verdict" not in res:
        raise HTTPException(status_code=502, detail="The AI check didn't return a clear answer. Please run it again.")
    out = {"verdict": "issues" if (res.get("issues") or res.get("missing_from_criteria")) else "match",
           "issues": (res.get("issues") or [])[:30], "missing_from_criteria": (res.get("missing_from_criteria") or [])[:30],
           "checked_at": now_iso(), "checked_by": admin.get("email")}
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {"criteria_ai_check": out}})
    await audit_log("tender.criteria_ai_check", admin, "notice", ref, {"verdict": out["verdict"], "issues": len(out["issues"])})
    return out


# ---------- Stage 2: automatic qualification at technical opening ----------

def _meets(op: str, v: float, t: float) -> bool:
    return v >= t if op == "gte" else v <= t if op == "lte" else abs(v - t) < 1e-9


def evaluate(criteria: list, answers: list, docs: list) -> dict:
    by_id = {a.get("criterion_id"): a.get("value") for a in answers or []}
    proofs = {d.get("criterion_id") for d in docs or [] if d.get("criterion_id")}
    results, failed, auto_pts, max_pts = [], False, 0.0, 0.0
    for c in criteria:
        v = by_id.get(c["id"])
        r = {"criterion_id": c["id"], "title": c["title"], "kind": c["kind"], "value": v, "unit": c.get("unit"),
             "rule": f"{c.get('operator')} {c.get('threshold')} {c.get('unit') or ''}".strip() if c["answer_type"] == "number" else
                     ("yes" if c["answer_type"] == "yes_no" else "written"),
             "proof_supplied": c["id"] in proofs}
        if c.get("proof_required") and c["id"] not in proofs:
            r.update(result="fail" if c["kind"] == "must_pass" else "points", points=0.0, reason="Required proof was not supplied")
        elif c["kind"] == "must_pass":
            if c["answer_type"] == "number":
                ok = v is not None and _meets(c["operator"], float(v), float(c["threshold"]))
                r.update(result="pass" if ok else "fail", reason=None if ok else
                         f"Declared {f'{float(v):,.0f}' if v is not None else 'nothing'} {c.get('unit') or ''}; needs {dict(gte='at least', lte='at most', eq='exactly')[c['operator']]} {c['threshold']:,} {c.get('unit') or ''}".strip())
            else:
                ok = v is True
                r.update(result="pass" if ok else "fail", reason=None if ok else "Answered No or did not answer")
        elif c.get("scoring") == "auto":
            mp = float(c["max_points"])
            t, f = float(c["threshold"]), float(c["full_points_at"])
            x = float(v) if v is not None else None
            if x is None:
                frac = 0.0
            elif f == t:
                frac = 1.0 if _meets(c["operator"], x, t) else 0.0
            else:
                frac = max(0.0, min(1.0, (x - t) / (f - t)))
            r.update(result="points", points=round(mp * frac, 2), max_points=mp)
        else:
            r.update(result="pending", points=None, max_points=float(c["max_points"]), reason="To be marked by evaluators")
        if c["kind"] == "scored":
            max_pts += float(c["max_points"])
            auto_pts += r.get("points") or 0.0
        failed = failed or r["result"] == "fail"
        results.append(r)
    return {"system_status": "not_qualified" if failed else "qualified", "results": results,
            "auto_points": round(auto_pts, 2), "max_points": round(max_pts, 2), "evaluated_at": now_iso()}


def final_status(q: dict) -> str:
    if q.get("decision"):
        return q["decision"]
    return "doubt_raised" if any(not d.get("resolved") for d in q.get("doubts") or []) else q["system_status"]


QUAL_ROLES = ("admin", "committee_member", "reviewer", "auditor")


async def _committee_member(ref: str, admin: dict) -> None:
    c = await db.committees.find_one({"notice_ref": ref, "status": "open"})
    members = {x for x in [(c or {}).get("chairperson_id"), *((c or {}).get("member_ids") or [])] if x}
    if admin.get("id") not in members:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can do this")


@router.get("/{ref}/qualification")
async def qualification(ref: str, _=Depends(require_role(*QUAL_ROLES))):
    n = await _notice(ref)
    rows = []
    async for b in db.bids.find({"notice_ref": ref, "qualification": {"$exists": True}}).sort("submitted_at", 1):
        q = b["qualification"]
        rows.append({"bid_id": str(b["_id"]), "bid_ref": b.get("bid_ref"), "supplier": b.get("company_name") or b.get("vendor_email"),
                     "status": final_status(q), **{k: q.get(k) for k in ("system_status", "results", "auto_points", "max_points",
                                                                           "evaluated_at", "doubts", "decision", "decision_note",
                                                                           "evaluator_scores")}})
    return {"notice_ref": ref, "criteria_count": len(n.get("tender_criteria") or []), "bids": rows}


class DoubtIn(BaseModel):
    criterion_id: str
    reason: str = Field(min_length=10, max_length=1000)


class ResolveIn(BaseModel):
    decision: Literal["uphold", "disqualify"]
    note: str = Field(min_length=5, max_length=1000)


class ScoreIn(BaseModel):
    criterion_id: str
    points: float = Field(ge=0)
    note: Optional[str] = Field(default=None, max_length=500)


async def _qual_bid(ref: str, bid_id: str) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id), "notice_ref": ref}) if ObjectId.is_valid(bid_id) else None
    if not b or not b.get("qualification"):
        raise HTTPException(status_code=404, detail="No qualification result for this bid yet")
    if b.get("commercial_unsealed_at"):
        raise HTTPException(status_code=409, detail="Price envelopes are already open; qualification is final")
    return b


async def _sync_clear(b: dict, q: dict) -> None:
    st = final_status(q)
    upd = {"qualification": q}
    if st == "qualified":
        upd["technical_cleared_at"] = b.get("technical_cleared_at") or now_iso()
        await db.bids.update_one({"_id": b["_id"]}, {"$set": upd})
    else:
        await db.bids.update_one({"_id": b["_id"]}, {"$set": upd, "$unset": {"technical_cleared_at": ""}})


@router.post("/{ref}/bids/{bid_id}/doubt")
async def raise_doubt(ref: str, bid_id: str, body: DoubtIn, admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    await _committee_member(ref, admin)
    b = await _qual_bid(ref, bid_id)
    q = b["qualification"]
    if not any(r["criterion_id"] == body.criterion_id for r in q.get("results") or []):
        raise HTTPException(status_code=422, detail="That criterion is not part of this tender")
    if q.get("decision"):
        raise HTTPException(status_code=409, detail="The committee has already decided on this bid")
    q.setdefault("doubts", []).append({"criterion_id": body.criterion_id, "reason": body.reason, "by": admin.get("email"),
                                       "at": now_iso(), "resolved": False})
    await _sync_clear(b, q)
    await audit_log("qualification.doubt_raised", admin, "bid", b.get("bid_ref"), {"criterion": body.criterion_id, "reason": body.reason})
    return {"status": final_status(q)}


@router.post("/{ref}/bids/{bid_id}/resolve")
async def resolve_doubt(ref: str, bid_id: str, body: ResolveIn, admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    await _committee_member(ref, admin)
    b = await _qual_bid(ref, bid_id)
    q = b["qualification"]
    if not any(not d.get("resolved") for d in q.get("doubts") or []):
        raise HTTPException(status_code=409, detail="There is no open doubt on this bid. The system result can't be changed directly.")
    for d in q["doubts"]:
        d.update(resolved=True, resolved_by=admin.get("email"), resolved_at=now_iso())
    if body.decision == "disqualify":
        q.update(decision="disqualified", decision_note=body.note, decided_by=admin.get("email"), decided_at=now_iso())
    else:
        q["upheld_note"] = body.note
    await _sync_clear(b, q)
    await audit_log(f"qualification.doubt_{body.decision}", admin, "bid", b.get("bid_ref"), {"note": body.note})
    return {"status": final_status(q)}


@router.post("/{ref}/bids/{bid_id}/score")
async def evaluator_score(ref: str, bid_id: str, body: ScoreIn, admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    await _committee_member(ref, admin)
    b = await _qual_bid(ref, bid_id)
    q = b["qualification"]
    r = next((x for x in q["results"] if x["criterion_id"] == body.criterion_id), None)
    if not r or r["result"] not in ("pending", "scored_by_evaluators"):
        raise HTTPException(status_code=422, detail="This criterion is not marked by evaluators")
    if body.points > (r.get("max_points") or 0):
        raise HTTPException(status_code=422, detail=f"Maximum is {r.get('max_points')} points")
    scores = q.setdefault("evaluator_scores", {}).setdefault(body.criterion_id, {})
    scores[admin["id"]] = {"by": admin.get("email"), "points": body.points, "note": body.note, "at": now_iso()}
    pts = [s["points"] for s in scores.values()]
    r.update(result="scored_by_evaluators", points=round(sum(pts) / len(pts), 2), reason=f"Average of {len(pts)} evaluator mark(s)")
    q["auto_points"] = round(sum((x.get("points") or 0) for x in q["results"] if x["kind"] == "scored"), 2)
    await db.bids.update_one({"_id": b["_id"]}, {"$set": {"qualification": q}})
    await audit_log("qualification.evaluator_score", admin, "bid", b.get("bid_ref"), {"criterion": body.criterion_id, "points": body.points})
    return {"points": r["points"]}


# ---------- supplier tenders built from templates (Tender Builder) ----------

async def _own_template(tid: str, request: Request, read: bool = False) -> tuple:
    from routers._tender_access import assert_can_edit_doc, assert_can_read_doc, tender_principal, write_principal
    p = await (tender_principal(request) if read else write_principal(request))
    doc = await db.tender_templates.find_one({"_id": ObjectId(tid)}) if ObjectId.is_valid(tid) else None
    if not doc:
        raise HTTPException(status_code=404, detail="Tender not found")
    (assert_can_read_doc if read else assert_can_edit_doc)(p, doc)
    return doc, p


def _tpl_view(doc: dict) -> dict:
    return {"notice_ref": str(doc["_id"]), "criteria": doc.get("tender_criteria") or [], "fx_rule": doc.get("criteria_fx_rule"),
            "locked": doc.get("review_status") in ("submitted", "approved"), "ai_check": None}


@router.get("/template/{tid}/mine")
async def template_get(tid: str, request: Request):
    doc, _ = await _own_template(tid, request, read=True)
    return _tpl_view(doc)


@router.put("/template/{tid}/mine")
async def template_save(tid: str, body: CriteriaIn, request: Request):
    doc, p = await _own_template(tid, request)
    if doc.get("review_status") in ("submitted", "approved"):
        raise HTTPException(status_code=409, detail="Criteria can only be changed while the tender is a draft or returned for changes.")
    crit = [c.model_dump() for c in body.criteria]
    if len({c["id"] for c in crit}) != len(crit):
        raise HTTPException(status_code=422, detail="Two criteria share the same id")
    await db.tender_templates.update_one({"_id": doc["_id"]}, {"$set": {"tender_criteria": crit, "criteria_fx_rule": body.fx_rule}})
    await audit_log("tender_template.criteria_saved", p, "tender_template", tid, {"count": len(crit)})
    doc.update(tender_criteria=crit, criteria_fx_rule=body.fx_rule)
    return _tpl_view(doc)


@router.post("/template/{tid}/mine/ai-suggest")
async def template_suggest(tid: str, request: Request):
    doc, p = await _own_template(tid, request)
    h = doc.get("header") or {}
    body = " ".join(re.sub(r"<[^>]+>", " ", str(s.get("body") or s.get("html") or "")) for s in doc.get("sections") or [] if isinstance(s, dict))
    fake = {"notice_ref": tid, "title": h.get("work_title") or doc.get("name"), "description": f"{h.get('work_description') or ''}\n{body}"}
    return await _suggest(fake, p)

