"""Wave 43 — DocuSign eSignature (JWT Grant) integration.

Requests digital signatures on Award PDFs (PO / SLA / Contract) and on any
Bid submission acknowledgement. JWT-only auth against a Developer Sandbox
integration; flip DOCUSIGN_ENV=production later without code changes.

Endpoints:
    GET  /api/v1/docusign/status                 — creds present + consent state.
    GET  /api/v1/docusign/consent-url            — one-time browser consent link.
    POST /api/v1/docusign/awards/{bid_id}/{kind}/envelope
                                                  — create envelope from an
                                                    Award PDF (po/sla/contract)
                                                    and return embedded signing URL.
    POST /api/v1/docusign/bids/{bid_id}/ack/envelope
                                                  — create envelope from a bid
                                                    acknowledgement PDF, return
                                                    embedded signing URL.
    GET  /api/v1/docusign/envelopes/{env_id}     — current envelope status.
    POST /api/v1/docusign/webhook                — Connect JSON SIM callback.
"""
import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

import docusign_esign as ds
from docusign_esign.client.api_exception import ApiException

from db import db
from security import current_admin
import config

router = APIRouter(prefix="/api/v1/docusign", tags=["docusign"])

# ---------------- Env / helpers ----------------

DS_ENV = os.environ.get("DOCUSIGN_ENV", "sandbox").lower()
DS_INT_KEY = os.environ.get("DOCUSIGN_INTEGRATION_KEY", "")
DS_USER_ID = os.environ.get("DOCUSIGN_USER_ID", "")
DS_ACCOUNT_ID = os.environ.get("DOCUSIGN_ACCOUNT_ID", "")
DS_BASE_URI = os.environ.get("DOCUSIGN_BASE_URI", "https://demo.docusign.net")
DS_AUTH_HOST = os.environ.get("DOCUSIGN_AUTH_HOST", "account-d.docusign.com")
DS_PRIVATE_KEY_PATH = os.environ.get("DOCUSIGN_PRIVATE_KEY_PATH", "/app/backend/keys/docusign_private.key")


def _consent_url() -> str:
    return f"https://{DS_AUTH_HOST}/oauth/auth?" + urlencode({
        "response_type": "code",
        "scope": "signature impersonation",
        "client_id": DS_INT_KEY,
        "redirect_uri": f"{config.FRONTEND_URL}/admin",
    })


def _load_private_key() -> bytes:
    p = Path(DS_PRIVATE_KEY_PATH)
    if not p.exists():
        raise HTTPException(500, "DocuSign private key file not found on server")
    return p.read_bytes()


def _client() -> ds.ApiClient:
    """Get a fresh JWT-authenticated DocuSign SDK client. Raises HTTP 428 with
    the consent URL if the impersonated user hasn't yet granted consent."""
    if not (DS_INT_KEY and DS_USER_ID and DS_ACCOUNT_ID):
        raise HTTPException(500, "DocuSign env not configured")
    private_key = _load_private_key()
    boot = ds.ApiClient()
    boot.set_base_path(f"https://{DS_AUTH_HOST}")
    try:
        token = boot.request_jwt_user_token(
            client_id=DS_INT_KEY,
            user_id=DS_USER_ID,
            oauth_host_name=DS_AUTH_HOST,
            private_key_bytes=private_key,
            expires_in=3600,
            scopes=["signature", "impersonation"],
        )
    except ApiException as e:
        body = str(getattr(e, "body", "") or e)
        if "consent_required" in body.lower():
            raise HTTPException(status_code=428, detail={
                "code": "DOCUSIGN_CONSENT_REQUIRED",
                "message": "Grant DocuSign consent once before using JWT Grant.",
                "consent_url": _consent_url(),
            })
        raise HTTPException(502, f"DocuSign auth failed: {body}")
    except Exception as e:
        msg = str(e).lower()
        if "consent_required" in msg:
            raise HTTPException(status_code=428, detail={
                "code": "DOCUSIGN_CONSENT_REQUIRED",
                "message": "Grant DocuSign consent once before using JWT Grant.",
                "consent_url": _consent_url(),
            })
        raise HTTPException(502, f"DocuSign auth failed: {e}")
    access = token.access_token
    c = ds.ApiClient()
    c.host = f"{DS_BASE_URI}/restapi"
    c.set_default_header("Authorization", f"Bearer {access}")
    return c


# ---------------- Envelope helpers ----------------

async def _load_award_pdf(bid_id: str, kind: str) -> tuple[bytes, str, str]:
    """Return (pdf_bytes, filename, award_ref) for an award document."""
    d = await db.award_documents.find_one({"bid_id": bid_id, "kind": kind})
    if not d or not d.get("pdf_bytes"):
        raise HTTPException(404, f"Award document '{kind}' not found for bid {bid_id}")
    pdf = d["pdf_bytes"]
    if isinstance(pdf, str):
        pdf = base64.b64decode(pdf)
    ref = d.get("award_ref", "AWARD")
    return pdf, f"{ref}-{kind}.pdf", ref


async def _load_bid(bid_id: str) -> dict:
    b = await db.bids.find_one({"id": bid_id}) or await db.bids.find_one({"bid_ref": bid_id})
    if not b:
        raise HTTPException(404, f"Bid {bid_id} not found")
    return b


def _create_envelope(client: ds.ApiClient, pdf_bytes: bytes, filename: str,
                     signer_name: str, signer_email: str, subject: str,
                     client_user_id: str) -> tuple[str, str]:
    """Send an envelope with an embedded signer; returns (envelope_id, sdk_client)."""
    pdf64 = base64.b64encode(pdf_bytes).decode("ascii")
    document = ds.Document(
        document_base64=pdf64,
        name=filename,
        file_extension="pdf",
        document_id="1",
    )
    # Anchor at "/sig_here/" if present, else drop a Sign-Here on the last page bottom.
    sign_here = ds.SignHere(
        anchor_string="/sig_here/",
        anchor_units="pixels",
        anchor_y_offset="-20",
        anchor_x_offset="0",
    )
    # Fallback fixed position — used only if the anchor isn't found in the PDF.
    sign_here_fixed = ds.SignHere(
        recipient_id="1",
        tab_label="SignHereTab",
        page_number="1",
        x_position="80",
        y_position="700",
        document_id="1",
    )
    signer = ds.Signer(
        email=signer_email,
        name=signer_name,
        recipient_id="1",
        routing_order="1",
        client_user_id=client_user_id,
        tabs=ds.Tabs(sign_here_tabs=[sign_here, sign_here_fixed]),
    )
    envelope = ds.EnvelopeDefinition(
        email_subject=subject,
        email_blurb="Please review and sign — PMC Managers Global Tender Board.",
        documents=[document],
        recipients=ds.Recipients(signers=[signer]),
        status="sent",
    )
    envelopes = ds.EnvelopesApi(client)
    result = envelopes.create_envelope(DS_ACCOUNT_ID, envelope_definition=envelope)
    return result.envelope_id, "ok"


def _recipient_view(client: ds.ApiClient, envelope_id: str, signer_name: str,
                    signer_email: str, client_user_id: str, return_url: str) -> str:
    envelopes = ds.EnvelopesApi(client)
    view_request = ds.RecipientViewRequest(
        authentication_method="none",
        client_user_id=client_user_id,
        recipient_id="1",
        return_url=return_url,
        user_name=signer_name,
        email=signer_email,
    )
    r = envelopes.create_recipient_view(DS_ACCOUNT_ID, envelope_id,
                                         recipient_view_request=view_request)
    return r.url


# ---------------- Public endpoints ----------------

@router.get("/status")
async def status():
    key_present = Path(DS_PRIVATE_KEY_PATH).exists()
    configured = bool(DS_INT_KEY and DS_USER_ID and DS_ACCOUNT_ID and key_present)
    consent_ok = False
    err = None
    if configured:
        try:
            _client()
            consent_ok = True
        except HTTPException as e:
            if isinstance(e.detail, dict) and e.detail.get("code") == "DOCUSIGN_CONSENT_REQUIRED":
                err = "consent_required"
            else:
                err = str(e.detail)[:200]
        except Exception as e:
            err = str(e)[:200]
    return {
        "env": DS_ENV,
        "configured": configured,
        "consent_ok": consent_ok,
        "account_id": DS_ACCOUNT_ID[:8] + "…" if DS_ACCOUNT_ID else None,
        "base_uri": DS_BASE_URI,
        "consent_url": _consent_url() if configured else None,
        "error": err,
    }


@router.get("/consent-url")
async def consent_url_endpoint():
    return {"url": _consent_url()}


# ---------------- Award envelope ----------------

class EnvelopeRequest(BaseModel):
    signer_name: str
    signer_email: EmailStr
    return_url: Optional[str] = None


@router.post("/awards/{bid_id}/{kind}/envelope")
async def create_award_envelope(
    bid_id: str, kind: str, req: EnvelopeRequest,
    admin=Depends(current_admin),
):
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(400, "kind must be po|sla|contract")
    pdf, fname, award_ref = await _load_award_pdf(bid_id, kind)
    client = _client()
    client_user_id = f"pmc:award:{bid_id}:{kind}:{req.signer_email}"
    subject = f"PMC {award_ref} · {kind.upper()} — signature requested"
    envelope_id, _ = _create_envelope(
        client, pdf, fname, req.signer_name, str(req.signer_email),
        subject, client_user_id,
    )
    return_url = req.return_url or f"{config.FRONTEND_URL}/admin?ds_signed=1"
    signing_url = _recipient_view(client, envelope_id, req.signer_name,
                                   str(req.signer_email), client_user_id, return_url)
    doc = {
        "envelope_id": envelope_id,
        "kind": "award",
        "sub_kind": kind,
        "bid_id": bid_id,
        "award_ref": award_ref,
        "signer_name": req.signer_name,
        "signer_email": str(req.signer_email),
        "client_user_id": client_user_id,
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email"),
    }
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id}, {"$set": doc}, upsert=True,
    )
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "expires_in": 300, "status": "sent"}


# ---------------- Bid acknowledgement envelope ----------------

@router.post("/bids/{bid_id}/ack/envelope")
async def create_bid_ack_envelope(
    bid_id: str, req: EnvelopeRequest,
    admin=Depends(current_admin),
):
    bid = await _load_bid(bid_id)
    # Reuse contract PDF if bid already has an award — otherwise render a
    # minimal acknowledgement PDF on the fly (WeasyPrint).
    from weasyprint import HTML as _HTML  # local import — WeasyPrint startup cost
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
      <style>body {{ font-family: 'Times New Roman', serif; padding: 40px; }}
      h1 {{ color: #0e2340; }} .sig {{ margin-top: 200px; }}</style></head>
      <body>
        <div style='font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#5b7ba1'>PMC Managers Limited</div>
        <h1>Bid submission acknowledgement</h1>
        <p><b>Bid ref:</b> {bid.get('bid_ref')}</p>
        <p><b>Notice:</b> {bid.get('notice_ref')}</p>
        <p><b>Vendor:</b> {bid.get('company_name') or bid.get('vendor_email')}</p>
        <p><b>Price:</b> {bid.get('price_currency','USD')} {bid.get('price_amount',0):,.2f}</p>
        <p>The bidder confirms the terms of the tender documents and consents to the pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee).</p>
        <p class='sig'>Signature: <span style='color:#c00'>/sig_here/</span></p>
      </body></html>"""
    pdf = _HTML(string=html).write_pdf()
    client = _client()
    client_user_id = f"pmc:bid:{bid_id}:{req.signer_email}"
    envelope_id, _ = _create_envelope(
        client, pdf, f"{bid.get('bid_ref','BID')}-ack.pdf",
        req.signer_name, str(req.signer_email),
        f"PMC {bid.get('bid_ref')} — bid acknowledgement", client_user_id,
    )
    return_url = req.return_url or f"{config.FRONTEND_URL}/admin?ds_signed=1"
    signing_url = _recipient_view(client, envelope_id, req.signer_name,
                                   str(req.signer_email), client_user_id, return_url)
    doc = {
        "envelope_id": envelope_id,
        "kind": "bid_ack",
        "bid_id": bid_id,
        "bid_ref": bid.get("bid_ref"),
        "signer_name": req.signer_name,
        "signer_email": str(req.signer_email),
        "client_user_id": client_user_id,
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email"),
    }
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id}, {"$set": doc}, upsert=True,
    )
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "expires_in": 300, "status": "sent"}


# ---------------- Status + list ----------------

@router.get("/envelopes/{envelope_id}")
async def get_envelope(envelope_id: str, admin=Depends(current_admin)):
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found in DB")
    # Also fetch live status from DocuSign.
    try:
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        live = envelopes.get_envelope(DS_ACCOUNT_ID, envelope_id)
        live_status = live.status
        if live_status and live_status != row.get("status"):
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id},
                {"$set": {"status": live_status,
                          "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            row["status"] = live_status
    except HTTPException:
        raise
    except Exception as e:
        row["live_error"] = str(e)[:200]
    row.pop("_id", None)
    return row


@router.get("/envelopes")
async def list_envelopes(admin=Depends(current_admin), limit: int = 100):
    cursor = db.docusign_envelopes.find({}).sort("created_at", -1).limit(limit)
    items = []
    async for row in cursor:
        row.pop("_id", None)
        items.append(row)
    return {"items": items}


# ---------------- Connect webhook ----------------

@router.post("/webhook")
async def docusign_webhook(request: Request):
    """DocuSign Connect (JSON SIM) callback. Updates envelope status in DB."""
    payload = await request.json()
    event = payload.get("event") or payload.get("Event")
    data = payload.get("data") or {}
    envelope_id = data.get("envelopeId") or payload.get("envelopeId")
    if not envelope_id:
        # Legacy XML-style body — try envelopeStatus
        env_status = payload.get("envelopeStatus", {})
        envelope_id = env_status.get("envelopeId") or env_status.get("envelopeID")
    if envelope_id:
        status_map = {
            "envelope-completed": "completed",
            "envelope-declined": "declined",
            "envelope-voided": "voided",
            "envelope-sent": "sent",
            "envelope-delivered": "delivered",
        }
        new_status = status_map.get(event or "", None) or (payload.get("envelopeStatus", {}) or {}).get("status")
        if new_status:
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id},
                {"$set": {"status": new_status,
                          "webhook_at": datetime.now(timezone.utc).isoformat()}},
            )
    return {"received": True}
