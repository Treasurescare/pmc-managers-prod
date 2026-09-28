"""PMC v50 — Admin-only email template preview.

`GET  /api/v1/admin/emails/templates`
    List every registered v50 template + its rendered subject.

`GET  /api/v1/admin/emails/preview/{name}?ctx=...`
    Render a single template. `ctx` is optional URL-encoded JSON overriding
    demo values. Returns rendered HTML directly so admins can eyeball it in
    the browser.

`POST /api/v1/admin/emails/test-send`
    Body: `{"template": "award.notification", "to": "you@example.com",
             "ctx": {...}}`
    Dispatches ONE rendered email via the existing Resend integration.

This route is behind the same admin auth guard as the rest of /api/v1/admin/*.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from emails_option_e import (
    TEMPLATES,
    all_template_names,
    preview_all,
    render_email,
    send_e_email,
)

router = APIRouter(prefix="/api/v1/admin/emails", tags=["admin-emails"])


@router.get("/templates")
def list_templates() -> Dict[str, Any]:
    """Return every template key + rendered demo subject."""
    rendered = preview_all()
    out = []
    for key in all_template_names():
        r = rendered.get(key, {})
        out.append({
            "key": key,
            "file": TEMPLATES[key],
            "subject": r.get("subject", ""),
            "error": r.get("error"),
        })
    return {"count": len(out), "templates": out}


@router.get("/preview/{name}", response_class=HTMLResponse)
def preview_one(name: str, ctx: Optional[str] = Query(default=None)) -> HTMLResponse:
    ctx_dict: Dict[str, Any] = {}
    if ctx:
        try:
            ctx_dict = json.loads(ctx)
        except Exception as exc:
            raise HTTPException(400, f"ctx must be valid JSON: {exc}")
    demo = preview_all().get(name)
    base_ctx = {}
    if demo and "html" in demo:
        pass  # demo already rendered; but we want overrides
    # Full re-render with overrides so any ctx key wins
    try:
        _, html = render_email(name, {**_demo(), **ctx_dict})
    except KeyError:
        raise HTTPException(404, f"Unknown template: {name}")
    return HTMLResponse(html)


class TestSendBody(BaseModel):
    template: str
    to: str
    ctx: Optional[Dict[str, Any]] = None


@router.post("/test-send")
async def test_send(body: TestSendBody, request: Request) -> Dict[str, Any]:
    if body.template not in TEMPLATES:
        raise HTTPException(404, f"Unknown template: {body.template}")
    return await send_e_email(body.template, body.to, {**_demo(), **(body.ctx or {})})


def _demo() -> Dict[str, Any]:
    """Reusable demo context so preview + test send share defaults."""
    return preview_all().get("account.verify_email", {}).get("_demo", {}) or {
        "first_name": "Aisha",
        "company_name": "Emerald Corporates",
        "email": "aisha@example.com",
        "expires_at": "24 hours",
        "verify_url": "https://pmcmanagers.com/verify/abc123",
        "reset_url": "https://pmcmanagers.com/reset/abc123",
        "tender_title": "Turnkey IVF Laboratory Setup",
        "notice_ref": "PMC-NOT-2026-0055",
        "tender_url": "https://pmcmanagers.com/notices/PMC-NOT-2026-0055",
        "amount": "USD 31,600",
        "reference": "TXN-882312",
        "award_ref": "PMC-AWD-2026-00007",
        "award_value": "USD 2,090,000",
        "sign_url": "https://pmcmanagers.com/docusign/env/abc123",
        "sign_by": "5 Mar 2026",
        "help_url": "https://pmcmanagers.com/help",
    }
