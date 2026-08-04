"""Wave 31 — Bidder Q&A.

Public "Ask a clarification" thread anchored to a Notice. Bidders submit
questions (name/email + question text), admin replies, and answered
threads become visible to *every* bidder so nobody gets an information
advantage — mirrors CPPP / GeM behaviour.

Wire:
* POST  /api/v1/notices/{notice_ref}/qa            (public) submit question
* GET   /api/v1/notices/{notice_ref}/qa            (public) list answered
* GET   /api/v1/notices/{notice_ref}/qa/admin      (admin) list all (incl. pending)
* POST  /api/v1/notices/{notice_ref}/qa/{qid}/reply (admin) post the reply
"""
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/notices", tags=["notice-qa"])

_EMAIL_MASK = re.compile(r"(.).*(@.*)")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _mask_email(e: Optional[str]) -> str:
    if not e:
        return ""
    return _EMAIL_MASK.sub(r"\1***\2", e)


def _out_public(d: dict) -> dict:
    """Publicly-safe shape — mask the asker's email so nobody dox's competitors."""
    return {
        "id": str(d["_id"]),
        "notice_ref": d["notice_ref"],
        "asker_name": d.get("asker_name") or "Anonymous",
        "asker_email_masked": _mask_email(d.get("asker_email")),
        "question": d.get("question"),
        "answer": d.get("answer"),
        "answered_by": d.get("answered_by"),
        "asked_at": d.get("asked_at"),
        "answered_at": d.get("answered_at"),
    }


def _out_admin(d: dict) -> dict:
    o = _out_public(d)
    o["asker_email"] = d.get("asker_email")
    return o


class QuestionIn(BaseModel):
    asker_name: str = Field(min_length=1, max_length=120)
    asker_email: str = Field(min_length=5, max_length=200)
    question: str = Field(min_length=8, max_length=2000)


class ReplyIn(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


@router.post("/{notice_ref}/qa")
async def post_question(notice_ref: str, payload: QuestionIn):
    """PUBLIC — bidder submits a clarification question."""
    if not _EMAIL_RE.match(payload.asker_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address")
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    doc = {
        "notice_ref": notice_ref,
        "tenant_id": n.get("tenant_id"),
        "asker_name": payload.asker_name,
        "asker_email": payload.asker_email,
        "question": payload.question,
        "answer": None,
        "answered_by": None,
        "asked_at": now_iso(),
        "answered_at": None,
    }
    r = await db.notice_qa.insert_one(doc)
    doc["_id"] = r.inserted_id
    return {"ok": True, "id": str(r.inserted_id), "status": "pending"}


@router.get("/{notice_ref}/qa")
async def list_public_qa(notice_ref: str):
    """PUBLIC — only answered questions are exposed."""
    cursor = db.notice_qa.find({"notice_ref": notice_ref, "answer": {"$ne": None}})\
                          .sort("answered_at", -1)
    items = [_out_public(d) async for d in cursor]
    return {"items": items, "total": len(items)}


@router.get("/{notice_ref}/qa/admin")
async def list_admin_qa(notice_ref: str,
                         admin=Depends(require_role("admin", "reviewer", "committee_member"))):
    cursor = db.notice_qa.find({"notice_ref": notice_ref}).sort("asked_at", -1)
    items = [_out_admin(d) async for d in cursor]
    return {"items": items, "pending": sum(1 for i in items if not i.get("answer"))}


@router.post("/{notice_ref}/qa/{qid}/reply")
async def reply_question(notice_ref: str, qid: str, payload: ReplyIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    try:
        q = await db.notice_qa.find_one({"_id": ObjectId(qid), "notice_ref": notice_ref})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed question id")
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    await db.notice_qa.update_one(
        {"_id": ObjectId(qid)},
        {"$set": {"answer": payload.answer, "answered_by": admin.get("email"),
                   "answered_at": now_iso()}},
    )
    await audit_log("notice_qa.reply", admin, "notice", notice_ref, {"qid": qid})
    return {"ok": True}
