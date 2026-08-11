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
import hashlib
import hmac
import logging
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
DS_HMAC_SECRET = os.environ.get("DOCUSIGN_CONNECT_HMAC_SECRET", "")

_log = logging.getLogger("docusign.webhook")


def _verify_hmac(raw_body: bytes, headers) -> bool:
    """Verify DocuSign Connect HMAC-SHA256 signature.

    DocuSign delivers up to 3 signatures via headers x-docusign-signature-1..3
    (base64-encoded HMAC-SHA256 of the raw request body using the shared secret).
    Any match is accepted. Returns True if secret is not configured (opt-in).
    """
    if not DS_HMAC_SECRET:
        return True  # HMAC not configured — accept (dev only)
    expected = base64.b64encode(
        hmac.new(DS_HMAC_SECRET.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("ascii")
    for i in range(1, 4):
        got = headers.get(f"x-docusign-signature-{i}") or headers.get(f"X-DocuSign-Signature-{i}")
        if got and hmac.compare_digest(got.strip(), expected):
            return True
    return False


def _consent_url(redirect_uri: Optional[str] = None) -> str:
    """Primary consent URL uses our own frontend as the redirect target so we
    can drop the user back at the admin console. Callers may override the
    redirect_uri (e.g. a DocuSign-hosted URI that ships pre-whitelisted on
    every sandbox app)."""
    redirect_uri = redirect_uri or f"{config.FRONTEND_URL}/admin"
    return f"https://{DS_AUTH_HOST}/oauth/auth?" + urlencode({
        "response_type": "code",
        "scope": "signature impersonation",
        "client_id": DS_INT_KEY,
        "redirect_uri": redirect_uri,
    })


def _consent_url_fallback() -> str:
    """Fallback consent URL using a DocuSign-hosted redirect that is
    pre-whitelisted on every sandbox app by default. Use this when the user
    hasn't added our frontend URL to their app's redirect URI list."""
    return _consent_url("https://apps-d.docusign.com/api-integrator-key")


def _load_private_key() -> bytes:
    """Return the DocuSign RSA private key bytes.

    Two sources supported (checked in order):
      1. ``DOCUSIGN_PRIVATE_KEY_B64`` env var — base64-encoded PEM. Preferred
         for cloud deploys (AWS App Runner / ECS / Heroku) where you can't
         easily mount a file.
      2. ``DOCUSIGN_PRIVATE_KEY_PATH`` file on disk — used in local/dev.
    """
    b64 = os.environ.get("DOCUSIGN_PRIVATE_KEY_B64", "").strip()
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception as e:
            raise HTTPException(500, f"DOCUSIGN_PRIVATE_KEY_B64 is set but not valid base64: {e}")
    p = Path(DS_PRIVATE_KEY_PATH)
    if not p.exists():
        raise HTTPException(500, "DocuSign private key not found — set DOCUSIGN_PRIVATE_KEY_B64 or place the file at DOCUSIGN_PRIVATE_KEY_PATH")
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
    if not d:
        raise HTTPException(404, f"Award document '{kind}' not found for bid {bid_id}")
    pdf = d.get("pdf_bytes") or d.get("pdf_b64")
    if not pdf:
        raise HTTPException(404, f"Award document '{kind}' has no PDF payload")
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
                     client_user_id: Optional[str]) -> tuple[str, str]:
    """Send an envelope; embedded when client_user_id is set, email-mode when None.
    Returns (envelope_id, sdk_client)."""
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
    signer_kwargs = dict(
        email=signer_email,
        name=signer_name,
        recipient_id="1",
        routing_order="1",
        tabs=ds.Tabs(sign_here_tabs=[sign_here, sign_here_fixed]),
    )
    # Only include client_user_id when embedded signing is requested. If it
    # is set, DocuSign will NOT email the signer (embedded flow). When left
    # off, DocuSign emails the signer a hosted signing link (email flow).
    if client_user_id:
        signer_kwargs["client_user_id"] = client_user_id
    signer = ds.Signer(**signer_kwargs)
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
        "consent_url_fallback": _consent_url_fallback() if configured else None,
        "redirect_uri_primary": f"{config.FRONTEND_URL}/admin",
        "redirect_uri_fallback": "https://apps-d.docusign.com/api-integrator-key",
        "error": err,
    }


@router.get("/consent-url")
async def consent_url_endpoint():
    return {
        "url": _consent_url(),
        "url_fallback": _consent_url_fallback(),
    }


# ---------------- Award envelope ----------------

class EnvelopeRequest(BaseModel):
    signer_name: str
    signer_email: EmailStr
    return_url: Optional[str] = None
    # Wave 44 — email-mode envelope: when "email", DocuSign emails the signer
    # a hosted signing link (better for signers not logged into PMC). Default
    # remains "embedded" (in-app iframe with a one-time recipient view URL).
    delivery: Optional[str] = "embedded"


@router.post("/awards/{bid_id}/{kind}/envelope")
async def create_award_envelope(
    bid_id: str, kind: str, req: EnvelopeRequest,
    admin=Depends(current_admin),
):
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(400, "kind must be po|sla|contract")
    pdf, fname, award_ref = await _load_award_pdf(bid_id, kind)
    client = _client()
    delivery = (req.delivery or "embedded").lower()
    client_user_id: Optional[str] = (
        f"pmc:award:{bid_id}:{kind}:{req.signer_email}" if delivery == "embedded" else None
    )
    subject = f"PMC {award_ref} · {kind.upper()} — signature requested"
    envelope_id, _ = _create_envelope(
        client, pdf, fname, req.signer_name, str(req.signer_email),
        subject, client_user_id,
    )
    return_url = req.return_url or f"{config.FRONTEND_URL}/admin?ds_signed=1"
    signing_url = None
    if delivery == "embedded":
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
        "delivery": delivery,
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email"),
    }
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id}, {"$set": doc}, upsert=True,
    )
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "delivery": delivery,
            "expires_in": 300 if signing_url else None, "status": "sent"}


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


# ---------------- Vendor-facing endpoints (Wave 44) ----------------

from routers.vendor_auth import current_vendor  # noqa: E402


@router.get("/mine")
async def list_my_envelopes(vendor=Depends(current_vendor)):
    """List envelopes where the vendor is the intended signer OR the envelope
    was created for one of the vendor's awarded bids."""
    ve = vendor.get("email")
    if not ve:
        return {"items": []}
    # Find bids owned by this vendor.
    bid_ids = []
    async for b in db.bids.find({"vendor_email": ve}, {"id": 1}):
        if b.get("id"):
            bid_ids.append(b["id"])
    query = {"$or": [{"signer_email": ve}, {"bid_id": {"$in": bid_ids}}]}
    cursor = db.docusign_envelopes.find(query).sort("created_at", -1).limit(50)
    items = []
    async for row in cursor:
        row.pop("_id", None)
        items.append(row)
    return {"items": items}


@router.post("/mine/awards/{bid_id}/{kind}/envelope")
async def vendor_request_award_envelope(
    bid_id: str, kind: str, req: EnvelopeRequest,
    vendor=Depends(current_vendor),
):
    """A vendor requests to sign one of their own awarded contract PDFs.
    Server-side guard: the bid must be awarded AND owned by the calling vendor."""
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(400, "kind must be po|sla|contract")
    ve = vendor.get("email")
    bid = await _load_bid(bid_id)
    if bid.get("vendor_email") != ve:
        raise HTTPException(403, "This bid is not owned by the calling vendor")
    if bid.get("status") != "awarded":
        raise HTTPException(412, "Bid must be awarded before signing")
    pdf, fname, award_ref = await _load_award_pdf(bid_id, kind)
    client = _client()
    client_user_id = f"pmc:vendor:{bid_id}:{kind}:{ve}"
    subject = f"PMC {award_ref} · {kind.upper()} — please sign"
    envelope_id, _ = _create_envelope(
        client, pdf, fname, req.signer_name or vendor.get("company_name") or ve,
        str(req.signer_email or ve), subject, client_user_id,
    )
    return_url = req.return_url or f"{config.FRONTEND_URL}/vendor/dashboard?ds_signed=1"
    signing_url = _recipient_view(client, envelope_id, req.signer_name or ve,
                                   str(req.signer_email or ve), client_user_id, return_url)
    doc = {
        "envelope_id": envelope_id,
        "kind": "award",
        "sub_kind": kind,
        "bid_id": bid_id,
        "award_ref": award_ref,
        "signer_name": req.signer_name or vendor.get("company_name") or ve,
        "signer_email": str(req.signer_email or ve),
        "client_user_id": client_user_id,
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": ve,
        "vendor_initiated": True,
    }
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id}, {"$set": doc}, upsert=True,
    )
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "expires_in": 300, "status": "sent"}


@router.get("/envelopes/{envelope_id}/combined-pdf")
async def download_combined_pdf(envelope_id: str, admin=Depends(current_admin)):
    """Return the fully-signed combined PDF for a completed envelope.

    Only allowed when envelope status is `completed`. Streams the PDF bytes
    from DocuSign's `EnvelopeDocuments.get_document` (documentId="combined").
    """
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    if row.get("status") not in ("completed",):
        raise HTTPException(412, f"Envelope status is '{row.get('status')}' — must be 'completed' before downloading the signed PDF")
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    try:
        pdf_path = envelopes.get_document(DS_ACCOUNT_ID, "combined", envelope_id)
    except Exception as e:
        raise HTTPException(502, f"DocuSign document fetch failed: {e}")
    try:
        pdf_bytes = Path(pdf_path).read_bytes()
    except Exception:
        raise HTTPException(500, "Could not read the fetched PDF from disk")
    fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}-signed.pdf"
    from fastapi.responses import Response as _R
    return _R(content=pdf_bytes, media_type="application/pdf",
              headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/mine/envelopes/{envelope_id}/combined-pdf")
async def vendor_download_combined_pdf(envelope_id: str, vendor=Depends(current_vendor)):
    """Vendor-facing: download the fully-signed PDF for an envelope they own."""
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    ve = vendor.get("email")
    # Ownership: signer is the vendor OR envelope is against one of vendor's bids.
    if row.get("signer_email") != ve:
        bid = await db.bids.find_one({"id": row.get("bid_id")}) or {}
        if bid.get("vendor_email") != ve:
            raise HTTPException(403, "Not your envelope")
    if row.get("status") != "completed":
        raise HTTPException(412, "Envelope not completed yet")
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    try:
        pdf_path = envelopes.get_document(DS_ACCOUNT_ID, "combined", envelope_id)
    except Exception as e:
        raise HTTPException(502, f"DocuSign document fetch failed: {e}")
    pdf_bytes = Path(pdf_path).read_bytes()
    fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}-signed.pdf"
    from fastapi.responses import Response as _R
    return _R(content=pdf_bytes, media_type="application/pdf",
              headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ---------------- Connect webhook ----------------

@router.post("/webhook")
async def docusign_webhook(request: Request):
    """DocuSign Connect (JSON SIM) callback. Updates envelope status in DB."""
    raw_body = await request.body()
    if not _verify_hmac(raw_body, request.headers):
        _log.warning("DocuSign webhook HMAC verification failed")
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
    try:
        import json as _json
        payload = _json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        payload = {}
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
