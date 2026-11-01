"""Committee bid opening: envelopes open only on/after the opening date and only when every member approves."""
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from audit import audit_log
from bid_seal import EMD_CONFIRMED, _parse, dec_text, opening_at
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/bid-opening", tags=["bid-opening"])
VIEW = Depends(require_role("admin", "reviewer", "committee_member", "auditor"))
LIVE = {"$nin": ["withdrawn", "rejected", "draft"]}
SIGN_STATEMENT = ("I approve the opening of these envelopes as a member of the tender committee and confirm I have no "
                  "conflict of interest. This is my electronic signature.")


class ApproveIn(BaseModel):
    stage: Literal["technical", "commercial"]
    signer_name: str = Field(min_length=3, max_length=120)
    consent: bool

    @field_validator("signer_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Type your full name (at least 3 characters)")
        return v


async def _ctx(notice_ref: str):
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    c = await db.committees.find_one({"notice_ref": notice_ref, "status": "open"})
    return n, c


def _members(c) -> list:
    if not c:
        return []
    return [m for m in dict.fromkeys([c.get("chairperson_id"), *(c.get("member_ids") or [])]) if m]


async def _blockers(n: dict, c, stage: str) -> list:
    now = datetime.now(timezone.utc)
    out = []
    if not c:
        out.append("No open committee has been formed for this tender")
    dl = _parse(n.get("submission_deadline"))
    if dl and now < dl:
        out.append("Bid submission is still open")
    oa = opening_at(n)
    if oa and now < oa:
        out.append(f"Bid opening date is {oa.isoformat()[:16].replace('T', ' ')} UTC")
    if stage == "commercial" and not n.get("technical_opened_at"):
        out.append("The technical envelopes must be opened first")
    if stage == "commercial" and n.get("technical_opened_at") and not n.get("commercial_opened_at"):
        base = {"notice_ref": n["notice_ref"], "seal_v": 1, "auction_id": None, "technical_unsealed_at": {"$ne": None}}
        if not await db.bids.count_documents({**base, "technical_cleared_at": {"$ne": None}, "status": LIVE}):
            out.append("No bid has passed technical evaluation yet")
        if n.get("tender_criteria"):
            pending = await db.bids.count_documents({**base, "status": LIVE, "qualification.doubts": {"$elemMatch": {"resolved": False}},
                                                     "qualification.decision": {"$exists": False}})
            if pending:
                out.append(f"The committee has raised a doubt on {pending} bid(s) — resolve it first")
            pending = 0
        else:
            pending = await db.bids.count_documents({**base, "technical_cleared_at": None, "status": LIVE})
        if pending:
            out.append(f"Technical evaluation is still pending for {pending} bid(s) — clear or reject each one first")
    if n.get(f"{stage}_opened_at"):
        out.append(f"The {stage} envelopes are already open")
    return out


@router.get("/{notice_ref}")
async def opening_state(notice_ref: str, admin=VIEW):
    n, c = await _ctx(notice_ref)
    members = _members(c)
    names = {}
    if members:
        async for u in db.admin_users.find({"_id": {"$in": [ObjectId(m) for m in members if ObjectId.is_valid(m)]}},
                                           {"email": 1, "full_name": 1, "name": 1}):
            names[str(u["_id"])] = u.get("full_name") or u.get("name") or u.get("email")
    q = {"notice_ref": notice_ref, "seal_v": 1, "auction_id": None, "status": LIVE}
    stages = {}
    for st in ("technical", "commercial"):
        appr = (n.get("opening_approvals") or {}).get(st) or []
        done = {a["by_id"] for a in appr}
        stages[st] = {"opened_at": n.get(f"{st}_opened_at"), "blockers": await _blockers(n, c, st),
                      "approvals": appr, "pending": [{"id": m, "name": names.get(m, m)} for m in members if m not in done],
                      "i_can_approve": admin.get("id") in members and admin.get("id") not in done}
    return {"notice_ref": notice_ref, "opening_at": (opening_at(n) or None) and opening_at(n).isoformat(),
            "submission_deadline": n.get("submission_deadline"),
            "committee": [{"id": m, "name": names.get(m, m)} for m in members],
            "bids_total": await db.bids.count_documents(q),
            "bids_emd_confirmed": await db.bids.count_documents({**q, "status": {"$in": list(EMD_CONFIRMED)}}),
            "stages": stages}


@router.post("/{notice_ref}/approve")
async def approve_opening(notice_ref: str, body: ApproveIn, request: Request,
                          admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    if not body.consent:
        raise HTTPException(status_code=422, detail="Tick the box to sign the opening electronically")
    n, c = await _ctx(notice_ref)
    members = _members(c)
    if admin.get("id") not in members:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can approve the opening")
    blockers = await _blockers(n, c, body.stage)
    if blockers:
        raise HTTPException(status_code=412, detail="; ".join(blockers))
    appr = (n.get("opening_approvals") or {}).get(body.stage) or []
    if any(a["by_id"] == admin["id"] for a in appr):
        raise HTTPException(status_code=409, detail="You have already approved this opening")
    appr.append({"by_id": admin["id"], "by": admin.get("email"), "at": now_iso(),
                 "signature": {"name": body.signer_name, "ip": (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
                               or (request.client.host if request.client else None),
                               "user_agent": (request.headers.get("user-agent") or "")[:200],
                               "statement": SIGN_STATEMENT}})
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {f"opening_approvals.{body.stage}": appr}})
    await audit_log(f"bid_opening.{body.stage}_approved", admin, "notice", notice_ref,
                    {"approved": len(appr), "required": len(members)})
    if {a["by_id"] for a in appr} >= set(members):
        opened = await _open(n, body.stage, admin)
        import asyncio
        asyncio.create_task(_email_record(notice_ref, body.stage, admin))
        return {"opened": True, "bids_opened": opened, "approvals": appr, "record_emailed": True}
    return {"opened": False, "approvals": appr, "remaining": len(set(members) - {a["by_id"] for a in appr})}


async def _open(n: dict, stage: str, admin: dict) -> int:
    ref, now = n["notice_ref"], now_iso()
    q = {"notice_ref": ref, "seal_v": 1, "auction_id": None, "status": LIVE}
    if stage == "technical":
        q["status"] = {"$in": list(EMD_CONFIRMED)}
    else:
        q |= {"technical_unsealed_at": {"$ne": None}, "technical_cleared_at": {"$ne": None}}
    count = 0
    async for b in db.bids.find(q):
        s = b.get("sealed") or {}
        if stage == "technical":
            upd = {"technical_notes": dec_text(s.get("technical_notes")), "technical_unsealed_at": now}
            crit = n.get("tender_criteria") or []
            if crit:
                import json as _json
                from routers.tender_criteria import evaluate
                ans = dec_text(s.get("criteria_answers_json"))
                q = evaluate(crit, _json.loads(ans) if ans else [], b.get("documents") or [])
                upd.update(criteria_answers_json=ans, qualification=q)
                if q["system_status"] == "qualified":
                    upd["technical_cleared_at"] = now
        else:
            price = dec_text(s.get("price_amount"))
            upd = {"price_amount": float(price) if price else None, "commercial_notes": dec_text(s.get("commercial_notes")),
                   "commercial_unsealed_at": now, "financial_opened_at": now, "financial_opened_by": "committee"}
        await db.bids.update_one({"_id": b["_id"]}, {"$set": upd})
        count += 1
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {f"{stage}_opened_at": now}})
    await audit_log(f"bid_opening.{stage}_opened", admin, "notice", ref, {"bids_opened": count})
    return count


# ---------- signed opening record ----------

def _esc(s) -> str:
    from html import escape
    return escape(str(s if s is not None else "—"))


def _ts(s) -> str:
    return _esc((str(s)[:16].replace("T", " ") + " UTC") if s else None)


def _qr_data_uri(text: str) -> str:
    import base64
    import io
    import qrcode
    buf = io.BytesIO()
    qrcode.make(text, box_size=4, border=1).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _qual_text(q) -> str:
    if not q:
        return None
    from routers.tender_criteria import final_status
    st = final_status(q)
    label = {"qualified": "Qualified", "not_qualified": "Not qualified", "disqualified": "Disqualified by committee",
             "doubt_raised": "Doubt raised"}.get(st, st)
    fails = [f"{r['title']}: {r.get('reason')}" for r in q.get("results") or [] if r.get("result") == "fail"]
    pts = f" · {q.get('auto_points')}/{q.get('max_points')} pts" if q.get("max_points") else ""
    return label + pts + (" — " + "; ".join(fails) if fails else "") + (f" — {q.get('decision_note')}" if q.get("decision_note") else "")


async def _record(n: dict, c) -> dict:
    bids = []
    vids = await db.bids.distinct("vendor_id", {"notice_ref": n["notice_ref"], "seal_v": 1})
    vnames = {str(v["_id"]): v.get("company_name") async for v in db.vendors.find(
        {"_id": {"$in": [ObjectId(x) for x in vids if x and ObjectId.is_valid(x)]}}, {"company_name": 1})}
    async for b in db.bids.find({"notice_ref": n["notice_ref"], "seal_v": 1, "auction_id": None}).sort("submitted_at", 1):
        bids.append({"bid_ref": b.get("bid_ref"), "vendor": vnames.get(b.get("vendor_id")) or b.get("vendor_email"),
                     "submitted_at": b.get("submitted_at") or b.get("created_at"), "status": b.get("status"),
                     "emd_confirmed": b.get("status") in EMD_CONFIRMED or bool(b.get("technical_unsealed_at")),
                     "technical_opened": bool(b.get("technical_unsealed_at")), "technical_cleared": bool(b.get("technical_cleared_at")),
                     "commercial_opened": bool(b.get("commercial_unsealed_at")),
                     "qualification": _qual_text(b.get("qualification")),
                     "price": f"{b.get('price_currency') or ''} {float(b['price_amount']):,.2f}" if b.get("commercial_unsealed_at") and b.get("price_amount") is not None else None})
    appr = n.get("opening_approvals") or {}
    return {"notice_ref": n["notice_ref"], "title": n.get("title"), "opening_at": (opening_at(n) or None) and opening_at(n).isoformat(),
            "submission_deadline": n.get("submission_deadline"), "committee_id": str(c["_id"]) if c else None,
            "technical_opened_at": n.get("technical_opened_at"), "commercial_opened_at": n.get("commercial_opened_at"),
            "approvals": {st: [{"by": a.get("by"), "name": (a.get("signature") or {}).get("name"), "at": a.get("at"),
                                "ip": (a.get("signature") or {}).get("ip")} for a in appr.get(st) or []] for st in ("technical", "commercial")},
            "bids": bids}


def _render_record(rec: dict, code: str, digest: str, ledger: dict, verify_url: str, issued_by: str, issued_at: str) -> bytes:
    from weasyprint import HTML
    from pdf_brand import brand_html

    def sig_rows(st):
        rows = rec["approvals"][st]
        if not rows:
            return "<tr><td colspan='4'>No approvals</td></tr>"
        return "".join(f"<tr><td><span class='sig'>{_esc(a['name'])}</span><br><small>{_esc(a['by'])}</small></td>"
                       f"<td>{_esc((a['at'] or '')[:19].replace('T', ' '))} UTC</td><td>{_esc(a['ip'])}</td><td>Signed electronically</td></tr>" for a in rows)
    bid_rows = "".join(
        f"<tr><td>{_esc(b['bid_ref'])}</td><td>{_esc(b['vendor'])}</td><td>{_esc((b['submitted_at'] or '')[:16].replace('T', ' '))}</td>"
        f"<td>{'Confirmed' if b['emd_confirmed'] else 'Not confirmed'}</td>"
        f"<td>{'Opened' if b['technical_opened'] else 'Sealed'}{' · cleared' if b['technical_cleared'] else ''}</td>"
        f"<td>{_esc(b.get('qualification') or '—')}</td>"
        f"<td>{'Opened' if b['commercial_opened'] else 'Sealed'}</td><td>{_esc(b['price']) if b['price'] else '—'}</td></tr>"
        for b in rec["bids"]) or "<tr><td colspan='7'>No sealed bids</td></tr>"
    html = f"""<html><head><style>
      @page {{ size:A4 landscape; margin:14mm; @bottom-center {{ content:"Record {code} · page " counter(page); font-size:8px; color:#777; }} }}
      body {{ font-family:Helvetica,Arial,sans-serif; font-size:10px; color:#14261F; }}
      h1 {{ font-size:18px; color:#0F3B2E; margin:0 0 4px; }} h2 {{ font-size:12px; color:#0F3B2E; margin:16px 0 6px; }}
      table {{ width:100%; border-collapse:collapse; }} th,td {{ border-bottom:1px solid rgba(15,59,46,.15); padding:5px 6px; text-align:left; vertical-align:top; }}
      th {{ font-size:8px; text-transform:uppercase; letter-spacing:1px; color:#5B6B63; }}
      .sig {{ font-family:'DejaVu Serif',serif; font-style:italic; font-size:14px; color:#0F3B2E; }}
      .stamp {{ display:flex; gap:14px; align-items:center; border:1.5px solid #0F3B2E; padding:8px 10px; margin-top:16px; }}
      .mono {{ font-family:'DejaVu Sans Mono',monospace; font-size:8px; word-break:break-all; }}
    </style></head><body>
      <h1>Bid opening record</h1>
      <div>{_esc(rec['title'])} · <b>{_esc(rec['notice_ref'])}</b></div>
      <div>Submission deadline: {_ts(rec['submission_deadline'])} · Bid opening date: {_ts(rec['opening_at'])}</div>
      <div>Technical envelopes opened: {_ts(rec['technical_opened_at'])} · Commercial envelopes opened: {_ts(rec['commercial_opened_at'])}</div>
      <h2>Committee signatures — technical opening</h2>
      <table><tr><th>Member</th><th>Signed at</th><th>IP address</th><th>Method</th></tr>{sig_rows('technical')}</table>
      <h2>Committee signatures — commercial opening</h2>
      <table><tr><th>Member</th><th>Signed at</th><th>IP address</th><th>Method</th></tr>{sig_rows('commercial')}</table>
      <p style="font-size:9px;color:#555">Each member signed: “{_esc(SIGN_STATEMENT)}”</p>
      <h2>Bids</h2>
      <table><tr><th>Bid</th><th>Supplier</th><th>Submitted</th><th>Deposit (escrow)</th><th>Technical</th><th>Qualification (system check)</th><th>Commercial</th><th>Quoted price</th></tr>{bid_rows}</table>
      <div class="stamp"><img src="{_qr_data_uri(verify_url)}" style="width:86px;height:86px"/>
        <div><b>Audit-ledger stamp</b> · Record code <b>{code}</b> · Ledger entry #{ledger.get('seq')}<br>
          Issued {issued_at[:19].replace('T', ' ')} UTC by {_esc(issued_by)}<br>
          Record fingerprint (SHA-256): <span class="mono">{digest}</span><br>
          Ledger hash: <span class="mono">{ledger.get('current_hash')}</span><br>
          Scan the QR code or open {_esc(verify_url)} to check this record has not been altered.</div></div>
    </body></html>"""
    return HTML(string=brand_html(html)).write_pdf()


async def _issue_record(notice_ref: str, admin: dict):
    import asyncio
    import hashlib
    import json
    import config
    n, c = await _ctx(notice_ref)
    if not n.get("technical_opened_at"):
        raise HTTPException(status_code=412, detail="The record is available once the technical envelopes are opened")
    rec = await _record(n, c)
    digest = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
    code = digest[:12].upper()
    existing = await db.opening_records.find_one({"code": code})
    issued_at = existing["issued_at"] if existing else now_iso()
    issued_by = existing["issued_by"] if existing else admin.get("email")
    if existing:
        ledger = existing["ledger"]
    else:
        ledger = await audit_log("bid_opening.record_issued", admin, "notice", notice_ref, {"code": code, "sha256": digest}) or {}
        try:
            await db.opening_records.insert_one({"code": code, "notice_ref": notice_ref, "sha256": digest, "record": rec,
                                                 "ledger": ledger, "issued_at": issued_at, "issued_by": issued_by})
        except DuplicateKeyError:
            existing = await db.opening_records.find_one({"code": code})
            ledger, issued_at, issued_by = existing["ledger"], existing["issued_at"], existing["issued_by"]
    verify_url = f"{config.FRONTEND_URL.rstrip('/')}/api/v1/bid-opening/verify/{code}"
    pdf = await asyncio.to_thread(_render_record, rec, code, digest, ledger, verify_url, issued_by, issued_at)
    return pdf, code, c, n


async def _email_record(notice_ref: str, stage: str, admin: dict) -> int:
    import base64
    import logging
    from emails import send_email, wrap
    try:
        pdf, code, c, n = await _issue_record(notice_ref, admin)
        ids = [ObjectId(m) for m in _members(c) if ObjectId.is_valid(m)]
        att = [{"filename": f"bid-opening-{notice_ref}-{code}.pdf", "content_b64": base64.b64encode(pdf).decode(),
                "content_type": "application/pdf"}]
        sent = 0
        async for u in db.admin_users.find({"_id": {"$in": ids}}, {"email": 1}):
            body = (f"<p>The {stage} envelopes for <b>{n.get('title') or notice_ref}</b> ({notice_ref}) were opened after every "
                    f"committee member signed. The signed opening record (code {code}) is attached.</p>")
            sent += bool(await send_email(u["email"], f"[PMC] Signed bid-opening record · {notice_ref}",
                                          wrap("Bid-opening record", body), attachments=att))
        await audit_log("bid_opening.record_emailed", admin, "notice", notice_ref, {"code": code, "stage": stage, "sent": sent})
        return sent
    except Exception:
        logging.getLogger(__name__).exception("opening record email failed for %s", notice_ref)
        return 0


@router.get("/{notice_ref}/record.pdf")
async def opening_record_pdf(notice_ref: str, admin=VIEW):
    from fastapi.responses import Response
    pdf, code, _c, _n = await _issue_record(notice_ref, admin)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="bid-opening-{notice_ref}-{code}.pdf"'})


@router.get("/verify/{code}")
async def verify_record(code: str):
    r = await db.opening_records.find_one({"code": code.upper()})
    if not r:
        return {"valid": False, "message": "No bid-opening record with this code exists. The document may be forged."}
    import hashlib
    import json
    from audit import _hash
    ev = await db.audit_events.find_one({"seq": r["ledger"].get("seq")})
    rec = r["record"]
    rec_ok = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest() == r["sha256"]
    ev_ok = False
    if ev:
        body = {k: v for k, v in ev.items() if k not in ("_id", "current_hash")}
        ev_ok = _hash(body) == ev.get("current_hash") == r["ledger"].get("current_hash") \
            and (ev.get("payload") or {}).get("sha256") == r["sha256"]
    ok = rec_ok and ev_ok
    return {"valid": ok, "code": r["code"], "notice_ref": r["notice_ref"], "title": rec.get("title"), "issued_at": r["issued_at"],
            "sha256": r["sha256"], "ledger_seq": r["ledger"].get("seq"),
            "signed_by": {st: [a.get("name") for a in v] for st, v in rec["approvals"].items()},
            "bids_opened": sum(1 for b in rec["bids"] if b["technical_opened"]),
            "message": "This record matches the PMC audit ledger." if ok else "Ledger check failed — treat this document as untrusted."}

