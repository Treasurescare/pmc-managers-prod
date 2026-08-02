"""Notification helper — called by state-transition handlers to alert
the next role in the pipeline. Fires an in-app notification record + email."""
import asyncio
import logging
from typing import Optional

from db import db
from models.base import now_iso
from emails import send_email, wrap

log = logging.getLogger("notify")


ROLE_NEXT_STAGE = {
    "emd_paid":            ("escrow_agent",   "New bid ready for Escrow acceptance"),
    "escrow_accepted":     ("admin",          "Bid awaits Admin flag for Certifier"),
    "admin_flagged":       ("certifier",      "You've been assigned to certify a bid"),
    "certifier_cleared":   ("legal_counsel",  "Bid ready for Legal review"),
    "legal_cleared":       ("accounting",     "Bid ready for Accounting sign-off"),
    "accounting_cleared":  ("committee_member", "Bid ready for Committee decision"),
    "awarded":             ("admin",          "Bid awarded — kickoff contract creation"),
}


async def notify_role(role: str, subject: str, body_html: str,
                       related_type: Optional[str] = None,
                       related_id: Optional[str] = None) -> int:
    """Fire in-app + email notifications to every ACTIVE staff member holding `role`."""
    count = 0
    async for staff in db.admin_users.find(
        {"$or": [{"roles": role}, {"role": role}], "is_active": {"$ne": False}}
    ):
        await db.notifications.insert_one({
            "user_id": str(staff["_id"]),
            "user_email": staff["email"],
            "role": role,
            "subject": subject,
            "body": body_html,
            "related_type": related_type,
            "related_id": related_id,
            "read": False,
            "created_at": now_iso(),
        })
        # Fire-and-forget email
        asyncio.create_task(send_email(
            staff["email"],
            f"[PMC] {subject}",
            wrap(subject, body_html),
        ))
        count += 1
    log.info(f"Notified {count} staff for role={role}: {subject}")
    return count


async def notify_bid_transition(bid: dict, new_status: str) -> None:
    """Called by /bids/{id}/decision after a state advance."""
    tgt = ROLE_NEXT_STAGE.get(new_status)
    if not tgt:
        return
    role, subject = tgt
    body = (f"<p>Bid <strong>{bid.get('bid_ref')}</strong> on tender "
            f"<code>{bid.get('notice_ref')}</code> is now at <em>{new_status}</em>.</p>"
            f"<p>Vendor: {bid.get('company_name') or bid.get('vendor_email')}<br/>"
            f"Value: {bid.get('price_currency')} {bid.get('price_amount')}</p>"
            f"<p>Please act on it from your dashboard.</p>")
    await notify_role(role, subject, body,
                      related_type="bid", related_id=str(bid.get("_id") or bid.get("id")))
