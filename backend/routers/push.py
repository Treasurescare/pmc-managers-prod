"""Web Push (VAPID) — subscribe, unsubscribe, admin fan-out.

Uses the standard Web Push protocol (works on Android Chrome/Edge/Samsung
Internet and on iOS 16.4+ *installed* PWAs). No Firebase dependency — the
same VAPID keys drive every browser.

Configuration (backend/.env):
    VAPID_PUBLIC_KEY   — base64url-encoded uncompressed EC P-256 public key
    VAPID_PRIVATE_KEY  — matching PEM private key (single-line, \\n escaped)
    VAPID_CLAIM_EMAIL  — mailto: address used in the VAPID JWT

Generate a fresh pair with:
    python3 -m py_vapid.main --gen  --applicationServerKey=./vapid_priv.pem
    (or `openssl ecparam -name prime256v1 -genkey -noout -out vapid_priv.pem`
     then `openssl ec -in vapid_priv.pem -pubout -outform DER | base64`)
Then copy the base64url pub-key into `/app/frontend/.env` as
`REACT_APP_VAPID_PUBLIC_KEY` so the browser can subscribe.
"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import now_iso
from security import require_role
from routers.vendor_auth import current_vendor

log = logging.getLogger("pmc.push")
router = APIRouter(prefix="/api/v1/push", tags=["push-notifications"])


VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").strip().replace("\\n", "\n")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@pmcmanagers.com")


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=10)
    auth: str = Field(min_length=4)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=10)
    keys: PushKeys
    user_agent: Optional[str] = None
    role: str = Field(default="vendor", pattern="^(vendor|admin|staff)$")
    user_ref: Optional[str] = None


@router.get("/config")
async def get_public_key():
    """Expose the VAPID public key so browsers can subscribe.

    Deliberately anonymous — the public key is public by design.
    """
    return {"public_key": VAPID_PUBLIC_KEY, "enabled": bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)}


@router.post("/subscribe")
async def subscribe(payload: SubscriptionIn):
    """Store or refresh a push subscription. Idempotent on endpoint."""
    doc = {
        "endpoint": payload.endpoint,
        "keys": payload.keys.model_dump(),
        "user_agent": payload.user_agent,
        "role": payload.role,
        "user_ref": payload.user_ref,
        "created_at": now_iso(),
        "last_seen_at": now_iso(),
        "active": True,
    }
    await db.push_subscriptions.update_one(
        {"endpoint": payload.endpoint},
        {"$set": doc},
        upsert=True,
    )
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(payload: dict):
    ep = (payload or {}).get("endpoint")
    if not ep:
        raise HTTPException(status_code=400, detail="endpoint required")
    await db.push_subscriptions.update_one({"endpoint": ep}, {"$set": {"active": False}})
    return {"ok": True}


class TestPushIn(BaseModel):
    title: str = "PMC test push"
    body: str = "If you see this, push notifications work end-to-end."
    url: str = "/"
    role: Optional[str] = None
    user_ref: Optional[str] = None


@router.post("/test")
async def send_test(payload: TestPushIn, admin=Depends(require_role("admin"))):
    """Admin-only helper: fan a test message out to every active subscription
    (optionally filtered by role or user_ref).
    """
    count = await fanout(payload.title, payload.body, payload.url,
                         role=payload.role, user_ref=payload.user_ref)
    return {"ok": True, "delivered": count}


async def fanout(title: str, body: str, url: str = "/",
                 role: Optional[str] = None, user_ref: Optional[str] = None) -> int:
    """Deliver a push message to every matching active subscription.

    Called from trigger points (awards, corrigenda, deadline cron). Returns
    the number of subscriptions we successfully pushed to. Silently swallows
    per-endpoint failures — one dead subscription must not tank the fan-out.
    """
    if not (VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY):
        log.info("push.fanout skipped: VAPID keys not configured")
        return 0

    try:
        from pywebpush import webpush, WebPushException  # local import so backend still boots if wheel is missing
    except Exception as exc:  # noqa: BLE001
        log.warning("push.fanout skipped: pywebpush unavailable (%s)", exc)
        return 0

    q: dict = {"active": True}
    if role:
        q["role"] = role
    if user_ref:
        q["user_ref"] = user_ref

    import json as _json
    payload = _json.dumps({"title": title, "body": body, "url": url})

    delivered = 0
    async for sub in db.push_subscriptions.find(q):
        try:
            webpush(
                subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            )
            delivered += 1
        except WebPushException as e:
            # 404 / 410 → subscription gone, mark inactive so we don't retry
            if getattr(e, "response", None) and e.response.status_code in (404, 410):
                await db.push_subscriptions.update_one(
                    {"_id": sub["_id"]}, {"$set": {"active": False}}
                )
            else:
                log.warning("push.deliver failed endpoint=%s err=%s",
                             sub.get("endpoint", "")[:60], e)
        except Exception as exc:  # noqa: BLE001
            log.warning("push.deliver crashed: %s", exc)
    return delivered


@router.get("/subscriptions")
async def list_subscriptions(admin=Depends(require_role("admin"))) -> dict:
    items: List[dict] = []
    async for s in db.push_subscriptions.find({"active": True}).sort("created_at", -1).limit(500):
        items.append({
            "id": str(s["_id"]),
            "endpoint": (s.get("endpoint") or "")[:80] + "…",
            "role": s.get("role"),
            "user_ref": s.get("user_ref"),
            "user_agent": s.get("user_agent"),
            "created_at": s.get("created_at"),
            "last_seen_at": s.get("last_seen_at"),
        })
    return {"items": items, "total": len(items)}
