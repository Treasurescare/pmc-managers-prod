"""v51an — Cron webhook endpoints.

Platform cron (defined in .emergent/crons.yml) hits these to run scheduled
background work. Each endpoint MUST return 2xx immediately and enqueue the
real work asynchronously (platform dispatcher caps at ~5s).
"""
import asyncio
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Header, HTTPException

import config
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
@router.post("/escrow-expiry-watchdog")
async def escrow_expiry_watchdog(
    authorization: str = Header(default=""),
    x_webhook_id: str = Header(default=""),
):
    """Daily sweep: email every approved escrow institution whose regulatory
    licence or audited-financials expire within the next 30 days (and nag at
    7 and 1 day too). Also emails PMC admins when a licence is already
    expired."""
    _verify_bearer(authorization)
    run_id = x_webhook_id or now_iso()
    # Idempotency guard — remember run_ids so retries don't double-send.
    seen = await db.cron_runs.find_one({"run_id": run_id, "name": "escrow-expiry-watchdog"})
    if seen:
        return {"ok": True, "duplicate": True}
    await db.cron_runs.insert_one({"run_id": run_id,
                                    "name": "escrow-expiry-watchdog",
                                    "started_at": now_iso()})
    asyncio.create_task(_do_expiry_watchdog(run_id))
    return {"ok": True, "run_id": run_id, "status": "queued"}


async def _do_expiry_watchdog(run_id: str) -> None:
    from emails import send_email, wrap
    today = datetime.now(timezone.utc).date()
    MILESTONES = [30, 7, 1]       # days-until-expiry to notify at
    sent = 0
    try:
        async for inst in db.escrow_institutions.find({"status": "approved"}):
            iid = str(inst["_id"])
            exp_str = inst.get("licence_expiry")
            if not exp_str:
                continue
            try:
                exp = datetime.fromisoformat(str(exp_str).replace("Z", "+00:00")).date()
            except Exception:
                continue
            days_left = (exp - today).days
            # Track which milestones we've already notified for this institution.
            notified = set((inst.get("expiry_notifications_sent") or []))
            if days_left < 0:
                key = "expired"
                if key in notified:
                    continue
                recipients = {inst.get("primary_contact_email", "").lower()}
                for s in inst.get("signatories") or []:
                    if s.get("email"):
                        recipients.add(s["email"].lower())
                recipients.discard("")
                subject = f"URGENT — Escrow licence expired for {inst.get('legal_name')}"
                body = wrap(subject,
                    f"<p>Our records show your regulatory licence expired on "
                    f"<strong>{exp_str}</strong> ({-days_left} day(s) ago).</p>"
                    f"<p>PMC Managers has paused new EMD routing to accounts you "
                    f"operate until an updated licence is on file. Please reply "
                    f"with the renewed licence PDF or upload it from your "
                    f"institution dashboard.</p>",
                    "Open dashboard",
                    f"{config.FRONTEND_URL}/escrow/dashboard/{iid}?token={inst.get('magic_token')}")
                for to in recipients:
                    try:
                        await send_email(to, f"[PMC] {subject}", body)
                        sent += 1
                    except Exception as e:
                        log.warning("expiry-email failed for %s: %s", to, e)
                notified.add(key)
            else:
                for m in MILESTONES:
                    if days_left <= m and days_left > (m // 3 if m > 1 else -1):
                        key = f"days-{m}"
                        if key in notified or days_left > m:
                            continue
                        recipients = {inst.get("primary_contact_email", "").lower()}
                        for s in inst.get("signatories") or []:
                            if s.get("email"):
                                recipients.add(s["email"].lower())
                        recipients.discard("")
                        subject = (f"Reminder — Escrow licence expires in {days_left} "
                                   f"day(s) for {inst.get('legal_name')}")
                        body = wrap(subject,
                            f"<p>Your regulatory licence on file expires on "
                            f"<strong>{exp_str}</strong>, in {days_left} day(s).</p>"
                            f"<p>Please upload a renewed licence (and refreshed "
                            f"audited financials if due) from your institution "
                            f"dashboard to avoid service interruption. PMC pauses "
                            f"new EMD routing to institutions with an expired "
                            f"licence on file.</p>",
                            "Open dashboard",
                            f"{config.FRONTEND_URL}/escrow/dashboard/{iid}?token={inst.get('magic_token')}")
                        for to in recipients:
                            try:
                                await send_email(to, f"[PMC] {subject}", body)
                                sent += 1
                            except Exception as e:
                                log.warning("expiry-email failed for %s: %s", to, e)
                        notified.add(key)
                        break
            await db.escrow_institutions.update_one(
                {"_id": inst["_id"]},
                {"$set": {"expiry_notifications_sent": list(notified),
                          "last_expiry_check_at": now_iso()}})
    finally:
        await db.cron_runs.update_one({"run_id": run_id, "name": "escrow-expiry-watchdog"},
                                       {"$set": {"finished_at": now_iso(),
                                                 "emails_sent": sent}})
