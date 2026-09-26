"""Notification helper — called by state-transition handlers to alert
the next role in the pipeline. Fires an in-app notification record + email."""
import asyncio
import logging
from typing import Optional

import config
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


# v47b — statuses the VENDOR (bidder) is emailed about. Staff notifications
# remain governed by ROLE_NEXT_STAGE above; these go to bid.vendor_email.
VENDOR_STAGE_MESSAGES = {
    "emd_pending":        ("EMD payment pending for your bid",
                           "is approved to proceed to the EMD (Earnest Money Deposit) step. "
                           "Please pay from Vendor Portal → My bids → Pay EMD, or use the link below."),
    "admin_flagged":      ("Your bid passed PMC admin review",
                           "has passed PMC's admin review and moved to certification."),
    "certifier_cleared":  ("Certifier cleared your bid",
                           "has cleared the certifier stage and moved to legal review."),
    "legal_cleared":      ("Legal cleared your bid",
                           "has cleared legal review and moved to accounting sign-off."),
    "accounting_cleared": ("Accounting cleared your bid",
                           "has cleared accounting and is now with the evaluation committee."),
    "on_hold":            ("Your bid is on hold",
                           "has been placed ON HOLD by PMC admin. You will be notified when it resumes. "
                           "Contact your PMC relationship manager if you need details."),
    "awarded":            ("Congratulations — your bid is awarded",
                           "has been AWARDED. Open your vendor portal to sign the purchase order."),
    "rejected":           ("Bid not selected",
                           "was not selected on this occasion. Thank you for participating — "
                           "your EMD (if paid) will be refunded per the tender terms."),
}


async def _notify_vendor(bid: dict, new_status: str) -> None:
    """v47b — email the bidder on every vendor-visible stage transition."""
    msg = VENDOR_STAGE_MESSAGES.get(new_status)
    if not msg:
        return
    subject, desc = msg
    pay_link = f"{config.FRONTEND_URL}/vendor/bids/{bid.get('_id') or bid.get('id')}/pay"
    reason = bid.get("hold_reason") if new_status == "on_hold" else None
    body_html = (
        f"<p>Dear {bid.get('company_name') or 'Vendor'},</p>"
        f"<p>Your bid <strong>{bid.get('bid_ref')}</strong> on tender "
        f"<code>{bid.get('notice_ref')}</code> {desc}</p>"
        + (f"<p>Hold reason: <em>{reason}</em></p>" if reason else "")
        + (f"<p>Quoted value: {bid.get('price_currency')} {bid.get('price_amount')}</p>")
    )
    if new_status == "emd_pending":
        body = wrap(subject, body_html, "Pay EMD securely", pay_link)
    else:
        body = wrap(subject, body_html, "Open vendor portal",
                    f"{config.FRONTEND_URL}/vendor")
    asyncio.create_task(send_email(bid.get("vendor_email"), f"[PMC] {subject}", body))


async def notify_bid_transition(bid: dict, new_status: str) -> None:
    """Called by /bids/{id}/decision after a state advance."""
    # v47b — always email the bidder on vendor-visible transitions.
    try:
        await _notify_vendor(bid, new_status)
    except Exception as e:
        log.warning("vendor transition email failed for bid %s: %s",
                    bid.get("bid_ref"), e)
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
