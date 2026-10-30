"""PMC Assistant — AI chat for website visitors and signed-in vendors (answers only)."""
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import config
from db import db
from models.base import now_iso

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

ABOUT = (
    "PMC Managers (pmcmanagers.com) is a global e-tendering and procurement platform run by THE PMC MANAGERS LTD (UK). "
    "Buyers publish tender notices (tenders, RFQs, RFPs). Suppliers register (registration + KYC review by PMC), choose business "
    "categories (the first category is free, each extra category has a fee), browse the Global Tender Board, download tender "
    "documents, pay EMD (bid security) where a tender requires it, and submit sealed bids online. Bids are opened and evaluated by "
    "the buyer's committee; awards create purchase orders and contracts. Every step is recorded on a tamper-evident audit ledger. "
    "Fees (registration, extra categories, document downloads, tender hosting, subscriptions) are set per country and category and "
    "paid securely by card through Stripe. Vendors have a portal with My bids, EMD & payments, Messages, Data intel and Refer & earn. "
    "Help pages: /register (supplier registration), /notices (open tenders), /buyers (for organisations issuing tenders), /login."
)
RULES = (
    "You are PMC Assistant. Answer briefly (max 120 words), friendly and factual, in the user's language. Use ONLY the facts given. "
    "Never invent prices, dates, tender details, legal advice or guarantees. If you don't know, say so and point to the most "
    "relevant page, or suggest emailing the PMC desk. Never ask for passwords, card numbers or ID documents. Plain text only."
)


class ChatIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=1000)


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
    v = await _vendor(request)
    s = await db.assistant_sessions.find_one({"session_id": body.session_id}) or {}
    if s.get("vendor_id") and (not v or str(v["_id"]) != s["vendor_id"]):
        raise HTTPException(status_code=409, detail="Please refresh the page to start a new chat.")
    hist = (s.get("messages") or [])[-10:]
    convo = "\n".join(f"{m['role'].upper()}: {m['text']}" for m in hist)
    system = f"{RULES}\n\nABOUT PMC:\n{ABOUT}\n\n{await _context(v)}"
    reply = (await _llm_complete(system, f"{convo}\nUSER: {body.message}\nASSISTANT:") or "").strip()
    if not reply:
        raise HTTPException(status_code=502, detail="The assistant is busy. Please try again.")
    msgs = hist + [{"role": "user", "text": body.message, "at": now_iso()}, {"role": "assistant", "text": reply, "at": now_iso()}]
    await db.assistant_sessions.update_one({"session_id": body.session_id}, {"$set": {
        "messages": msgs, "vendor_id": str(v["_id"]) if v else None, "updated_at": now_iso()},
        "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
    return {"reply": reply}


async def ensure_indexes() -> None:
    await db.assistant_hits.create_index("at_dt", expireAfterSeconds=3600)
    await db.assistant_sessions.create_index("session_id", unique=True)
    await db.oauth_states.create_index("created_at", expireAfterSeconds=900)
    await db.mkt_social_posts.create_index("notice_ref", unique=True)
