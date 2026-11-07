"""iPhone push notifications (APNs token auth) for suppliers' saved-alert matches. No-op until APNS_* keys are set."""
import os
import time
import uuid
from typing import Any, Dict

import httpx
import jwt
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor

router = APIRouter(prefix="/api/v1/push/ios", tags=["push-ios"])
_jwt: Dict[str, Any] = {"v": None, "exp": 0}
DEAD = ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic")


class DeviceIn(BaseModel):
    token: str = Field(min_length=10, max_length=512, pattern=r"^[0-9a-fA-F]+$")


def _cfg():
    c = {k: os.environ.get(f"APNS_{k}") for k in ("KEY_ID", "TEAM_ID", "BUNDLE_ID", "KEY_P8")}
    return c if all(c.values()) else None


def _provider_jwt(c) -> str:
    now = int(time.time())
    if not _jwt["v"] or now >= _jwt["exp"]:
        _jwt["v"] = jwt.encode({"iss": c["TEAM_ID"], "iat": now}, c["KEY_P8"].replace("\\n", "\n"),
                               algorithm="ES256", headers={"kid": c["KEY_ID"]})
        _jwt["exp"] = now + 50 * 60
    return _jwt["v"]


@router.post("/register")
async def register(body: DeviceIn, vendor=Depends(current_vendor)):
    await db.push_devices.update_one({"token": body.token}, {"$set": {
        "token": body.token, "platform": "ios", "vendor_id": vendor["id"], "email": vendor.get("email"),
        "active": True, "updated_at": now_iso()}}, upsert=True)
    return {"ok": True, "enabled": bool(_cfg())}


@router.post("/unregister")
async def unregister(body: DeviceIn, vendor=Depends(current_vendor)):
    await db.push_devices.update_one({"token": body.token, "vendor_id": vendor["id"]}, {"$set": {"active": False, "updated_at": now_iso()}})
    return {"ok": True}


async def send_to_vendor(vendor_id: str, title: str, body: str, url: str = "") -> int:
    c = _cfg()
    if not c or not vendor_id:
        return 0
    host = "https://api.sandbox.push.apple.com" if os.environ.get("APNS_ENV") == "sandbox" else "https://api.push.apple.com"
    payload = {"aps": {"alert": {"title": title[:120], "body": body[:300]}, "sound": "default"}, "url": url}
    sent = 0
    async with httpx.AsyncClient(http2=True, base_url=host, timeout=10) as cl:
        async for d in db.push_devices.find({"vendor_id": vendor_id, "active": True}):
            try:
                r = await cl.post(f"/3/device/{d['token']}", json=payload, headers={
                    "authorization": f"bearer {_provider_jwt(c)}", "apns-topic": c["BUNDLE_ID"],
                    "apns-push-type": "alert", "apns-priority": "10", "apns-id": str(uuid.uuid4())})
            except httpx.HTTPError:
                continue
            if r.status_code == 200:
                sent += 1
            elif any(x in (r.text or "") for x in DEAD):
                await db.push_devices.update_one({"_id": d["_id"]}, {"$set": {"active": False, "dead_reason": r.text[:80]}})
    return sent


async def ensure_indexes() -> None:
    await db.push_devices.create_index("token", unique=True)
    await db.push_devices.create_index("vendor_id")
