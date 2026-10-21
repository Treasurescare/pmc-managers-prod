"""v56s — App-level settings: the Go-Live switch.

Go-Live is a persisted admin toggle, OFF by default. While OFF, Sector and
Contract Type stay optional on notices and vendor registration. When an admin
switches it ON, the server enforces that NEW notices and NEW vendor
registrations carry a sector + contract type. Existing records are untouched.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from db import db
from models.base import now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

GO_LIVE_KEY = "go_live"


async def is_go_live() -> bool:
    doc = await db.app_settings.find_one({"key": GO_LIVE_KEY})
    return bool(doc and doc.get("value"))


class GoLiveIn(BaseModel):
    enabled: bool


@router.get("/go-live/public")
async def go_live_public() -> dict:
    """PUBLIC — lets the registration portal + notice board know whether the
    Sector/Contract taxonomy is mandatory yet."""
    return {"go_live": await is_go_live()}


@router.get("/go-live")
async def go_live_admin(admin=Depends(require_role("admin", "reviewer"))) -> dict:
    doc = await db.app_settings.find_one({"key": GO_LIVE_KEY})
    return {"go_live": bool(doc and doc.get("value")),
            "updated_at": (doc or {}).get("updated_at"),
            "updated_by": (doc or {}).get("updated_by")}


@router.put("/go-live")
async def set_go_live(payload: GoLiveIn, admin=Depends(require_role("admin"))) -> dict:
    await db.app_settings.update_one(
        {"key": GO_LIVE_KEY},
        {"$set": {"key": GO_LIVE_KEY, "value": bool(payload.enabled),
                  "updated_at": now_iso(), "updated_by": admin.get("email")}},
        upsert=True)
    await audit_log("settings.go_live", admin, "settings", GO_LIVE_KEY,
                    {"enabled": bool(payload.enabled)})
    return {"go_live": bool(payload.enabled)}
