"""Admin email health check: config presence, Resend domain status, and a real test send."""
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

import config
from audit import audit_log
from emails import last_error, send_email, wrap
from models.base import now_iso
from security import require_csrf, require_role

router = APIRouter(tags=["email-health"])
ADMIN = Depends(require_role("admin"))


async def _domains() -> dict:
    if not config.RESEND_API_KEY:
        return {"ok": False, "error": "RESEND_API_KEY is not set on this server"}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://api.resend.com/domains", headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"})
        if r.status_code >= 400:
            msg = (r.json() or {}).get("message", r.text)[:200]
            if "restricted to only send" in msg:
                return {"ok": True, "send_only": True, "items": []}
            return {"ok": False, "error": f"Resend rejected the key ({r.status_code}): {msg}"}
        items = [{"name": d.get("name"), "status": d.get("status"), "region": d.get("region")} for d in (r.json() or {}).get("data", [])]
        return {"ok": True, "items": items}
    except Exception as e:
        return {"ok": False, "error": f"Could not reach Resend: {e}"}


def _sender_domain() -> str:
    return (config.EMAIL_FROM_ADDRESS or "").split("@")[-1].lower()


@router.get("/api/v1/admin/email/health")
async def email_health(admin=ADMIN):
    d = await _domains()
    dom = _sender_domain()
    match = next((x for x in d.get("items", []) if (x["name"] or "").lower() == dom), None)
    tips = []
    if not config.RESEND_API_KEY:
        tips.append("Add RESEND_API_KEY to the server's settings (AWS Parameter Store) and restart the app.")
    elif not d["ok"]:
        tips.append("The Resend key looks wrong or revoked — create a new key in Resend and update it on the server.")
    elif d.get("send_only"):
        tips.append("Your Resend key is send-only, so domain status can't be read here — use 'Send test email' to confirm delivery.")
    elif not match:
        tips.append(f"Your sender address uses {dom or '(none)'}, but that domain isn't added in Resend. Add and verify it in Resend → Domains.")
    elif match["status"] != "verified":
        tips.append(f"Domain {dom} is '{match['status']}' in Resend — add the DNS records Resend shows, then click Verify.")
    return {"resend_key_set": bool(config.RESEND_API_KEY), "from_name": config.EMAIL_FROM_NAME, "from_address": config.EMAIL_FROM_ADDRESS,
            "reply_to": config.EMAIL_REPLY_TO or None, "sender_domain": dom, "domains": d, "sender_domain_status": (match or {}).get("status"),
            "tips": tips, "checked_at": now_iso()}


class TestIn(BaseModel):
    to: EmailStr


@router.post("/api/v1/admin/email/test", dependencies=[Depends(require_csrf)])
async def email_test(body: TestIn, admin=ADMIN):
    ok = await send_email(str(body.to), "[PMC] Test email — your email setup works",
                          wrap("Email setup check", f"<p>This is a test sent by {admin.get('email')} from the PMC admin console at {now_iso()[:16]} UTC.</p>"
                               "<p>If you can read this, PMC emails (invites, receipts, statements) are being delivered.</p>"))
    await audit_log("admin.email_test", admin, "email", str(body.to), {"ok": ok})
    return {"ok": ok, "error": "" if ok else last_error(str(body.to))}
