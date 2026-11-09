"""AI proof reading at technical opening + unanimous committee accept/reject per must-pass proof."""
import asyncio
import base64
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
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
    from pmc_lib.llm.chat import FileContentWithMimeType, LlmChat, UserMessage
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
    stale = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    done = 0
    async for b in db.bids.find({"notice_ref": ref, "qualification.proof_reviews": {"$exists": True}, "commercial_unsealed_at": None}):
        for r in b["qualification"].get("results") or []:
            if r["criterion_id"] not in b["qualification"]["proof_reviews"]:
                continue
            p = f"qualification.proof_reviews.{r['criterion_id']}"
            claimed = await db.bids.update_one(
                {"_id": b["_id"], "$or": [{f"{p}.ai_status": {"$in": ["pending", "failed"]}},
                                         {f"{p}.ai_status": "running", f"{p}.ai_started_at": {"$lt": stale}}]},
                {"$set": {f"{p}.ai_status": "running", f"{p}.ai_started_at": now_iso()}})
            if not claimed.modified_count:
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
    asyncio.create_task(review_proofs(ref))
    await audit_log("qualification.proof_ai_run", admin, "notice", ref, {})
    return {"started": True}


class VoteIn(BaseModel):
    decision: Literal["accept", "reject"]
    comment: Optional[str] = Field(default=None, max_length=1000)


@router.post("/{ref}/bids/{bid_id}/proofs/{cid}/vote")
async def vote(ref: str, bid_id: str, cid: str, body: VoteIn, admin=COMMITTEE):
    members = await _members(ref)
    if admin.get("id") not in members:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can decide on proofs")
    if body.decision == "reject" and len((body.comment or "").strip()) < 5:
        raise HTTPException(status_code=422, detail="Add a comment (at least 5 characters) explaining why the proof is rejected")
    oid = ObjectId(bid_id) if ObjectId.is_valid(bid_id) else None
    p = f"qualification.proof_reviews.{cid}"
    if not oid or not await db.bids.find_one({"_id": oid, "notice_ref": ref, p: {"$exists": True}}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="No proof review for this criterion")
    entry = {"by": admin.get("email"), "decision": body.decision, "comment": (body.comment or "").strip() or None, "at": now_iso()}
    res = await db.bids.update_one({"_id": oid, f"{p}.status": "pending", "commercial_unsealed_at": None, "qualification.decision": {"$exists": False}},
                                   {"$set": {f"{p}.votes.{admin['id']}": entry}})
    if not res.matched_count:
        raise HTTPException(status_code=409, detail="This proof has already been decided")
    b = await db.bids.find_one({"_id": oid})
    q = b["qualification"]
    pr = q["proof_reviews"][cid]
    status = "pending"
    if set(pr["votes"]) >= set(members):
        rejected = [v for v in pr["votes"].values() if v["decision"] == "reject"]
        status = "rejected" if rejected else "accepted"
        upd, extra = {f"{p}.status": status, f"{p}.decided_at": now_iso()}, {}
        if rejected:
            idx, res = next(((i, x) for i, x in enumerate(q.get("results") or []) if x["criterion_id"] == cid), (None, {}))
            title = res.get("title", cid)
            note = f"Proof for \"{title}\" rejected by the committee: " + " | ".join(f"{v['by']}: {v['comment']}" for v in rejected)
            if idx is not None:
                upd.update({f"qualification.results.{idx}.result": "fail", f"qualification.results.{idx}.reason": note})
            opt = q.get("optional_summary")
            knock = bool(res.get("mandatory", True) or not opt)
            if knock:
                upd.update({"qualification.decision": "disqualified", "qualification.decided_at": now_iso(), "qualification.decided_by": "committee",
                            "qualification.decision_note": note})
                extra = {"$unset": {"technical_cleared_at": ""}}
        done = await db.bids.update_one({"_id": oid, f"{p}.status": "pending"}, {"$set": upd, **extra})
        if not done.modified_count:
            status = (await db.bids.find_one({"_id": oid}))["qualification"]["proof_reviews"][cid]["status"]
        elif rejected and not knock:
            fresh = (await db.bids.find_one({"_id": oid}))["qualification"]
            passed = sum(1 for x in fresh["results"] if x["kind"] == "must_pass" and not x.get("mandatory", True) and x["result"] == "pass")
            need = fresh["optional_summary"]["required"]
            await db.bids.update_one({"_id": oid}, {"$set": {"qualification.optional_summary.passed": passed}})
            if passed < need:
                await db.bids.update_one({"_id": oid, "qualification.decision": {"$exists": False}},
                                         {"$set": {"qualification.decision": "disqualified", "qualification.decided_at": now_iso(), "qualification.decided_by": "committee",
                                                   "qualification.decision_note": f"{note} — now meets {passed} of the {need} optional criteria required"},
                                          "$unset": {"technical_cleared_at": ""}})
    await audit_log(f"qualification.proof_{body.decision}", admin, "bid", b.get("bid_ref"), {"criterion": cid, "comment": body.comment, "final": status})
    return {"status": status, "votes": len(pr["votes"]), "needed": len(members)}



def _report_pdf(n: dict, bids: list, names: dict) -> bytes:
    import io
    from xml.sax.saxutils import escape as x
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from pdf_brand import logo_flowable
    from routers.tender_criteria import final_status
    ss = getSampleStyleSheet()
    sm = ss["BodyText"].clone("sm", fontSize=7.5, leading=9.5)
    P = lambda t: Paragraph(x(str(t if t is not None else "—")), sm)  # noqa: E731
    out = [logo_flowable(), Paragraph(f"Proof check report — {x(n['notice_ref'])}", ss["Title"]),
           Paragraph(x(n.get("title") or ""), ss["Heading3"]),
           Paragraph(f"Generated {now_iso()[:16].replace('T', ' ')} UTC · Committee: {x(', '.join(names.values()) or '—')}", sm), Spacer(1, 4 * mm)]
    for b in bids:
        q = b.get("qualification") or {}
        out.append(Paragraph(f"{x(b.get('company_name') or b.get('vendor_email') or '')} · {x(b.get('bid_ref') or '')} — <b>{x(final_status(q).replace('_', ' '))}</b>", ss["Heading4"]))
        if q.get("decision_note"):
            out.append(Paragraph(f"Committee decision: {x(q['decision_note'])}", sm))
        if q.get("optional_summary"):
            o = q["optional_summary"]
            out.append(Paragraph(f"Optional criteria met: {o['passed']} of {o['total']} (at least {o['required']} required)", sm))
        rows = [[P(h) for h in ("Criterion", "Declared", "System result", "Proof files", "AI finding", "Committee decisions")]]
        files = {}
        for d in b.get("documents") or []:
            if d.get("criterion_id"):
                files.setdefault(d["criterion_id"], []).append(d.get("filename") or d.get("key"))
        for r in q.get("results") or []:
            pr = (q.get("proof_reviews") or {}).get(r["criterion_id"]) or {}
            ai = pr.get("ai") or {}
            ai_txt = f"{ai.get('verdict', '—')}; shows: {ai.get('found_value') or '—'}. {ai.get('details') or ''}" if pr else "Not reviewed"
            votes = "; ".join(f"{v['by']}: {v['decision']}{(' — ' + v['comment']) if v.get('comment') else ''}" for v in (pr.get("votes") or {}).values())
            rows.append([P(f"{r['title']} ({'mandatory' if r.get('mandatory', True) else 'optional'}; {r.get('rule')})"),
                         P(f"{r.get('value')} {r.get('unit') or ''}"), P(f"{r.get('result')}{(': ' + r['reason']) if r.get('reason') else ''}"),
                         P(", ".join(files.get(r["criterion_id"], [])) or "none"), P(ai_txt),
                         P(f"{pr.get('status', '—')}{(' · ' + votes) if votes else ''}")])
        t = Table(rows, colWidths=[30 * mm, 18 * mm, 30 * mm, 26 * mm, 42 * mm, 36 * mm], repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE7D2")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        out += [t, Spacer(1, 5 * mm)]
    if not bids:
        out.append(Paragraph("No bids have been through technical opening yet.", sm))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                      title=f"Proof check report {n['notice_ref']}").build(out)
    return buf.getvalue()


@router.get("/{ref}/proof-report.pdf")
async def proof_report(ref: str, admin=Depends(require_role("admin", "committee_member", "reviewer", "auditor"))):
    n = await db.notices.find_one({"notice_ref": ref}, {"notice_ref": 1, "title": 1})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    bids = [b async for b in db.bids.find({"notice_ref": ref, "qualification": {"$exists": True}}).sort("submitted_at", 1)]
    names = {}
    ids = [ObjectId(m) for m in await _members(ref) if ObjectId.is_valid(m)]
    async for u in db.admin_users.find({"_id": {"$in": ids}}, {"email": 1, "full_name": 1}):
        names[str(u["_id"])] = u.get("full_name") or u.get("email")
    pdf = _report_pdf(n, bids, names)
    await audit_log("qualification.proof_report", admin, "notice", ref, {"bids": len(bids)})
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="proof-check-{ref}.pdf"'})
