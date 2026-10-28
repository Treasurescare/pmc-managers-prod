"""Governance controls — due-diligence hardening (R7).

Closes the integrity gaps surfaced in the PMC portal questionnaire:
  * Manual-exceptions register  — one reviewable log of every bypass / waiver /
    override / skipped stage, sourced from a dedicated collection AND mirrored
    to the hash-chained audit ledger.
  * Buyer public/private classification — with a two-person (SoD) verify step.
  * Integrity committee + collusion indicators — raise/hold, committee review,
    resolution, and an audited+disclosed senior override.
  * Fee-waiver workflow — request/approve with maker-checker separation.
  * Per-country legal register — board-visible legal approval status.
  * Incident register + published SLA — public disclosure of critical-moment
    failures.

Single-tenant staff-RBAC app: authorization is role-based via `require_role`,
every state change is written to the audit ledger, and maker-checker (SoD)
separation is enforced where the questionnaire demands independence.
"""
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import secrets

from db import db
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/governance-controls", tags=["governance-controls"])

# Published service standard for critical moments (bid deadlines / openings).
SLA_STATEMENT = {
    "bid_acceptance": "Bids are accepted until the published deadline to the second, server-timestamped.",
    "live_opening_uptime_target": "99.5% monthly availability for live bid-opening rooms.",
    "live_opening_failover": "Live rooms stream over SSE with automatic polling fallback; if streaming fails the opening continues on a manual, audit-logged close.",
    "incident_disclosure": "Any failure affecting a bid deadline or opening is logged and, where bidders are affected, publicly disclosed on this page.",
    "support_response_critical": "Critical incidents (deadline/opening affected) are acknowledged within 1 hour.",
}


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


async def record_exception(kind: str, actor: Optional[dict], target_type: str,
                           target_id: str, reason: str, details: Optional[dict] = None) -> str:
    """Append a manual exception to the register AND the audit ledger.

    `kind` ∈ kyc_bypass | fee_waiver | buyer_classification_override |
    integrity_override | stage_skip | other
    """
    ref = f"EXC-{secrets.token_hex(5).upper()}"
    row = {
        "exception_ref": ref,
        "kind": kind,
        "actor_id": (actor or {}).get("id"),
        "actor_email": (actor or {}).get("email"),
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "details": details or {},
        "at": now_iso(),
    }
    await db.manual_exceptions.insert_one(row)
    await audit_log(f"exception.{kind}", actor, target_type, target_id,
                    {"exception_ref": ref, "reason": reason, **(details or {})})
    return ref


# ======================= Manual-exceptions register =======================

@router.get("/exceptions")
async def list_exceptions(kind: Optional[str] = None, limit: int = 200,
                          admin=Depends(require_role("admin", "auditor", "reviewer"))):
    q = {"kind": kind} if kind else {}
    cur = db.manual_exceptions.find(q).sort("at", -1).limit(min(limit, 500))
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


# ======================= Buyer public/private classification =======================

class BuyerClassifyIn(BaseModel):
    notice_ref: str
    buyer_name: str = Field(min_length=2, max_length=200)
    buyer_type: Literal["public_sector", "private_sector"]
    basis: str = Field(min_length=3, max_length=500)


class BuyerVerifyIn(BaseModel):
    notice_ref: str
    agree: bool
    note: Optional[str] = None
    override_type: Optional[Literal["public_sector", "private_sector"]] = None


@router.get("/buyer-classifications")
async def list_buyer_classifications(status: Optional[str] = None,
                                     admin=Depends(require_role("admin", "auditor", "reviewer", "committee_member", "legal_counsel"))):
    q = {"status": status} if status else {}
    cur = db.buyer_classifications.find(q).sort("classified_at", -1)
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/buyer-classifications")
async def classify_buyer(payload: BuyerClassifyIn,
                         admin=Depends(require_role("admin", "reviewer"))):
    doc = {
        "notice_ref": payload.notice_ref,
        "buyer_name": payload.buyer_name.strip(),
        "buyer_type": payload.buyer_type,
        "basis": payload.basis.strip(),
        "status": "pending_verification",
        "classified_by": admin["email"],
        "classified_at": now_iso(),
        "verified_by": None,
        "verified_at": None,
    }
    await db.buyer_classifications.update_one(
        {"notice_ref": payload.notice_ref}, {"$set": doc}, upsert=True)
    await audit_log("buyer.classify", admin, "notice", payload.notice_ref,
                    {"buyer_type": payload.buyer_type, "basis": payload.basis})
    return {"ok": True, "status": "pending_verification"}


@router.post("/buyer-classifications/verify")
async def verify_buyer_classification(payload: BuyerVerifyIn,
                                      admin=Depends(require_role("admin", "auditor", "legal_counsel"))):
    rec = await db.buyer_classifications.find_one({"notice_ref": payload.notice_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="No classification to verify")
    # Segregation of duties — the verifier must be a different person.
    if (rec.get("classified_by") or "").lower() == admin["email"].lower():
        raise HTTPException(status_code=403,
            detail="Separation of duties: the person who classified the buyer cannot verify it. A second officer must verify.")
    final_type = rec.get("buyer_type")
    overridden = False
    if payload.override_type and payload.override_type != rec.get("buyer_type"):
        final_type = payload.override_type
        overridden = True
    status = "verified" if payload.agree or overridden else "rejected"
    await db.buyer_classifications.update_one(
        {"notice_ref": payload.notice_ref},
        {"$set": {"status": status, "buyer_type": final_type,
                  "verified_by": admin["email"], "verified_at": now_iso(),
                  "verify_note": payload.note}})
    await audit_log("buyer.classify_verify", admin, "notice", payload.notice_ref,
                    {"status": status, "buyer_type": final_type, "overridden": overridden})
    if overridden:
        await record_exception("buyer_classification_override", admin, "notice",
                               payload.notice_ref,
                               payload.note or "Verifier overrode the proposed buyer type",
                               {"from": rec.get("buyer_type"), "to": final_type})
    return {"ok": True, "status": status, "buyer_type": final_type}


# ======================= Integrity committee + collusion =======================

class IntegrityRaiseIn(BaseModel):
    notice_ref: str
    title: str = Field(min_length=3, max_length=200)
    reason: str = Field(min_length=5, max_length=2000)


class IntegrityReviewIn(BaseModel):
    case_ref: str
    vote: Literal["uphold", "dismiss"]
    note: Optional[str] = None


class IntegrityResolveIn(BaseModel):
    case_ref: str
    resolution: Literal["upheld", "dismissed"]
    note: Optional[str] = None


class IntegrityOverrideIn(BaseModel):
    case_ref: str
    decision: Literal["upheld", "dismissed"]
    reason: str = Field(min_length=10, max_length=2000)


@router.get("/integrity-cases")
async def list_integrity_cases(status: Optional[str] = None,
                               admin=Depends(require_role("admin", "committee_member", "auditor", "reviewer"))):
    q = {"status": status} if status else {}
    cur = db.integrity_cases.find(q).sort("raised_at", -1)
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/integrity-cases")
async def raise_integrity_case(payload: IntegrityRaiseIn,
                               admin=Depends(require_role("admin", "committee_member", "reviewer", "auditor"))):
    ref = f"INT-{secrets.token_hex(4).upper()}"
    doc = {
        "case_ref": ref, "notice_ref": payload.notice_ref,
        "title": payload.title.strip(), "reason": payload.reason.strip(),
        "status": "open", "raised_by": admin["email"], "raised_at": now_iso(),
        "reviews": [], "resolution": None, "resolved_by": None, "resolved_at": None,
        "senior_override": None,
    }
    await db.integrity_cases.insert_one(doc)
    await audit_log("integrity.raise", admin, "notice", payload.notice_ref,
                    {"case_ref": ref, "title": payload.title})
    return {"ok": True, "case_ref": ref}


@router.post("/integrity-cases/review")
async def review_integrity_case(payload: IntegrityReviewIn,
                                admin=Depends(require_role("admin", "committee_member"))):
    rec = await db.integrity_cases.find_one({"case_ref": payload.case_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="Integrity case not found")
    if rec.get("status") not in ("open", "under_review"):
        raise HTTPException(status_code=409, detail=f"Case already {rec.get('status')}")
    reviews = [r for r in (rec.get("reviews") or []) if r.get("by") != admin["email"]]
    reviews.append({"by": admin["email"], "vote": payload.vote,
                    "note": payload.note, "at": now_iso()})
    await db.integrity_cases.update_one(
        {"case_ref": payload.case_ref},
        {"$set": {"reviews": reviews, "status": "under_review"}})
    await audit_log("integrity.review", admin, "integrity_case", payload.case_ref,
                    {"vote": payload.vote})
    return {"ok": True, "reviews": reviews}


@router.post("/integrity-cases/resolve")
async def resolve_integrity_case(payload: IntegrityResolveIn,
                                 admin=Depends(require_role("admin", "committee_member"))):
    rec = await db.integrity_cases.find_one({"case_ref": payload.case_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="Integrity case not found")
    await db.integrity_cases.update_one(
        {"case_ref": payload.case_ref},
        {"$set": {"status": payload.resolution, "resolution": payload.resolution,
                  "resolved_by": admin["email"], "resolved_at": now_iso(),
                  "resolution_note": payload.note}})
    await audit_log("integrity.resolve", admin, "integrity_case", payload.case_ref,
                    {"resolution": payload.resolution})
    return {"ok": True, "status": payload.resolution}


@router.post("/integrity-cases/senior-override")
async def senior_override_integrity_case(payload: IntegrityOverrideIn,
                                         admin=Depends(require_role("admin"))):
    """A senior officer may overrule the committee — but only on the record:
    the override, its author and its reason are written to the ledger, logged
    as a manual exception, and flagged publicly-disclosable."""
    rec = await db.integrity_cases.find_one({"case_ref": payload.case_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="Integrity case not found")
    override = {"by": admin["email"], "decision": payload.decision,
                "reason": payload.reason, "at": now_iso(), "disclosed": True}
    await db.integrity_cases.update_one(
        {"case_ref": payload.case_ref},
        {"$set": {"status": "overridden", "senior_override": override,
                  "resolution": payload.decision}})
    await record_exception("integrity_override", admin, "integrity_case",
                           payload.case_ref, payload.reason,
                           {"decision": payload.decision,
                            "committee_reviews": rec.get("reviews") or []})
    return {"ok": True, "status": "overridden", "override": override}


@router.get("/collusion/{notice_ref}")
async def collusion_indicators(notice_ref: str,
                               admin=Depends(require_role("admin", "committee_member", "auditor", "reviewer"))):
    """Surface INDICATORS of possible collusion between bidders on one notice —
    shared contact details, addresses, bank accounts and repeated co-bidding.
    These are prompts for human review, NOT proof of wrongdoing."""
    bids = await db.bids.find({"notice_ref": notice_ref}).to_list(500)
    refs = [b.get("vendor_ref") for b in bids if b.get("vendor_ref")]
    vendors = {}
    if refs:
        async for v in db.vendors.find({"vendor_ref": {"$in": refs}}):
            vendors[v.get("vendor_ref")] = v

    def _norm(x):
        return (str(x or "")).strip().lower()

    def _domain(email):
        e = _norm(email)
        return e.split("@", 1)[1] if "@" in e else ""

    flags: List[dict] = []
    # Shared signals across the bidders on this notice.
    buckets = {"email_domain": {}, "phone": {}, "address": {}, "bank_account": {}}
    for b in bids:
        vr = b.get("vendor_ref")
        v = vendors.get(vr, {})
        sigs = {
            "email_domain": _domain(v.get("email") or b.get("contact_email")),
            "phone": _norm(v.get("phone") or v.get("contact_phone")),
            "address": _norm(v.get("address") or v.get("registered_address")),
            "bank_account": _norm((v.get("bank") or {}).get("account_number") if isinstance(v.get("bank"), dict) else v.get("bank_account")),
        }
        label = v.get("company_name") or vr or b.get("company_name") or "Bidder"
        for key, val in sigs.items():
            if val:
                buckets[key].setdefault(val, []).append(label)

    readable = {"email_domain": "share an email domain", "phone": "share a phone number",
                "address": "share a registered address", "bank_account": "share a bank account"}
    for key, groups in buckets.items():
        for val, parties in groups.items():
            uniq = sorted(set(parties))
            if len(uniq) > 1:
                flags.append({"signal": key, "severity": "high" if key in ("bank_account", "address") else "medium",
                              "message": f"{len(uniq)} bidders {readable[key]} ({val})",
                              "parties": uniq})

    # Repeated historical co-bidding between the same vendors.
    if len(refs) > 1:
        co = {}
        async for ob in db.bids.find({"vendor_ref": {"$in": refs}}):
            co.setdefault(ob.get("notice_ref"), set()).add(ob.get("vendor_ref"))
        pair_counts = {}
        for nref, vset in co.items():
            vl = sorted(v for v in vset if v)
            for i in range(len(vl)):
                for j in range(i + 1, len(vl)):
                    pair_counts[(vl[i], vl[j])] = pair_counts.get((vl[i], vl[j]), 0) + 1
        for (a, b2), c in pair_counts.items():
            if c >= 3:
                na = (vendors.get(a) or {}).get("company_name") or a
                nb = (vendors.get(b2) or {}).get("company_name") or b2
                flags.append({"signal": "co_bidding", "severity": "medium",
                              "message": f"{na} and {nb} have bid on the same notice {c} times",
                              "parties": [na, nb]})

    return {"notice_ref": notice_ref, "bidder_count": len(bids),
            "flag_count": len(flags), "flags": flags,
            "disclaimer": "Indicators for human review only — not evidence of collusion."}


# ======================= Fee-waiver workflow =======================

class FeeWaiverRequestIn(BaseModel):
    subject_type: Literal["vendor", "notice", "engagement"]
    subject_ref: str
    fee_type: str = Field(min_length=2, max_length=80)
    amount: float = Field(ge=0)
    currency: str = Field(default="USD", max_length=8)
    reason: str = Field(min_length=5, max_length=1000)


class FeeWaiverDecideIn(BaseModel):
    waiver_ref: str
    decision: Literal["approved", "rejected"]
    note: Optional[str] = None


@router.get("/fee-waivers")
async def list_fee_waivers(status: Optional[str] = None,
                           admin=Depends(require_role("admin", "accounting", "auditor", "reviewer"))):
    q = {"status": status} if status else {}
    cur = db.fee_waivers.find(q).sort("requested_at", -1)
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/fee-waivers")
async def request_fee_waiver(payload: FeeWaiverRequestIn,
                             admin=Depends(require_role("admin", "accounting", "reviewer"))):
    ref = f"FW-{secrets.token_hex(4).upper()}"
    doc = {
        "waiver_ref": ref, "subject_type": payload.subject_type,
        "subject_ref": payload.subject_ref, "fee_type": payload.fee_type.strip(),
        "amount": payload.amount, "currency": payload.currency,
        "reason": payload.reason.strip(), "status": "pending",
        "requested_by": admin["email"], "requested_at": now_iso(),
        "decided_by": None, "decided_at": None, "decision_note": None,
    }
    await db.fee_waivers.insert_one(doc)
    await audit_log("fee_waiver.request", admin, payload.subject_type, payload.subject_ref,
                    {"waiver_ref": ref, "fee_type": payload.fee_type, "amount": payload.amount})
    return {"ok": True, "waiver_ref": ref}


@router.post("/fee-waivers/decide")
async def decide_fee_waiver(payload: FeeWaiverDecideIn,
                            admin=Depends(require_role("admin", "accounting"))):
    rec = await db.fee_waivers.find_one({"waiver_ref": payload.waiver_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="Fee waiver not found")
    if rec.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Waiver already {rec.get('status')}")
    # Maker-checker — the approver cannot be the requester.
    if (rec.get("requested_by") or "").lower() == admin["email"].lower():
        raise HTTPException(status_code=403,
            detail="Separation of duties: the person who requested the waiver cannot approve it.")
    await db.fee_waivers.update_one(
        {"waiver_ref": payload.waiver_ref},
        {"$set": {"status": payload.decision, "decided_by": admin["email"],
                  "decided_at": now_iso(), "decision_note": payload.note}})
    await audit_log("fee_waiver.decide", admin, rec.get("subject_type"), rec.get("subject_ref"),
                    {"waiver_ref": payload.waiver_ref, "decision": payload.decision})
    if payload.decision == "approved":
        await record_exception("fee_waiver", admin, rec.get("subject_type"),
                               rec.get("subject_ref"),
                               payload.note or rec.get("reason") or "Fee waived",
                               {"waiver_ref": payload.waiver_ref, "fee_type": rec.get("fee_type"),
                                "amount": rec.get("amount"), "requested_by": rec.get("requested_by")})
    return {"ok": True, "status": payload.decision}


# ======================= Per-country legal register =======================

class LegalRegisterIn(BaseModel):
    country: str = Field(min_length=2, max_length=80)
    legal_status: Literal["approved", "pending", "blocked"]
    counsel_note: Optional[str] = None
    documents: Optional[List[dict]] = None


@router.get("/legal-register")
async def list_legal_register(admin=Depends(require_role("admin", "auditor", "reviewer", "legal_counsel", "committee_member"))):
    cur = db.legal_country_register.find({}).sort("country", 1)
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/legal-register")
async def upsert_legal_register(payload: LegalRegisterIn,
                                admin=Depends(require_role("admin", "legal_counsel"))):
    key = payload.country.strip()
    doc = {
        "country": key, "legal_status": payload.legal_status,
        "counsel_note": payload.counsel_note, "documents": payload.documents or [],
        "board_visible": True, "approved_by": admin["email"], "updated_at": now_iso(),
    }
    await db.legal_country_register.update_one(
        {"country": key}, {"$set": doc}, upsert=True)
    await audit_log("legal_register.upsert", admin, "country", key,
                    {"legal_status": payload.legal_status})
    return {"ok": True, "country": key, "legal_status": payload.legal_status}


# ======================= Incident register + SLA =======================

class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    severity: Literal["low", "medium", "high", "critical"]
    category: str = Field(min_length=2, max_length=80)
    impact: str = Field(min_length=3, max_length=2000)
    public_disclosure: bool = False
    public_statement: Optional[str] = None


class IncidentUpdateIn(BaseModel):
    incident_ref: str
    status: Literal["open", "monitoring", "resolved"]
    public_disclosure: Optional[bool] = None
    public_statement: Optional[str] = None


@router.get("/incidents")
async def list_incidents(admin=Depends(require_role("admin", "auditor", "reviewer", "committee_member"))):
    cur = db.incidents.find({}).sort("started_at", -1)
    items = [_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/incidents")
async def create_incident(payload: IncidentIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    ref = f"INC-{secrets.token_hex(4).upper()}"
    doc = {
        "incident_ref": ref, "title": payload.title.strip(),
        "severity": payload.severity, "category": payload.category.strip(),
        "impact": payload.impact.strip(), "status": "open",
        "public_disclosure": payload.public_disclosure,
        "public_statement": payload.public_statement,
        "started_at": now_iso(), "resolved_at": None,
        "created_by": admin["email"],
    }
    await db.incidents.insert_one(doc)
    await audit_log("incident.create", admin, "incident", ref,
                    {"severity": payload.severity, "category": payload.category})
    return {"ok": True, "incident_ref": ref}


@router.post("/incidents/update")
async def update_incident(payload: IncidentUpdateIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    rec = await db.incidents.find_one({"incident_ref": payload.incident_ref})
    if not rec:
        raise HTTPException(status_code=404, detail="Incident not found")
    updates = {"status": payload.status}
    if payload.status == "resolved":
        updates["resolved_at"] = now_iso()
    if payload.public_disclosure is not None:
        updates["public_disclosure"] = payload.public_disclosure
    if payload.public_statement is not None:
        updates["public_statement"] = payload.public_statement
    await db.incidents.update_one({"incident_ref": payload.incident_ref}, {"$set": updates})
    await audit_log("incident.update", admin, "incident", payload.incident_ref,
                    {"status": payload.status})
    return {"ok": True, "status": payload.status}


@router.get("/public/incidents")
async def public_incidents():
    """Public — disclosed incidents + the published SLA. No auth."""
    cur = db.incidents.find({"public_disclosure": True}).sort("started_at", -1).limit(50)
    items = []
    async for d in cur:
        items.append({
            "incident_ref": d.get("incident_ref"), "title": d.get("title"),
            "severity": d.get("severity"), "category": d.get("category"),
            "status": d.get("status"), "started_at": d.get("started_at"),
            "resolved_at": d.get("resolved_at"),
            "statement": d.get("public_statement"),
        })
    return {"sla": SLA_STATEMENT, "incidents": items, "count": len(items)}
