"""PMC Assistant — AI chat for visitors, vendors and signed-in admin/staff (answers only)."""
import re
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import config
from db import db
from models.base import now_iso
from pmc_lib.help_content_data import MODULES

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

ABOUT = (
    "PMC Managers (pmcmanagers.com) is a global e-tendering and procurement platform run by THE PMC MANAGERS LTD (UK). "
    "Buyers publish tender notices (tenders, RFQs, RFPs). Suppliers register (registration + KYC review by PMC), choose business "
    "categories (the first category is free unless PMC waives extra-category fees for that supplier), browse the Global Tender Grid, download tender "
    "documents, pay EMD (bid security) where a tender requires it, and submit sealed bids online. Bids are opened and evaluated by "
    "the buyer's committee; awards create purchase orders and contracts. Every step is recorded on a tamper-evident audit ledger. "
    "Fees (extra categories, document downloads, tender hosting, award fee) are set by PMC per pricing band or country, and for each "
    "tender PMC decides before publishing whether each fee is charged or waived and who pays the award fee; a supplier-paid award fee "
    "is shown on the tender. Prices are not published yet — ask PMC Managers for a quote. Payments are by card through Stripe. "
    "Vendors have a portal with My bids, EMD & payments, Messages, Data intel and Refer & earn. "
    "Help pages: /register (supplier registration), /notices (open tenders), /buyers (for organisations issuing tenders), /login."
)
RULES = (
    "You are PMC Assistant. Answer briefly (max 120 words), friendly and factual, in the user's language. Use ONLY the facts given. "
    "Never invent prices, dates, tender details, legal advice or guarantees. If you don't know, say so and point to the most "
    "relevant page, or suggest emailing the PMC desk. Never ask for passwords, card numbers or ID documents. Plain text only."
)


STAFF_RULES = (
    "You are PMC Assistant for PMC Managers' internal admin and staff team. Explain how to do tasks in the portal using ONLY "
    "the HELP GUIDES given: name the screen, then give short numbered steps with the exact button names. Max 150 words, plain text with no markdown or asterisks, "
    "in the user's language. If a relevant guide is listed, end with 'Guide: /help/<code>'. Never invent features, figures or "
    "policies. If the guides don't cover it, say so and suggest asking the Master Admin. Never ask for passwords or card numbers."
)
PUBLIC_SURFACES = {"public", "vendor", "registration"}
STOP = set("the a an to of and or in on for how do i is it my me can what where with this that be are you your we from at by".split())


class ChatIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=1000)
    mode: str = Field(default="public", pattern="^(public|staff)$")


async def _staff(request: Request):
    tok = request.cookies.get("access_token")
    if not tok:
        return None
    try:
        p = jwt.decode(tok, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return await db.admin_users.find_one({"_id": ObjectId(p["sub"])}) if p.get("type") == "access" else None
    except Exception:
        return None


def _words(t: str) -> set:
    return {w for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in STOP}


def _guides(message: str, staff: bool, k: int = 3) -> list:
    q = _words(message)
    scored = []
    for code, m in MODULES.items():
        if not staff and m.get("surface") not in PUBLIC_SURFACES:
            continue
        labels = " ".join(a.get("label", "") for a in m.get("actions", []))
        s = 3 * len(q & _words(m.get("title"))) + 2 * len(q & _words(labels)) + len(q & _words(m.get("purpose")))
        if s >= 2:
            scored.append((s, code))
    return [c for _, c in sorted(scored, reverse=True)[:k]]


def _guide_text(codes: list) -> str:
    out = []
    for c in codes:
        m = MODULES[c]
        acts = "; ".join(f"{a.get('label')}: " + " ".join(a.get("steps", [])) for a in m.get("actions", []))
        out.append(f"[{c}] {m.get('title')} (screen {m.get('url_path')}): {m.get('purpose')} Tasks: {acts}"[:1800])
    return "\n".join(out) or "- no matching guide"


async def _vendor(request: Request):
    tok = request.cookies.get("vendor_token")
    if not tok:
        return None
    try:
        p = jwt.decode(tok, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return await db.vendors.find_one({"_id": ObjectId(p["sub"])}) if p.get("type") == "vendor_access" else None
    except Exception:
        return None


async def _context(v) -> str:
    rows = await db.notices.find({"is_published": True, "$or": [{"submission_deadline": {"$gte": now_iso()}},
                                                              {"submission_deadline": {"$in": [None, ""]}}]}, {"notice_ref": 1, "title": 1, "category": 1,
                                                          "delivery_country": 1, "submission_deadline": 1}
                                 ).sort("published_at", -1).limit(12).to_list(12)
    t = "\n".join(f"- {r['notice_ref']}: {r.get('title')} | {r.get('category')} | {r.get('delivery_country')} | "
                  f"closes {str(r.get('submission_deadline') or '')[:10]}" for r in rows) or "- none open right now"
    out = f"LATEST OPEN TENDERS:\n{t}\n"
    if v:
        ref = v.get("vendor_ref")
        bids = await db.bids.count_documents({"vendor_id": str(v["_id"])})
        unread = await db.messages.count_documents({"to_vendor_ref": ref, "read": {"$ne": True}})
        pend = await db.vendor_category_requests.count_documents({"vendor_ref": ref, "status": {"$in": ["pending", "payment_pending"]}})
        out += (f"\nSIGNED-IN SUPPLIER: {v.get('company_name')} ({ref}), country {v.get('country')}, categories "
                f"{', '.join(v.get('business_categories') or []) or 'none'}; bids on record {bids}; unread PMC messages {unread}; "
                f"category requests waiting {pend}. Only discuss this supplier's own data.\n")
    return out


@router.post("/chat")
async def chat(body: ChatIn, request: Request):
    from routers.tender_pro import _llm_complete
    ip = ((request.headers.get("x-forwarded-for") or "").split(",")[-1].strip()
          or (request.client.host if request.client else ""))
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    if await db.assistant_hits.count_documents({"ip": ip, "at_dt": {"$gte": since}}) >= 40:
        raise HTTPException(status_code=429, detail="You've sent a lot of messages. Please try again in a while.")
    await db.assistant_hits.insert_one({"ip": ip, "at_dt": datetime.now(timezone.utc)})
    st = await _staff(request) if body.mode == "staff" else None
    if body.mode == "staff" and not st:
        raise HTTPException(status_code=401, detail="Please sign in again to use the staff assistant.")
    v = None if st else await _vendor(request)
    s = await db.assistant_sessions.find_one({"session_id": body.session_id}) or {}
    if s.get("vendor_id") and (not v or str(v["_id"]) != s["vendor_id"]):
        raise HTTPException(status_code=409, detail="Please refresh the page to start a new chat.")
    if (st and s and s.get("staff_id") != str(st["_id"])) or (not st and s.get("staff_id")):
        raise HTTPException(status_code=409, detail="Please refresh the page to start a new chat.")
    hist = (s.get("messages") or [])[-10:]
    convo = "\n".join(f"{m['role'].upper()}: {m['text']}" for m in hist)
    codes = _guides(body.message, bool(st))
    if st:
        role = st.get("role") or "admin"
        system = f"{STAFF_RULES}\n\nUSER: {st.get('name') or 'team member'}, role {role}.\n\nABOUT PMC:\n{ABOUT}\n\nHELP GUIDES:\n{_guide_text(codes)}"
    else:
        system = f"{RULES}\n\nABOUT PMC:\n{ABOUT}\n\nHELP GUIDES:\n{_guide_text(codes)}\n\n{await _context(v)}"
    reply = (await _llm_complete(system, f"{convo}\nUSER: {body.message}\nASSISTANT:") or "").strip()
    if not reply:
        raise HTTPException(status_code=502, detail="The assistant is busy. Please try again.")
    msgs = hist + [{"role": "user", "text": body.message, "at": now_iso()}, {"role": "assistant", "text": reply, "at": now_iso()}]
    await db.assistant_sessions.update_one({"session_id": body.session_id}, {"$set": {
        "messages": msgs, "vendor_id": str(v["_id"]) if v else None, "staff_id": str(st["_id"]) if st else None,
        "updated_at": now_iso()}, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
    named = [c for c in re.findall(r"/help/([a-z0-9-]+)", reply) if c in MODULES]
    picks = list(dict.fromkeys(named + codes))[:2]
    return {"reply": reply, "videos": [{"slug": c, "title": MODULES[c].get("title")} for c in picks]}


async def ensure_indexes() -> None:
    await db.assistant_hits.create_index("at_dt", expireAfterSeconds=3600)
    await db.assistant_sessions.create_index("session_id", unique=True)
    await db.oauth_states.create_index("created_at", expireAfterSeconds=900)
    await db.mkt_social_posts.create_index("notice_ref", unique=True)
