"""AI proof reading at technical opening + unanimous committee accept/reject per must-pass proof."""
import json
import os
import re
import secrets
import tempfile
import base64
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from bid_seal import dec_bytes
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/tender-criteria", tags=["proof-review"])
COMMITTEE = Depends(require_role("admin", "committee_member", "reviewer"))
READABLE = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}
EXT_MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
_PROMPT = """You check proof documents in a public tender. Read the attached file(s) and decide whether they back up the supplier's declared answer.
Criterion: {title}
Rule: {rule}
Proof asked for: {proof}
Supplier declared: {declared}
Reply with ONLY JSON: {{"verdict": "match" | "mismatch" | "unclear", "found_value": "<the figure or answer the document shows, or null>", "details": "<2-3 short sentences: what the document is, its date/period, and why it matches or not>"}}"""


def init_reviews(q: dict) -> None:
    q["proof_reviews"] = {r["criterion_id"]: {"ai_status": "pending", "votes": {}, "status": "pending"}
                          for r in q.get("results") or [] if r.get("kind") == "must_pass" and r.get("proof_supplied")}


def pending_reviews(q: dict) -> int:
    return sum(1 for v in (q.get("proof_reviews") or {}).values() if v.get("status") == "pending")


async def _members(ref: str) -> list:
    c = await db.committees.find_one({"notice_ref": ref, "status": "open"}) or {}
    return [m for m in dict.fromkeys([c.get("chairperson_id"), *(c.get("member_ids") or [])]) if m]


async def _files(b: dict, cid: str) -> list:
    out = []
    for d in b.get("documents") or []:
        if d.get("criterion_id") != cid or not d.get("key"):
            continue
        u = await db.uploads.find_one({"key": d["key"]})
        if not u:
            continue
        mime = u.get("content_type") or EXT_MIME.get(os.path.splitext((d.get("filename") or "").lower())[1], "")
        body = base64.b64decode(u["data_b64"])
        out.append((d.get("filename") or d["key"], mime, dec_bytes(body) if u.get("sealed") else body))
    return out


async def _ask_ai(r: dict, crit: dict, files: list) -> dict:
    from emergentintegrations.llm.chat import FileContentWithMimeType, LlmChat, UserMessage
    readable = [f for f in files if f[1] in READABLE]
    if not readable:
        return {"ai_status": "unreadable", "ai": {"verdict": "unclear", "found_value": None,
                "details": "The AI can read PDF and image files only. Please check this proof by hand."}}
    declared = r.get("value")
    if r.get("member_values"):
        declared = "; ".join(f"{m['member']}: {m['value']}" for m in r["member_values"])
    paths = []
    try:
        for name, mime, body in readable:
            fd, p = tempfile.mkstemp(suffix=os.path.splitext(name)[1] or ".pdf")
            with os.fdopen(fd, "wb") as fh:
                fh.write(body)
            paths.append((p, mime))
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"proof-{secrets.token_hex(6)}",
                       system_message="You are a careful procurement document checker. Never invent figures.").with_model("gemini", "gemini-3.1-pro-preview")
        raw = await chat.send_message(UserMessage(text=_PROMPT.format(title=r["title"], rule=r.get("rule"), proof=crit.get("proof_hint") or "supporting document",
                                                                      declared=f"{declared} {r.get('unit') or ''}".strip()),
                                                  file_contents=[FileContentWithMimeType(file_path=p, mime_type=m) for p, m in paths]))
    finally:
        for p, _ in paths:
            os.remove(p)
    m = re.search(r"\{.*\}", raw or "", re.S)
    data = json.loads(m.group(0)) if m else {}
    verdict = data.get("verdict") if data.get("verdict") in ("match", "mismatch", "unclear") else "unclear"
    return {"ai_status": "done", "ai": {"verdict": verdict, "found_value": data.get("found_value"),
                                        "details": str(data.get("details") or "")[:800], "files": [f[0] for f in readable]}}


async def review_proofs(ref: str) -> int:
    n = await db.notices.find_one({"notice_ref": ref}, {"tender_criteria": 1})
    crit = {c["id"]: c for c in (n or {}).get("tender_criteria") or []}
    done = 0
    async for b in db.bids.find({"notice_ref": ref, "qualification.proof_reviews": {"$exists": True}, "commercial_unsealed_at": None}):
        for r in b["qualification"].get("results") or []:
            pr = b["qualification"]["proof_reviews"].get(r["criterion_id"])
            if not pr or pr.get("ai_status") not in ("pending", "failed"):
                continue
            try:
                upd = await _ask_ai(r, crit.get(r["criterion_id"], {}), await _files(b, r["criterion_id"]))
            except Exception as e:
                upd = {"ai_status": "failed", "ai": {"verdict": "unclear", "found_value": None, "details": f"The AI could not read this proof ({type(e).__name__}). Check it by hand or retry."}}
            await db.bids.update_one({"_id": b["_id"]}, {"$set": {f"qualification.proof_reviews.{r['criterion_id']}.{k}": v for k, v in {**upd, "ai_at": now_iso()}.items()}})
            done += 1
    return done


@router.post("/{ref}/proof-ai/run")
async def rerun_ai(ref: str, admin=COMMITTEE):
    if admin.get("id") not in await _members(ref) and admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only this tender's committee can do this")
    count = await review_proofs(ref)
    await audit_log("qualification.proof_ai_run", admin, "notice", ref, {"read": count})
    return {"read": count}


class VoteIn(BaseModel):
    decision: Literal["accept", "reject"]
    comment: Optional[str] = Field(default=None, max_length=1000)


@router.post("/{ref}/bids/{bid_id}/proofs/{cid}/vote")
async def vote(ref: str, bid_id: str, cid: str, body: VoteIn, admin=COMMITTEE):
    from routers.tender_criteria import _sync_clear
    members = await _members(ref)
    if admin.get("id") not in members:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can decide on proofs")
    if body.decision == "reject" and len((body.comment or "").strip()) < 5:
        raise HTTPException(status_code=422, detail="Add a comment (at least 5 characters) explaining why the proof is rejected")
    b = await db.bids.find_one({"_id": ObjectId(bid_id), "notice_ref": ref}) if ObjectId.is_valid(bid_id) else None
    q = (b or {}).get("qualification") or {}
    pr = (q.get("proof_reviews") or {}).get(cid)
    if not pr:
        raise HTTPException(status_code=404, detail="No proof review for this criterion")
    if b.get("commercial_unsealed_at") or pr["status"] != "pending" or q.get("decision"):
        raise HTTPException(status_code=409, detail="This proof has already been decided")
    pr["votes"][admin["id"]] = {"by": admin.get("email"), "decision": body.decision, "comment": (body.comment or "").strip() or None, "at": now_iso()}
    title = next((r["title"] for r in q.get("results") or [] if r["criterion_id"] == cid), cid)
    if set(pr["votes"]) >= set(members):
        rejected = [v for v in pr["votes"].values() if v["decision"] == "reject"]
        pr.update(status="rejected" if rejected else "accepted", decided_at=now_iso())
        if rejected:
            q.update(decision="disqualified", decided_at=now_iso(), decided_by="committee",
                     decision_note=f"Proof for \"{title}\" rejected by the committee: " + " | ".join(f"{v['by']}: {v['comment']}" for v in rejected))
    await _sync_clear(b, q)
    await audit_log(f"qualification.proof_{body.decision}", admin, "bid", b.get("bid_ref"), {"criterion": cid, "comment": body.comment, "final": pr["status"]})
    return {"status": pr["status"], "votes": len(pr["votes"]), "needed": len(members)}
