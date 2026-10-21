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


# ---------- #13 — Incomplete escrow registration reminders + dormancy ----------

REG_REMINDER_INTERVAL_DAYS = 7
REG_DORMANT_AFTER_DAYS = 30


def _parse_iso(s: str):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


async def _institution_recipients(inst: dict):
    """Base email (continues with the escrow for its whole life) + CC every
    registered signatory email."""
    base = (inst.get("primary_contact_email") or "").strip().lower()
    cc = []
    for s in inst.get("signatories") or []:
        e = (s.get("email") or "").strip().lower()
        if e and e != base:
            cc.append(e)
    return base, sorted(set(cc))


# Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
@router.post("/escrow-registration-reminders")
async def escrow_registration_reminders(
    authorization: str = Header(default=""),
    x_webhook_id: str = Header(default=""),
):
    """Daily sweep over incomplete escrow institution registrations
    (draft / needs_clarification): nudge the applicant every 7 days until they
    complete; at 30 days mark the registration dormant and send a final warning
    that they may need to register again. All mails go to the base escrow email
    with a CC to every registered signatory."""
    _verify_bearer(authorization)
    run_id = x_webhook_id or now_iso()
    seen = await db.cron_runs.find_one({"run_id": run_id, "name": "escrow-registration-reminders"})
    if seen:
        return {"ok": True, "duplicate": True}
    await db.cron_runs.insert_one({"run_id": run_id,
                                    "name": "escrow-registration-reminders",
                                    "started_at": now_iso()})
    asyncio.create_task(_do_registration_reminders(run_id))
    return {"ok": True, "run_id": run_id, "status": "queued"}


async def _do_registration_reminders(run_id: str) -> None:
    from emails import send_email, wrap
    now = datetime.now(timezone.utc)
    reminded = 0
    dormant = 0
    try:
        async for inst in db.escrow_institutions.find(
                {"status": {"$in": ["draft", "needs_clarification"]}}):
            iid = str(inst["_id"])
            base, cc = await _institution_recipients(inst)
            if not base:
                continue
            created = _parse_iso(inst.get("created_at")) or now
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (now - created).days
            name = inst.get("legal_name") or "applicant"

            # --- 30+ days: mark dormant + final warning ---
            if age_days >= REG_DORMANT_AFTER_DAYS:
                subject = "PMC Managers — your escrow registration is now dormant"
                body = wrap("Your escrow registration is dormant",
                    f"<p>Dear {name},</p>"
                    f"<p>Your escrow institution registration with PMC Managers has "
                    f"been open and incomplete for more than {REG_DORMANT_AFTER_DAYS} "
                    f"days, so we have marked it <strong>dormant</strong>.</p>"
                    f"<p>If you still wish to join, you may need to start a fresh "
                    f"registration at the link below using this same email address.</p>",
                    "Start a new registration",
                    f"{config.FRONTEND_URL}/escrow/register")
                try:
                    await send_email(base, f"[PMC] {subject}", body, cc=cc)
                except Exception as e:
                    log.warning("dormant-warning email failed for %s: %s", base, e)
                await db.escrow_institutions.update_one(
                    {"_id": inst["_id"]},
                    {"$set": {"status": "dormant", "dormant_at": now_iso(),
                              "reg_warned_dormant": True, "updated_at": now_iso()}})
                if inst.get("account_id"):
                    try:
                        from routers.escrow_accounts import notify_account
                        await notify_account(inst["account_id"], "registration_dormant",
                            "Registration marked dormant",
                            "Your incomplete escrow registration has been marked "
                            "dormant after 30 days. You may need to register again.",
                            "/escrow/register", send_email_too=False)
                    except Exception:
                        pass
                dormant += 1
                continue

            # --- otherwise: reminder every 7 days ---
            last = _parse_iso(inst.get("reg_reminder_last_at"))
            if last and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            due = (last is None) or ((now - last).days >= REG_REMINDER_INTERVAL_DAYS)
            if not due:
                continue
            resume_url = f"{config.FRONTEND_URL}/escrow/login"
            subject = "PMC Managers — please finish your escrow registration"
            body = wrap("Finish your escrow registration",
                f"<p>Dear {name},</p>"
                f"<p>You started registering as an escrow institution with PMC "
                f"Managers but haven't completed all sections yet. Your progress is "
                f"saved — sign in to pick up where you left off and submit for review.</p>"
                f"<p>Reminders continue weekly; after "
                f"{REG_DORMANT_AFTER_DAYS} days an incomplete registration is marked "
                f"dormant.</p>",
                "Sign in & continue", resume_url)
            try:
                await send_email(base, f"[PMC] {subject}", body, cc=cc)
            except Exception as e:
                log.warning("reg-reminder email failed for %s: %s", base, e)
            await db.escrow_institutions.update_one(
                {"_id": inst["_id"]},
                {"$set": {"reg_reminder_last_at": now_iso(), "updated_at": now_iso()},
                 "$inc": {"reg_reminder_count": 1}})
            reminded += 1
    finally:
        await db.cron_runs.update_one(
            {"run_id": run_id, "name": "escrow-registration-reminders"},
            {"$set": {"finished_at": now_iso(),
                      "reminded": reminded, "dormant": dormant}})
