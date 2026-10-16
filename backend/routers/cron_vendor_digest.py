"""v53j — Weekly vendor opportunity digest.

Platform cron hits POST /api/v1/cron/vendor-opportunity-digest once a week.
For each vendor that was invited to one or more live/upcoming reverse
auctions but has not yet registered OR declined, we send a single digest
email listing those auctions so they can still join or decline with a
reason. Keeps the vendor relationship warm without spamming per-auction.

Cron contract: endpoint ACKs 2xx immediately; _do_digest runs in a
background task. Idempotent via cron_runs run_id.
"""
import asyncio
import logging
import os
import secrets
from collections import defaultdict
from fastapi import APIRouter, Header, HTTPException

import config
from bson import ObjectId
from db import db
from models.base import now_iso

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])
log = logging.getLogger("cron")


def _verify_bearer(authorization: str) -> None:
    secret = os.environ.get("WEBHOOK_CRON_SECRET") or getattr(config, "WEBHOOK_CRON_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="WEBHOOK_CRON_SECRET not set")
    expected = f"Bearer {secret}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


# Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
@router.post("/vendor-opportunity-digest")
async def vendor_opportunity_digest(
    authorization: str = Header(default=""),
    x_webhook_id: str = Header(default=""),
):
    """Weekly digest. For each invited vendor who hasn't joined or declined,
    email the list of still-open reverse auctions they can still enter."""
    _verify_bearer(authorization)
    run_id = x_webhook_id or now_iso()
    seen = await db.cron_runs.find_one({"run_id": run_id, "name": "vendor-opportunity-digest"})
    if seen:
        return {"ok": True, "duplicate": True}
    await db.cron_runs.insert_one({"run_id": run_id,
                                    "name": "vendor-opportunity-digest",
                                    "started_at": now_iso()})
    asyncio.create_task(_do_digest(run_id))
    return {"ok": True, "run_id": run_id, "status": "queued"}


async def _do_digest(run_id: str) -> None:
    from emails import send_email, wrap as email_wrap
    sent = 0
    by_email: dict = defaultdict(list)
    try:
        # Collect every invite with status not accepted/declined, grouped by email.
        async for inv in db.reverse_auction_invitations.find(
            {"status": {"$nin": ["accepted", "declined"]}}
        ):
            aid = inv.get("auction_id")
            if not aid:
                continue
            try:
                a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
            except Exception:
                a = None
            if not a or a.get("status") not in ("draft", "live"):
                continue  # digest only lists auctions the vendor can still join
            email = (inv.get("email") or "").lower()
            if not email:
                continue
            by_email[email].append({
                "token": inv["token"],
                "title": a.get("title"),
                "notice_ref": a.get("notice_ref"),
                "currency": a.get("currency"),
                "starting_price": a.get("starting_price"),
                "end_at": a.get("end_at"),
            })
        for email, items in by_email.items():
            rows_html = ""
            for it in items:
                invite_url = f"{config.FRONTEND_URL}/vendor/auction/invite/{it['token']}"
                price = (f"{it['currency']} {float(it['starting_price']):,.0f}"
                         if it.get("starting_price") else "—")
                rows_html += (
                    f'<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">'
                    f'<div style="font-weight:600;color:#0F3B2E">{it["title"]}</div>'
                    f'<div style="font-size:12px;color:#64748B">{it["notice_ref"]} · '
                    f'starts at {price}</div>'
                    f'<a href="{invite_url}" style="font-size:12px;'
                    f'color:#0F3B2E;text-decoration:underline">Open invitation</a>'
                    f'</td></tr>'
                )
            subject = f"PMC Managers — {len(items)} reverse auction invite(s) still open for you"
            body = email_wrap(subject,
                f"<p>You have been invited to the following reverse auctions "
                f"and have not registered yet. Each link below opens the "
                f"auction room where you can join (or decline with a reason).</p>"
                f'<table style="width:100%;border-collapse:collapse;'
                f'margin-top:12px">{rows_html}</table>'
                f"<p style='margin-top:16px;font-size:12px;color:#64748B'>"
                f"If you don't want to receive these digests, decline each "
                f"invitation from its auction page with a short reason — "
                f"you'll stop appearing in this list.</p>")
            try:
                if await send_email(email, subject, body):
                    sent += 1
            except Exception as e:
                log.warning("digest email failed for %s: %s", email, e)
    finally:
        await db.cron_runs.update_one(
            {"run_id": run_id, "name": "vendor-opportunity-digest"},
            {"$set": {"finished_at": now_iso(),
                      "emails_sent": sent,
                      "vendors_notified": len(by_email)}})
