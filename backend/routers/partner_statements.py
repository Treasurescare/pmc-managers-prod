"""Partner monthly statement PDF (email on the 1st) + monthly badges (portal, leaderboard, homepage)."""
import asyncio
import base64
import hmac
import logging
import os
import re
from datetime import datetime, timezone
from html import escape as h
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.partner_suppliers import _approved_partner, _board, _show_names
from security import require_csrf, require_role

router = APIRouter(tags=["partner-statements"])
log = logging.getLogger(__name__)
ADMIN = Depends(require_role("admin"))
BADGES = {"top_partner": "Top partner of the month", "most_invites": "Most active inviter", "rising_star": "Rising star"}


def _range(month: str) -> tuple:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise HTTPException(status_code=422, detail="Month must look like 2026-10")
    y, m = int(month[:4]), int(month[5:])
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


def _prev_month() -> str:
    n = datetime.now(timezone.utc)
    return f"{n.year - (n.month == 1)}-{12 if n.month == 1 else n.month - 1:02d}"


def _this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def badges_for(month: str) -> dict:
    """partner_id -> [badge keys] for the given month."""
    start, end = _range(month)
    rows = await _board(start, end)
    out: dict = {}
    top = max((r["approved"] for r in rows), default=0)
    inv = max((r["invites"] for r in rows), default=0)
    for r in rows:
        b = []
        if top > 0 and r["approved"] == top:
            b.append("top_partner")
        if inv > 0 and r["invites"] == inv:
            b.append("most_invites")
        if r["approved"] > 0 and not await db.registrations.find_one({"approved_partner_id": r["id"], "reviewed_at": {"$lt": start}}):
            b.append("rising_star")
        if b:
            out[r["id"]] = b
    return out


async def _statement_data(a: dict, month: str) -> dict:
    start, end = _range(month)
    pid = str(a["_id"])
    sups = await db.registrations.find({"$or": [{"approved_partner_id": pid}, {"invited_by_partner_id": pid}, {"partner_id": pid}],
                                        "$and": [{"$or": [{"reviewed_at": {"$gte": start, "$lt": end}}, {"partner_invited_at": {"$gte": start, "$lt": end}}]}]},
                                       {"company_name": 1, "vendor_ref": 1, "status": 1, "partner_invited_at": 1, "reviewed_at": 1}).to_list(500)
    earned = await db.partner_commissions.find({"partner_id": pid, "created_at": {"$gte": start, "$lt": end}}).to_list(1000)
    paid = await db.partner_commissions.find({"partner_id": pid, "status": "paid", "settled_at": {"$gte": start, "$lt": end}}).to_list(1000)
    due = await db.partner_commissions.find({"partner_id": pid, "status": "due"}).to_list(1000)
    return {"sups": sups, "earned": earned, "paid": paid, "due": due, "badges": (await badges_for(month)).get(pid, [])}


def _sum(rows: list) -> str:
    t: dict = {}
    for r in rows:
        t[r["currency"]] = t.get(r["currency"], 0) + float(r["amount"])
    return ", ".join(f"{c} {v:,.2f}" for c, v in t.items()) or "—"


def render_statement_pdf(a: dict, month: str, d: dict) -> bytes:
    from weasyprint import HTML
    from pdf_brand import brand_html
    sup_rows = "".join(f"<tr><td>{h(s.get('company_name') or '')}</td><td>{h(s.get('vendor_ref') or '—')}</td><td>{h(str(s.get('status') or ''))}</td>"
                       f"<td>{h(str(s.get('partner_invited_at') or '')[:10])}</td></tr>" for s in d["sups"]) or "<tr><td colspan=4>No supplier activity this month</td></tr>"
    ent = lambda rows, col: "".join(f"<tr><td>{h(str(r.get(col) or '')[:10])}</td><td>{h(r['kind'].title())}{' · ' + h(r['deal_ref']) if r.get('deal_ref') else ''}</td>"  # noqa: E731
                                    f"<td>{h(r.get('company_name') or '')}</td><td>{h(r.get('reference') or r.get('basis') or '')}</td>"
                                    f"<td class=r>{h(r['currency'])} {float(r['amount']):,.2f}</td></tr>" for r in rows) or "<tr><td colspan=5>None</td></tr>"
    badges = " ".join(f"<span class=badge>{h(BADGES[b])}</span>" for b in d["badges"])
    html = f"""<html><head><style>
      @page {{ size:A4; margin:16mm; }} body {{ font-family:Helvetica,Arial,sans-serif; font-size:10.5px; color:#14261F; }}
      h1 {{ font-size:20px; color:#0F3B2E; margin:6px 0 2px; }} h2 {{ font-size:12px; color:#0F3B2E; margin:18px 0 6px; text-transform:uppercase; letter-spacing:1px; }}
      table {{ width:100%; border-collapse:collapse; }} th, td {{ padding:6px 8px; text-align:left; border-bottom:1px solid rgba(15,59,46,.12); }}
      th {{ font-size:8.5px; letter-spacing:1px; text-transform:uppercase; color:#5B6B63; }} .r {{ text-align:right; }}
      .kpis {{ display:flex; gap:10px; margin:12px 0; }} .kpi {{ border:1px solid rgba(15,59,46,.2); padding:8px 12px; flex:1; }}
      .kpi b {{ display:block; font-size:8.5px; text-transform:uppercase; color:#5B6B63; letter-spacing:1px; }}
      .badge {{ display:inline-block; background:#F3E7C4; color:#6B4E00; padding:3px 9px; font-weight:700; font-size:9px; margin-right:6px; }}
      .foot {{ margin-top:28px; font-size:8.5px; color:#7B8B83; }}
    </style></head><body>
      <h1>Partner statement · {h(month)}</h1>
      <div>{h(a.get('legal_name') or a.get('name') or '')} · partner code <b>{h(a.get('partner_code') or '—')}</b> · {h(a['email'])}</div>
      <div style="margin-top:6px">{badges}</div>
      <div class=kpis><div class=kpi><b>Suppliers approved</b>{sum(1 for s in d['sups'] if s.get('status') == 'approved' and str(s.get('reviewed_at') or '')[:7] == month)}</div>
        <div class=kpi><b>Invites sent</b>{sum(1 for s in d['sups'] if str(s.get('partner_invited_at') or '')[:7] == month)}</div>
        <div class=kpi><b>Commission earned</b>{h(_sum(d['earned']))}</div><div class=kpi><b>Payouts received</b>{h(_sum(d['paid']))}</div>
        <div class=kpi><b>Still due (all time)</b>{h(_sum(d['due']))}</div></div>
      <h2>Supplier activity</h2><table><thead><tr><th>Company</th><th>Supplier ref</th><th>Status</th><th>Invited</th></tr></thead><tbody>{sup_rows}</tbody></table>
      <h2>Commissions earned</h2><table><thead><tr><th>Date</th><th>Type</th><th>Supplier</th><th>Basis</th><th class=r>Amount</th></tr></thead><tbody>{ent(d['earned'], 'created_at')}</tbody></table>
      <h2>Payouts received</h2><table><thead><tr><th>Date</th><th>Type</th><th>Supplier</th><th>Reference</th><th class=r>Amount</th></tr></thead><tbody>{ent(d['paid'], 'paid_on')}</tbody></table>
      <div class=foot>Generated {h(now_iso()[:16].replace('T', ' '))} UTC · PMC Managers Limited · Global Tender Board · pmcmanagers.com<br/>
        Commissions are paid by PMC directly from its own account. Contact PMC if anything here looks wrong.</div>
    </body></html>"""
    return HTML(string=brand_html(html)).write_pdf()


async def _pdf_for(a: dict, month: str) -> bytes:
    return await asyncio.to_thread(render_statement_pdf, a, month, await _statement_data(a, month))


def _pdf_response(pdf: bytes, a: dict, month: str) -> Response:
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="PMC-partner-statement-{a.get("partner_code") or "partner"}-{month}.pdf"'})


@router.get("/api/v1/agents/me/statement.pdf")
async def my_statement(request: Request, month: Optional[str] = None):
    a = await _approved_partner(request)
    month = month or _prev_month()
    return _pdf_response(await _pdf_for(a, month), a, month)


@router.get("/api/v1/admin/agents/{aid}/statement.pdf")
async def admin_statement(aid: str, month: Optional[str] = None, admin=ADMIN):
    a = await db.agents.find_one({"_id": ObjectId(aid)}) if ObjectId.is_valid(aid) else None
    if not a:
        raise HTTPException(status_code=404, detail="Partner not found")
    month = month or _prev_month()
    return _pdf_response(await _pdf_for(a, month), a, month)


async def send_statements(month: str, force: bool = False) -> dict:
    sent = skipped = failed = 0
    async for a in db.agents.find({"status": "approved"}):
        key = {"partner_id": str(a["_id"]), "month": month}
        if not force and await db.partner_statements.find_one({**key, "email_ok": True}):
            skipped += 1
            continue
        try:
            pdf = await _pdf_for(a, month)
            ok = await send_email(a["email"], f"[PMC] Your partner statement for {month}",
                                  wrap(f"Partner statement · {month}", f"<p>Hello {h(a.get('name') or '')},</p><p>Your PMC partner statement for {month} is attached: "
                                       "suppliers you onboarded, commission earned and payouts received.</p>", "Open partner portal",
                                       f"{config.FRONTEND_URL.rstrip('/')}/partner/me"),
                                  attachments=[{"filename": f"PMC-partner-statement-{a.get('partner_code')}-{month}.pdf",
                                                "content_b64": base64.b64encode(pdf).decode(), "content_type": "application/pdf"}])
            await db.partner_statements.update_one(key, {"$set": {**key, "sent_at": now_iso(), "email_ok": bool(ok)}}, upsert=True)
            sent += 1 if ok else 0
            failed += 0 if ok else 1
        except Exception:
            log.exception("partner statement failed for %s", a.get("email"))
            failed += 1
    await audit_log("partner.statements_sent", None, "partner_statements", month, {"sent": sent, "skipped": skipped, "failed": failed})
    return {"month": month, "sent": sent, "skipped": skipped, "failed": failed}


@router.post("/api/v1/cron/partner-monthly-statements")
async def cron_statements(request: Request, bg: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    if not secret or not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    run_id = request.headers.get("X-Webhook-Id") or ""
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": "partner-monthly-statements", "at": now_iso()})
    bg.add_task(send_statements, _prev_month())
    return {"ok": True}


class SendIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    resend: bool = False


@router.post("/api/v1/admin/partners/statements/send", dependencies=[Depends(require_csrf)])
async def admin_send(body: SendIn, bg: BackgroundTasks, admin=ADMIN):
    _range(body.month)
    bg.add_task(send_statements, body.month, body.resend)
    await audit_log("partner.statements_manual", admin, "partner_statements", body.month, {"resend": body.resend})
    return {"queued": True, "month": body.month}


@router.get("/api/v1/agents/me/badges")
async def my_badges(request: Request):
    a = await _approved_partner(request)
    pid = str(a["_id"])
    cur, prev = (await badges_for(_this_month())).get(pid, []), (await badges_for(_prev_month())).get(pid, [])
    return {"this_month": [{"key": b, "label": BADGES[b]} for b in cur], "last_month": [{"key": b, "label": BADGES[b]} for b in prev],
            "month": _this_month(), "last": _prev_month()}


@router.get("/api/v1/public/partner-highlights")
async def public_highlights():
    """Homepage: last month's badge winners (falls back to this month so far). Names only if admin allows."""
    names = await _show_names()
    for month, live in ((_prev_month(), False), (_this_month(), True)):
        b = await badges_for(month)
        if b:
            start, end = _range(month)
            rows = {r["id"]: r for r in await _board(start, end)}
            order = ["top_partner", "most_invites", "rising_star"]
            items = []
            profiles = {str(p["_id"]): p async for p in db.agents.find(
                {"_id": {"$in": [ObjectId(x) for x in b if ObjectId.is_valid(x)]}, "public_profile.show": True, "public_profile.hidden": {"$ne": True}},
                {"public_profile": 1, "partner_code": 1, "legal_name": 1, "name": 1})}
            for pid, ks in sorted(b.items(), key=lambda kv: min(order.index(k) for k in kv[1])):
                if pid in rows:
                    r, ks = rows[pid], sorted(ks, key=order.index)
                    pp = (profiles.get(pid) or {}).get("public_profile") or {}
                    items.append({"badge": ks[0], "label": " · ".join(BADGES[k] for k in ks), "badges": ks,
                                  "partner": r["name"] if (names or pp) else r["code"], "code": r["code"], "approved": r["approved"], "invites": r["invites"],
                                  **({"bio": pp.get("bio") or "", "photo_url": f"/api/v1/public/partner-photo/{r['code']}?v={pp.get('photo_at', '')[:19]}" if pp.get("photo_at") else None} if pp else {})})
            return {"month": month, "live": live, "items": items[:6]}
    return {"month": _this_month(), "live": True, "items": []}


# ---------- partner public profile card (photo + bio, opt-in) ----------

class PublicProfileIn(BaseModel):
    bio: str = Field("", max_length=280)
    show: bool = False


@router.put("/api/v1/agents/me/public-profile", dependencies=[Depends(require_csrf)])
async def save_public_profile(body: PublicProfileIn, request: Request):
    a = await _approved_partner(request)
    pp = {**(a.get("public_profile") or {}), "bio": body.bio.strip(), "show": body.show, "updated_at": now_iso()}
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"public_profile": pp}})
    await audit_log("partner.public_profile", {"id": str(a["_id"]), "email": a["email"]}, "agent", str(a["_id"]), {"show": body.show})
    return pp


@router.get("/api/v1/agents/me/public-profile")
async def get_public_profile(request: Request):
    a = await _approved_partner(request)
    pp = a.get("public_profile") or {}
    return {**pp, "photo_url": f"/api/v1/agents/me/public-photo?v={pp.get('photo_at', '')[:19]}" if pp.get("photo_at") else None}


PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/api/v1/agents/me/public-photo", dependencies=[Depends(require_csrf)])
async def upload_public_photo(request: Request, file: UploadFile = File(...)):
    a = await _approved_partner(request)
    data = await file.read()
    if (file.content_type or "") not in PHOTO_TYPES or not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")):
        raise HTTPException(status_code=422, detail="Upload a JPG, PNG or WebP photo")
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo must be under 2 MB")
    await db.partner_photos.update_one({"partner_id": str(a["_id"])}, {"$set": {"partner_id": str(a["_id"]), "content_type": file.content_type,
                                                                          "data_b64": base64.b64encode(data).decode(), "at": now_iso()}}, upsert=True)
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"public_profile.photo_at": now_iso()}})
    return {"ok": True}


async def _photo(pid: str) -> Response:
    p = await db.partner_photos.find_one({"partner_id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="No photo")
    return Response(base64.b64decode(p["data_b64"]), media_type=p["content_type"],
                    headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.get("/api/v1/agents/me/public-photo")
async def my_photo(request: Request):
    a = await _approved_partner(request)
    return await _photo(str(a["_id"]))


@router.get("/api/v1/public/partner-photo/{code}")
async def public_photo(code: str):
    a = await db.agents.find_one({"partner_code": code, "status": "approved", "public_profile.show": True, "public_profile.hidden": {"$ne": True}})
    if not a:
        raise HTTPException(status_code=404, detail="No photo")
    return await _photo(str(a["_id"]))


class HideIn(BaseModel):
    hidden: bool


@router.post("/api/v1/admin/agents/{aid}/public-profile/hide", dependencies=[Depends(require_csrf)])
async def hide_public_profile(aid: str, body: HideIn, admin=ADMIN):
    if not ObjectId.is_valid(aid) or not await db.agents.find_one({"_id": ObjectId(aid)}):
        raise HTTPException(status_code=404, detail="Partner not found")
    await db.agents.update_one({"_id": ObjectId(aid)}, {"$set": {"public_profile.hidden": body.hidden}})
    await audit_log("partner.public_profile_hidden", admin, "agent", aid, body.model_dump())
    return body.model_dump()
