"""Helpers for routers/committee.py::create_committee.

Extracted to reduce the router's cyclomatic complexity: validating staff IDs,
tagging them with `committee_member`, building external-invitee records, and
firing acceptance emails.
"""
import asyncio
from typing import Iterable, List
from bson import ObjectId
from fastapi import HTTPException

import config
from db import db
from models.base import now_iso
from security import new_magic_token
from emails import send_email, wrap


async def validate_and_tag_committee_staff(chair_id: str, member_ids: Iterable[str]) -> None:
    """Ensure every referenced staff exists; tag them with committee_member role."""
    all_ids = list({chair_id, *member_ids})
    if not all_ids:
        return
    docs = await db.admin_users.find(
        {"_id": {"$in": [ObjectId(x) for x in all_ids]}}
    ).to_list(length=100)
    if len(docs) != len(all_ids):
        raise HTTPException(status_code=400, detail="One or more staff IDs are invalid")
    for s in docs:
        roles = s.get("roles") or [s.get("role") or "admin"]
        if "committee_member" not in roles:
            roles.append("committee_member")
            await db.admin_users.update_one({"_id": s["_id"]}, {"$set": {"roles": roles}})


def build_external_records(invitees) -> List[dict]:
    records: List[dict] = []
    for inv in (invitees or []):
        records.append({
            "email": inv.email.lower(),
            "name": inv.name,
            "designation": inv.designation,
            "accept_token": new_magic_token(),
            "status": "invited",
            "invited_at": now_iso(),
        })
    return records


def dispatch_committee_invites(notice: dict, notice_ref: str, records: List[dict]) -> None:
    """Fire best-effort emails to all external invitees. Non-blocking."""
    tender_title = notice.get("title", "")
    tender_budget = f"{notice.get('budget_currency', '')} {notice.get('budget_amount') or ''}"
    deadline = (notice.get("submission_deadline") or "")[:10]
    for inv in records:
        accept_url = f"{config.FRONTEND_URL}/committee/accept/{inv['accept_token']}"
        body_html = (
            f"<p>You have been invited to sit on the evaluation committee for the following procurement:</p>"
            f"<table style='width:100%;font-size:13px'>"
            f"<tr><td><strong>Tender Ref</strong></td><td>{notice_ref}</td></tr>"
            f"<tr><td><strong>Title</strong></td><td>{tender_title}</td></tr>"
            f"<tr><td><strong>Budget</strong></td><td>{tender_budget}</td></tr>"
            f"<tr><td><strong>Submission deadline</strong></td><td>{deadline}</td></tr>"
            f"</table>"
            f"<p style='margin-top:16px'>Please accept or decline this invitation using the link below.</p>"
        )
        asyncio.create_task(send_email(
            inv["email"],
            f"PMC Managers — Committee invitation for {notice_ref}",
            wrap(f"Committee invitation · {notice_ref}",
                 body_html, "Accept or decline", accept_url),
        ))
