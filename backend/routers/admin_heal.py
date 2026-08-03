"""Wave 14 — one-shot production data healers.

Endpoints under /api/v1/admin/heal/* let a signed-in admin fix legacy data
without shell access. Currently:

  POST /admin/heal/rename-admin  — rename the legacy `admin@pmcmanagers.com`
                                    to `adminsupport@pmcmanagers.com` if the
                                    former exists and the latter does not.
"""
from fastapi import APIRouter, Depends

import config
from db import db
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/admin/heal", tags=["admin-heal"])


@router.post("/rename-admin")
async def rename_stale_admin(admin=Depends(require_role("admin"))):
    """If the DB has a legacy `admin@pmcmanagers.com` and the correct
    `adminsupport@pmcmanagers.com` is missing, rename the legacy row."""
    legacy = await db.admin_users.find_one({"email": "admin@pmcmanagers.com"})
    correct = await db.admin_users.find_one({"email": config.ADMIN_EMAIL})
    if not legacy:
        return {"ok": True, "action": "noop", "reason": "no legacy row"}
    if correct:
        # Both exist — do NOT overwrite. Delete legacy row to avoid dupes.
        await db.admin_users.delete_one({"_id": legacy["_id"]})
        await audit_log("admin.heal.remove_legacy", admin, "admin_user",
                        "admin@pmcmanagers.com", {"deleted": True})
        return {"ok": True, "action": "deleted_legacy",
                "reason": "correct row already present"}
    await db.admin_users.update_one({"_id": legacy["_id"]},
                                     {"$set": {"email": config.ADMIN_EMAIL}})
    await audit_log("admin.heal.rename", admin, "admin_user", config.ADMIN_EMAIL,
                    {"from": "admin@pmcmanagers.com"})
    return {"ok": True, "action": "renamed",
            "from": "admin@pmcmanagers.com", "to": config.ADMIN_EMAIL}
