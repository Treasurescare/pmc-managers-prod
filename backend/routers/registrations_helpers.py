"""Helpers for routers/registrations.py::admin_decide.

Extracts the per-action side effects (create vendor row + email, notify
rejection, notify clarification) so the router branch stays small.
"""
import asyncio
import secrets

import config
from db import db, next_sequence
from models.base import now_iso
from security import hash_password
from emails import send_email, wrap


async def approve_and_create_vendor(doc: dict) -> dict:
    """Assign a vendor_ref, insert the vendors row, email the new supplier."""
    seq = await next_sequence("vendor_seq")
    vendor_ref = f"PMC-SUP-{seq:06d}"
    temp_password = secrets.token_urlsafe(9)
    await db.vendors.insert_one({
        "vendor_ref": vendor_ref,
        "email": (doc["email"] or "").lower(),
        "company_name": doc.get("company_name"),
        "country": doc.get("country"),
        "kz_licenses": doc.get("kz_licenses") or [],
        "profile": {k: doc.get(k) for k in doc.keys() if k not in ("_id", "magic_token", "status")},
        "tenant_id": doc.get("tenant_id", config.DEFAULT_TENANT_ID),
        "password_hash": hash_password(temp_password),
        "must_change_password": True,
        "is_active": True,
        "created_at": now_iso(),
    })
    login_url = f"{config.FRONTEND_URL}/vendor/login"
    await send_email(
        doc["email"],
        "PMC Managers — Registration approved · Login details",
        wrap(f"You're approved · {vendor_ref}",
             f"<p>Congratulations. Your PMC Managers vendor registration has been approved. "
             f"Your supplier reference is <strong>{vendor_ref}</strong>.</p>"
             f"<p>You can now log in to the Vendor Portal to browse tenders and submit bids.</p>"
             f"<p><strong>Email:</strong> {doc['email']}<br/>"
             f"<strong>Temporary password:</strong> <code>{temp_password}</code></p>"
             f"<p>You will be asked to set a new password on your first login.</p>",
             "Sign in to the Vendor Portal", login_url),
    )
    return {"status": "approved", "vendor_ref": vendor_ref}


def dispatch_rejection_email(doc: dict, notes: str) -> None:
    asyncio.create_task(send_email(
        doc["email"],
        "PMC Managers — Registration update",
        wrap("Registration update",
             f"<p>Thank you for your interest. Unfortunately your registration was not approved at this time.</p>"
             f"<p><em>Reason:</em> {notes}</p>"),
    ))


def dispatch_clarification_email(doc: dict, notes: str) -> None:
    resume_url = f"{config.FRONTEND_URL}/register/resume?token={doc['magic_token']}"
    asyncio.create_task(send_email(
        doc["email"],
        "PMC Managers — Clarification needed",
        wrap("Clarification needed on your registration",
             f"<p>We reviewed your submission and need some clarification before approving.</p>"
             f"<p><em>Reviewer notes:</em> {notes}</p>",
             "Resume registration", resume_url),
    ))
