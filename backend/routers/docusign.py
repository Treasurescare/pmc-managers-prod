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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

import docusign_esign as ds
from docusign_esign.client.api_exception import ApiException

from db import db
from pdf_brand import brand_html
from security import current_admin, require_role
from audit import audit_log
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
    Any match is accepted.

    SEC-003: in production the shared secret MUST be configured. If it is
    missing, we fail CLOSED (reject the webhook) rather than fail open. In
    non-production envs an unset secret is still accepted with a loud log, so
    local sandbox webhooks stay testable.
    """
    if not DS_HMAC_SECRET:
        env = os.environ.get("ENV", "").lower() or os.environ.get("DEPLOY_ENV", "").lower()
        if env == "production":
            _log.error(
                "[PMC-SEC-003] DOCUSIGN_CONNECT_HMAC_SECRET not set in production — "
                "rejecting webhook. Configure the secret in EB env vars.",
            )
            return False
        _log.warning(
            "[PMC-SEC-003] DOCUSIGN_CONNECT_HMAC_SECRET not set — accepting unsigned "
            "webhook (NON-PROD ONLY).",
        )
        return True
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


def _fetch_document_bytes(envelopes_api, envelope_id: str, document_id: str = "combined") -> bytes:
    """v51d — Robust DocuSign document fetch.

    docusign-esign's EnvelopesApi.get_document() by default returns a str path
    to a NamedTemporaryFile. On AWS EB that tempfile is sometimes auto-deleted
    (or returned as empty bytes-mode) before our next line reads it, surfacing
    as HTTP 500 "Could not read the fetched PDF from disk" to the admin.

    Reading raw urllib3 bytes directly via `_preload_content=False` bypasses
    the tempfile hop entirely, works on every SDK version and every hosting
    environment (EB, ECS, Fargate, local docker)."""
    try:
        resp = envelopes_api.get_document(DS_ACCOUNT_ID, document_id, envelope_id,
                                          _preload_content=False)
        data = resp.read() if hasattr(resp, "read") else getattr(resp, "data", resp)
        if hasattr(resp, "release_conn"):
            try: resp.release_conn()
            except Exception: pass
    except TypeError:
        # Very old SDK that doesn't accept _preload_content — fall back to the
        # path return and read immediately before the tempfile can be GC'd.
        p = envelopes_api.get_document(DS_ACCOUNT_ID, document_id, envelope_id)
        if isinstance(p, (bytes, bytearray)):
            return bytes(p)
        return Path(p).read_bytes()
    if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
        raise HTTPException(502, "DocuSign returned an empty document body")
    return bytes(data)


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
        raise HTTPException(status_code=424, detail={
                "code": "DOCUSIGN_AUTH_FAILED",
                "message": "DocuSign authentication failed — the integration key or consent in this environment is invalid/expired. Check DOCUSIGN_* settings.",
                "upstream": body[:200],
            })
    except Exception as e:
        msg = str(e).lower()
        if "consent_required" in msg:
            raise HTTPException(status_code=428, detail={
                "code": "DOCUSIGN_CONSENT_REQUIRED",
                "message": "Grant DocuSign consent once before using JWT Grant.",
                "consent_url": _consent_url(),
            })
        raise HTTPException(status_code=424, detail={
            "code": "DOCUSIGN_AUTH_FAILED",
            "message": "DocuSign authentication failed — the integration key or consent in this environment is invalid/expired. Check DOCUSIGN_* settings.",
            "upstream": str(e)[:200],
        })
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
    # v49p fix — tabs MUST carry recipient_id + document_id or DocuSign drops
    # them silently (signer then sees a read-only view with just "Close").
    # Anchor at "/sig_here/" (embedded invisibly in PMC award PDFs at the
    # supplier signature box); fixed fallback at the supplier box position on
    # page 1 for PDFs that predate the marker.
    sign_anchor = ds.SignHere(
        anchor_string="/sig_here/",
        anchor_units="pixels",
        anchor_y_offset="-6",
        anchor_x_offset="0",
        recipient_id="1",
        document_id="1",
        tab_label="Supplier signature",
    )
    date_anchor = ds.DateSigned(
        anchor_string="/ds_here/",
        anchor_units="pixels",
        anchor_y_offset="-6",
        recipient_id="1",
        document_id="1",
        tab_label="Date signed",
    )
    sign_fixed = ds.SignHere(
        recipient_id="1",
        tab_label="SupplierSignHereFixed",
        page_number="1",
        x_position="330",
        y_position="240",
        document_id="1",
    )
    date_fixed = ds.DateSigned(
        recipient_id="1",
        tab_label="SupplierDateFixed",
        page_number="1",
        x_position="330",
        y_position="285",
        document_id="1",
    )
    signer_kwargs = dict(
        email=signer_email,
        name=signer_name,
        recipient_id="1",
        routing_order="1",
        tabs=ds.Tabs(sign_here_tabs=[sign_anchor, sign_fixed],
                     date_signed_tabs=[date_anchor, date_fixed]),
    )
    # Only include client_user_id when embedded signing is requested. If it
    # is set, DocuSign will NOT email the signer (embedded flow). When left
    # off, DocuSign emails the signer a hosted signing link (email flow).
    if client_user_id:
        signer_kwargs["client_user_id"] = client_user_id
    signer = ds.Signer(**signer_kwargs)
    envelope = ds.EnvelopeDefinition(
        email_subject=subject,
        email_blurb="Please review and sign — PMC Managers Global Tender Grid.",
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
    # Private key present if EITHER the B64 env var is set OR a file exists at the disk path
    key_present = bool(os.environ.get("DOCUSIGN_PRIVATE_KEY_B64", "").strip()) or Path(DS_PRIVATE_KEY_PATH).exists()
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


# ---------------- Status sync + completion side effects ----------------

TERMINAL_STATUSES = ("completed", "declined", "voided")


async def _on_envelope_completed(row: dict) -> None:
    """v49y — the missing confirmation: when an envelope completes, notify
    PMC admins (in-app + email), confirm to the vendor, audit-log it and
    stamp the bid. Fired by the webhook AND the polling sync."""
    env_id = row.get("envelope_id")
    ref = row.get("award_ref") or row.get("bid_ref") or env_id
    signer = f"{row.get('signer_name') or ''} ({row.get('signer_email') or ''})".strip()
    try:
        await audit_log("docusign.envelope_completed", None, "docusign_envelope",
                        env_id, {"ref": ref, "signer": row.get("signer_email")})
    except Exception:
        pass
    try:
        from notify import notify_role
        await notify_role(
            "admin",
            f"Signed: {ref}",
            f"<p><b>{signer}</b> has completed signing <b>{ref}</b>. "
            f"The signed PDF is available under DocuSign admin.</p>",
            "docusign_envelope", env_id)
    except Exception as e:
        _log.warning("completion admin notify failed for %s: %s", env_id, e)
    try:
        if row.get("signer_email"):
            from emails import send_email
            portal = f"{config.FRONTEND_URL}/vendor/signatures"
            await send_email(
                row["signer_email"],
                f"[PMC] Signature complete — {ref}",
                f"<p>Dear {row.get('signer_name') or 'Signer'},</p>"
                f"<p>Your signature on <b>{ref}</b> is complete and PMC has been "
                f"notified. You can download the signed copy any time from your "
                f"supplier portal &rarr; Signatures:<br>"
                f"<a href=\"{portal}\">{portal}</a></p>")
    except Exception as e:
        _log.warning("completion vendor email failed for %s: %s", env_id, e)
    try:
        if row.get("bid_id"):
            # v51ax — bids are keyed on _id (ObjectId), not `id`. The old
            # `{"id": bid_id}` filter silently matched nothing, so an
            # admin-completed envelope never stamped the bid and the vendor
            # portal kept showing the document as unsigned (xlsx #17).
            field = f"{row.get('sub_kind') or 'document'}_signed_at"
            from bson import ObjectId as _Oid
            await db.bids.update_one({"_id": _Oid(row["bid_id"])},
                                     {"$set": {field: now_iso(),
                                               "docusign_completed_at": now_iso()}})
    except Exception:
        pass


async def create_escrow_recipient_view(envelope_id: str, side: str, return_url: str) -> str:
    """v56g — mint an EMBEDDED signing URL for one side of an escrow_tx
    envelope so the signer actually signs in-app (not the view-only console
    view) and is redirected back to `return_url` afterwards. If the envelope
    was created email-mode (no client_user_id on the recipient), we first
    convert that recipient to embedded via update_recipients."""
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope row missing")
    signer = None
    for s in (row.get("signers") or []):
        if s.get("side") == side:
            signer = s
            break
    if not signer:
        raise HTTPException(400, f"No signer on side {side}")
    cuid = signer.get("client_user_id") or signer.get("email")
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    if not signer.get("client_user_id"):
        # Legacy email-mode envelope — convert this recipient to embedded.
        recips = ds.Recipients(signers=[ds.Signer(
            recipient_id=str(signer.get("recipient_id")),
            name=signer.get("name"), email=signer.get("email"),
            routing_order=str(signer.get("routing_order") or "1"),
            client_user_id=cuid)])
        envelopes.update_recipients(DS_ACCOUNT_ID, envelope_id,
                                     recipients=recips, resend_envelope="false")
        await db.docusign_envelopes.update_one(
            {"envelope_id": envelope_id, "signers.recipient_id": signer.get("recipient_id")},
            {"$set": {"signers.$.client_user_id": cuid}})
    view = envelopes.create_recipient_view(
        DS_ACCOUNT_ID, envelope_id,
        recipient_view_request=ds.RecipientViewRequest(
            authentication_method="none",
            client_user_id=cuid,
            recipient_id=str(signer.get("recipient_id")),
            user_name=signer.get("name") or signer.get("email"),
            email=signer.get("email"),
            return_url=return_url))
    return view.url


async def _deliver_escrow_signed_document(tid: str, envelope_id: str) -> None:
    """v56f — on escrow-tx envelope completion, download the combined signed
    PDF, store it on the transaction and EMAIL it (attached) to BOTH officers
    so the escrow institution officer actually receives the fully-executed
    document — not just a status flag. Idempotent + best-effort."""
    try:
        from bson import ObjectId as _Oid
        tx = await db.escrow_transactions.find_one({"_id": _Oid(tid)})
        if not tx:
            return
        if (tx.get("signed_document") or {}).get("content_b64"):
            return  # already delivered
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        pdf = _fetch_document_bytes(envelopes, envelope_id, "combined")
        import base64 as _b64
        b64 = _b64.b64encode(pdf).decode("ascii")
        fname = f"PMC-Escrow-Signed-{tx.get('bid_ref') or tid}.pdf"
        await db.escrow_transactions.update_one(
            {"_id": _Oid(tid)},
            {"$set": {"signed_document": {
                "filename": fname, "content_b64": b64,
                "content_type": "application/pdf",
                "envelope_id": envelope_id, "fetched_at": now_iso()}}})
        snap = tx.get("escrow_account_snapshot") or {}
        recipients = []
        for off in (snap.get("escrow_officer") or {}, snap.get("pmc_officer") or {}):
            e = (off.get("email") or "").strip()
            if e and e.lower() not in {r.lower() for r in recipients}:
                recipients.append(e)
        # Also copy the admin who issued the envelope (admin master record).
        creator = (row.get("created_by") if (row := await db.docusign_envelopes.find_one({"envelope_id": envelope_id})) else None)
        if creator and creator.lower() not in {r.lower() for r in recipients}:
            recipients.append(creator)
        from emails import send_email, _wrap
        subject = f"Signed escrow document — {tx.get('bid_ref') or 'EMD'}"
        html = _wrap(
            "Escrow document fully executed",
            f"<p>The EMD escrow receipt &amp; release mandate for bid "
            f"<b>{tx.get('bid_ref') or '—'}</b> (tender "
            f"<b>{tx.get('notice_ref') or '—'}</b>) has now been signed by "
            f"both officers. The fully-executed PDF is attached for your "
            f"records.</p>",
            "Open your dashboard", f"{config.FRONTEND_URL}/escrow/me")
        for email in recipients:
            try:
                await send_email(email, f"PMC Escrow · {subject}", html,
                    attachments=[{"filename": fname, "content_b64": b64,
                                  "content_type": "application/pdf"}])
            except Exception as ee:
                _log.warning("signed-doc email to %s failed: %s", email, ee)
    except Exception as e:
        _log.warning("escrow signed-doc delivery failed for tx %s: %s", tid, e)


async def _apply_live_status(envelope_id: str, live_status: str) -> None:
    """Update the DB row and fire completion side effects on transition."""
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row or not live_status or row.get("status") == live_status:
        return
    prev = row.get("status")
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id},
        {"$set": {"status": live_status,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    # v52bw — mirror the envelope status onto the linked bid/award so the
    # vendor's dashboard reflects "Admin signed" / "Dispatched to vendor"
    # the moment the admin acts. Previously there were TWO gates:
    #   (1) a webhook/poll had to detect the change, AND
    #   (2) the envelope row had to carry `bid_id` already.
    # Gate (2) is now lifted: if `bid_id` is missing, we fall back to
    # `award_ref` → awards.bid_id, and to `bid_ref` → bids._id lookups.
    try:
        from bson import ObjectId as _Oid
        bid_id = row.get("bid_id")
        if not bid_id and row.get("award_ref"):
            aw = await db.awards.find_one({"award_ref": row["award_ref"]})
            if aw and aw.get("bid_id"):
                bid_id = aw["bid_id"]
                await db.docusign_envelopes.update_one(
                    {"envelope_id": envelope_id},
                    {"$set": {"bid_id": bid_id}})
        if not bid_id and row.get("bid_ref"):
            b = await db.bids.find_one({"bid_ref": row["bid_ref"]})
            if b:
                bid_id = str(b["_id"])
                await db.docusign_envelopes.update_one(
                    {"envelope_id": envelope_id},
                    {"$set": {"bid_id": bid_id}})
        if bid_id:
            sub = (row.get("sub_kind") or row.get("kind") or "document").lower()
            await db.bids.update_one(
                {"_id": _Oid(bid_id)},
                {"$set": {f"{sub}_docusign_status": live_status,
                          "docusign_status": live_status,
                          "docusign_updated_at": now_iso()}})
        if row.get("award_ref"):
            await db.awards.update_one(
                {"award_ref": row["award_ref"]},
                {"$set": {f"{(row.get('sub_kind') or 'document').lower()}_docusign_status": live_status,
                          "docusign_updated_at": now_iso()}})
    except Exception as e:
        _log.warning("mirror live status failed for %s: %s", envelope_id, e)
    # v56e — escrow transaction envelopes: mirror DocuSign status onto the
    # escrow_transaction so the admin + institution dashboards reflect signing,
    # and on completion mark BOTH officer acknowledgements. (Previously only
    # bids/awards were mirrored, so a completed escrow envelope never showed up.)
    if row.get("kind") == "escrow_tx" and row.get("escrow_transaction_id"):
        try:
            from bson import ObjectId as _Oid3
            tid = row["escrow_transaction_id"]
            upd = {"docusign_status": live_status, "updated_at": now_iso()}
            op = {"$set": upd}
            if live_status == "completed":
                now = now_iso()
                upd["docusign_completed_at"] = now
                tx = await db.escrow_transactions.find_one({"_id": _Oid3(tid)})
                snap = (tx or {}).get("escrow_account_snapshot") or {}
                sigs = dict((tx or {}).get("signatures") or {})
                for side, off in (("pmc", snap.get("pmc_officer") or {}),
                                  ("escrow_institution", snap.get("escrow_officer") or {})):
                    cur = sigs.get(side) or {}
                    if not cur.get("signed_at"):
                        sigs[side] = {"email": off.get("email"),
                                      "action": "acknowledge_receipt",
                                      "comment": "Signed via DocuSign",
                                      "signed_at": now, "via": "docusign"}
                upd["signatures"] = sigs
                op["$push"] = {"audit_trail": {"at": now, "by": "docusign",
                                               "event": "docusign_completed",
                                               "envelope_id": envelope_id}}
            await db.escrow_transactions.update_one({"_id": _Oid3(tid)}, op)
            if live_status == "completed":
                await _deliver_escrow_signed_document(tid, envelope_id)
        except Exception as e:
            _log.warning("escrow_tx reconcile failed for %s: %s", envelope_id, e)

    if live_status == "completed" and prev != "completed":
        await _on_envelope_completed(row)


@router.post("/envelopes/{envelope_id}/refresh")
async def refresh_envelope_status(envelope_id: str, admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))):
    """v52bw — explicit status pull. Called by the admin UI after the admin
    signs or dispatches so the vendor's row flips immediately, without
    waiting for the next poll or a Connect webhook. Returns the live
    status so the admin page can re-render in place."""
    try:
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        live = envelopes.get_envelope(DS_ACCOUNT_ID, envelope_id)
        live_status = (live.status or "").lower()
        await _apply_live_status(envelope_id, live_status)
        return {"ok": True, "status": live_status}
    except Exception as e:
        _log.warning("refresh_envelope_status(%s): %s", envelope_id, e)
        return {"ok": False, "error": str(e)[:200]}


async def _sync_recent_statuses(days: int = 30) -> int:
    """v49y — pull DocuSign status changes in ONE API call and apply them.
    This removes the hard dependency on the Connect webhook being
    configured in the DocuSign account. Best-effort; never breaks lists."""
    try:
        from datetime import timedelta
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        resp = envelopes.list_status_changes(DS_ACCOUNT_ID, from_date=since)
        changed = 0
        for env in (getattr(resp, "envelopes", None) or []):
            env_id = getattr(env, "envelope_id", None)
            status = (getattr(env, "status", None) or "").lower()
            if not env_id or not status:
                continue
            row = await db.docusign_envelopes.find_one({"envelope_id": env_id})
            if row and row.get("status") != status:
                await _apply_live_status(env_id, status)
                changed += 1
        if changed:
            _log.info("status sync applied %d envelope updates", changed)
        return changed
    except Exception as e:
        _log.warning("status sync failed: %s", e)
        return 0


# ---------------- Award envelope ----------------

# v49x — Embedded envelopes never trigger a DocuSign email (client_user_id
# suppresses it by design), so signers heard nothing at send or resend.
# Always email a portal link via Resend so the signer knows a document is
# waiting. Best-effort: envelope flow must not fail on mail errors.
async def _email_signer(signer_email: str, signer_name: str, subject: str, ref: str) -> None:
    try:
        from emails import send_email
        portal = f"{config.FRONTEND_URL}/vendor/signatures"
        html = (
            f"<p>Dear {signer_name or 'Signer'},</p>"
            f"<p>{subject}.</p>"
            f"<p>Please sign in to your PMC supplier portal to review and sign:<br>"
            f"<a href=\"{portal}\">{portal}</a></p>"
            f"<p style=\"color:#5B6B63;font-size:13px\">Reference: {ref} · "
            f"PMC Managers Global Tender Grid</p>"
        )
        await send_email(str(signer_email), f"[PMC] {subject}", html)
    except Exception:
        pass


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
    admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting")),
):
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(400, "kind must be po|sla|contract")
    from routers.bid_challenges import assert_contract_allowed
    await assert_contract_allowed(bid_id)
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
    if delivery == "embedded":
        # v49x — embedded flow suppresses DocuSign's own email; notify via Resend
        await _email_signer(str(req.signer_email), req.signer_name, subject, award_ref)
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "delivery": delivery,
            "expires_in": 300 if signing_url else None, "status": "sent"}


# ---------------- Bid acknowledgement envelope ----------------

@router.post("/bids/{bid_id}/ack/envelope")
async def create_bid_ack_envelope(
    bid_id: str, req: EnvelopeRequest,
    admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting")),
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
    pdf = _HTML(string=brand_html(html)).write_pdf()
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
    # v49x — bid-ack envelopes are always embedded → no DocuSign email; notify
    await _email_signer(str(req.signer_email), req.signer_name,
                        f"PMC {bid.get('bid_ref')} — bid acknowledgement",
                        str(bid.get("bid_ref")))
    return {"envelope_id": envelope_id, "signing_url": signing_url,
            "expires_in": 300, "status": "sent"}


# ---------------- Status + list ----------------

@router.post("/envelopes/{envelope_id}/resend")
async def resend_envelope(envelope_id: str, admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))):
    """v47f — re-send the DocuSign envelope reminder to the current signer.
    Uses the SDK's resend by re-issuing the recipient view URL for embedded
    envelopes, or triggering a reminder for email delivery."""
    env = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not env:
        raise HTTPException(status_code=404, detail="Envelope not found")
    if env.get("status") in ("completed", "declined", "voided"):
        raise HTTPException(status_code=400,
            detail=f"Cannot resend an envelope in status '{env.get('status')}'")
    try:
        client = _client()
        # For both embedded and email delivery, DocuSign provides a resend endpoint
        # via ModifyRecipients (resend_envelope=true). Simpler: recreate the
        # recipient-view URL (embedded) or hit the Envelopes::update with resend.
        signer_name  = env.get("signer_name") or "Signer"
        signer_email = env.get("signer_email") or ""
        if env.get("delivery") == "embedded":
            # v51c fix — _recipient_view needs client_user_id + return_url;
            # the previous 4-arg call raised TypeError → 502 on every resend.
            cuid = env.get("client_user_id") or f"pmc:resend:{envelope_id}:{signer_email}"
            return_url = f"{config.FRONTEND_URL}/admin?ds_signed=1"
            # The recipient view only mints when the DocuSign recipient carries
            # a client_user_id — stamp one on if the envelope predates it.
            try:
                envelopes_api = ds.EnvelopesApi(client)
                recips = envelopes_api.list_recipients(DS_ACCOUNT_ID, envelope_id)
                signers = recips.signers or []
                target = next((s for s in signers
                               if (s.email or "").lower() == signer_email.lower()),
                              signers[0] if signers else None)
                if target and not getattr(target, "client_user_id", None):
                    target.client_user_id = cuid
                    envelopes_api.update_recipients(DS_ACCOUNT_ID, envelope_id,
                                                    recipients=ds.Recipients(signers=signers))
                    await db.docusign_envelopes.update_one(
                        {"envelope_id": envelope_id}, {"$set": {"client_user_id": cuid}})
            except Exception as e2:
                _log.warning("resend: recipient repair failed for %s: %s", envelope_id, e2)
            signing_url = _recipient_view(client, envelope_id, signer_name,
                                          signer_email, cuid, return_url)
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id},
                {"$set": {"last_resent_at": now_iso(),
                          "last_resent_by": admin.get("email")}})
            # v49x — embedded flow sends no DocuSign email; send a reminder
            # with the portal link so "Resend" always reaches the signer.
            await _email_signer(signer_email, signer_name,
                                "Reminder: document awaiting your signature",
                                env.get("award_ref") or env.get("bid_ref") or envelope_id)
            return {"ok": True, "signing_url": signing_url, "delivery": "embedded",
                    "emailed": signer_email}
        # Email delivery: re-issue via ModifyRecipients with resend flag.
        envelopes = ds.EnvelopesApi(client)
        # v49w — The previous ModifyRecipients-with-resend_envelope path
        # was fragile: setting signer.email to the SAME value made DocuSign
        # treat it as a no-op change and no reminder email went out. Use
        # the Envelope-level update which is the documented way to trigger
        # a resend without mutating recipients.
        try:
            envelopes.update(DS_ACCOUNT_ID, envelope_id,
                             envelope=ds.Envelope(status="sent"),
                             resend_envelope="true")
        except Exception:
            # Fallback: refresh the signer email on the first signer and
            # resend. Some DocuSign API variants require this path.
            recips = envelopes.list_recipients(DS_ACCOUNT_ID, envelope_id)
            signers = recips.signers or []
            for s in signers[:1]:
                s.email = signer_email
                s.name = signer_name
            envelopes.update_recipients(DS_ACCOUNT_ID, envelope_id,
                                         recipients=ds.Recipients(signers=signers),
                                         resend_envelope="true")
        await db.docusign_envelopes.update_one(
            {"envelope_id": envelope_id},
            {"$set": {"last_resent_at": now_iso(),
                      "last_resent_by": admin.get("email")}})
        return {"ok": True, "delivery": "email", "resent_to": signer_email}
    except HTTPException:
        raise
    except Exception as e:
        # v52bt — DocuSign returns ENVELOPE_DOES_NOT_EXIST (404) when the
        # envelope was created against a different sandbox account/key than
        # the one currently configured (common after a key rotation or when
        # moving from preview to prod). Surface that as a friendly 410 so
        # the admin UI can show a "Use Reassign" nudge instead of a scary
        # stack-trace toast, and flag the local row as orphaned.
        err_text = ""
        try:
            body = getattr(e, "body", None)
            err_text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body or e)
        except Exception:
            err_text = str(e)
        if ("ENVELOPE_DOES_NOT_EXIST" in err_text or "no rights to it" in err_text
                or "UNKNOWN_ENVELOPE_RECIPIENT" in err_text
                or "not a valid recipient of the specified envelope" in err_text):
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id},
                {"$set": {"status": "orphaned",
                          "orphaned_at": now_iso(),
                          "orphan_reason": "upstream recipient/envelope missing (sandbox key change)"}})
            raise HTTPException(status_code=410,
                detail="This envelope's recipient is no longer valid in the configured DocuSign account (likely a sandbox key change or the recipient was removed upstream). Use Reassign to issue a new envelope to the signer.")
        raise HTTPException(status_code=424, detail=f"DocuSign resend failed — upstream DocuSign error (expired sandbox key in preview; verify DOCUSIGN_* in this environment): {e}")


@router.post("/envelopes/{envelope_id}/reassign")
async def reassign_envelope(envelope_id: str,
                             payload: dict,
                             admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))) -> dict:
    """v51b — admin reassigns an orphaned envelope to a new signer.

    Updates signer_email + signer_name on the envelope so the new vendor
    (or any new signer address) can see it in Signatures and resume signing.
    DocuSign-side signer re-correction is best-effort: we only persist the
    mapping; if the envelope was already sent, the admin should also use
    Resend to issue a fresh signing URL.
    """
    new_email = (payload.get("signer_email") or "").strip().lower()
    new_name  = (payload.get("signer_name") or "").strip()
    reason    = (payload.get("reason") or "").strip()
    if not new_email or "@" not in new_email:
        raise HTTPException(status_code=400, detail="signer_email required")
    env = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not env:
        raise HTTPException(status_code=404, detail="Envelope not found")
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id},
        {"$set": {
            "signer_email": new_email,
            "signer_name": new_name or env.get("signer_name") or new_email,
            "reassigned_at": now_iso(),
            "reassigned_by": admin.get("email"),
            "reassign_reason": reason,
            "archived": False,
        }},
    )
    await audit_log("docusign.envelope.reassign", admin, "docusign_envelope",
                    envelope_id,
                    {"from": env.get("signer_email"), "to": new_email, "reason": reason})
    return {"ok": True, "signer_email": new_email}


@router.post("/envelopes/{envelope_id}/archive")
async def archive_envelope(envelope_id: str,
                            payload: Optional[dict] = None,
                            admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))) -> dict:
    """v51b — soft-archive an orphaned envelope so vendors never see it in
    /mine (list_my_envelopes already excludes archived)."""
    env = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not env:
        raise HTTPException(status_code=404, detail="Envelope not found")
    reason = ((payload or {}).get("reason") or "").strip()
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id},
        {"$set": {"archived": True, "archived_at": now_iso(),
                  "archived_by": admin.get("email"),
                  "archive_reason": reason}},
    )
    await audit_log("docusign.envelope.archive", admin, "docusign_envelope",
                    envelope_id, {"signer": env.get("signer_email"), "reason": reason})
    return {"ok": True}


@router.post("/envelopes/{envelope_id}/unarchive")
async def unarchive_envelope(envelope_id: str,
                              admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))) -> dict:
    env = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not env:
        raise HTTPException(status_code=404, detail="Envelope not found")
    await db.docusign_envelopes.update_one(
        {"envelope_id": envelope_id},
        {"$set": {"archived": False, "unarchived_at": now_iso(),
                  "unarchived_by": admin.get("email")}},
    )
    await audit_log("docusign.envelope.unarchive", admin, "docusign_envelope",
                    envelope_id, {"signer": env.get("signer_email")})
    return {"ok": True}


@router.get("/envelopes/{envelope_id}")
async def get_envelope(envelope_id: str, admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))):
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
            await _apply_live_status(envelope_id, live_status)
            row["status"] = live_status
    except HTTPException:
        raise
    except Exception as e:
        row["live_error"] = str(e)[:200]
    row.pop("_id", None)
    return row


@router.get("/envelopes")
async def list_envelopes(admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting")), limit: int = 100,
                         created_by_email: Optional[str] = None,
                         created_from: Optional[str] = None,
                         created_to: Optional[str] = None):
    # v49y — sync live statuses from DocuSign first so the panel reflects
    # signings even when the Connect webhook is not configured.
    await _sync_recent_statuses()
    # v52w — DB-side created-by / created-range filters (created_at is ISO str).
    q: dict = {}
    if created_by_email:
        q["created_by"] = {"$regex": created_by_email.strip(), "$options": "i"}
    if created_from or created_to:
        rng: dict = {}
        if created_from:
            rng["$gte"] = f"{created_from[:10]}T00:00:00"
        if created_to:
            rng["$lte"] = f"{created_to[:10]}T23:59:59.999"
        q["created_at"] = rng
    cursor = db.docusign_envelopes.find(q).sort("created_at", -1).limit(limit)
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
    # v49y — sync so the vendor sees their completed signature reflected.
    await _sync_recent_statuses()
    # Find bids owned by this vendor (v50z — by vendor_id, not just email:
    # a re-registered vendor reusing an email must NOT inherit envelopes
    # that belonged to the previous registration).
    bid_ids = []
    vid = vendor.get("id")
    # v56o — bug #17: envelopes store bid_id as str(_id); bids have no `id`
    # field, so the old `b.get("id")` match found 0 bids and vendors only saw
    # email-addressed envelopes. Match on str(_id) and include email-only bids
    # that predate vendor_id stamping.
    async for b in db.bids.find({"$or": [{"vendor_id": vid},
                                          {"vendor_email": ve}]}, {"vendor_id": 1, "vendor_email": 1}):
        if b.get("vendor_id") == vid or (not b.get("vendor_id") and b.get("vendor_email") == ve):
            bid_ids.append(str(b["_id"]))
    # signer_email matches only count for envelopes created AFTER this
    # vendor record was created (fresh registration = clean slate).
    vendor_created = vendor.get("created_at") or ""
    query_or = [{"bid_id": {"$in": bid_ids}}]
    if vendor_created:
        query_or.append({"signer_email": ve, "created_at": {"$gte": vendor_created}})
    else:
        query_or.append({"signer_email": ve})
    query = {"$or": query_or, "archived": {"$ne": True}}
    cursor = db.docusign_envelopes.find(query).sort("created_at", -1).limit(50)
    items = []
    # v50n — surface `has_document` so the UI can hide the Download button
    # for envelopes DocuSign has no file for (avoids "no document linked"
    # 404s). Only probed on completed envelopes where Download is relevant.
    try:
        client = _client()
        envelopes_api = ds.EnvelopesApi(client)
    except Exception:
        envelopes_api = None
    async for row in cursor:
        row.pop("_id", None)
        has_doc = bool(row.get("archived_file_key"))
        if not has_doc and row.get("status") == "completed" and envelopes_api is not None:
            try:
                docs = envelopes_api.list_documents(DS_ACCOUNT_ID, row["envelope_id"])
                has_doc = bool(getattr(docs, "envelope_documents", None))
            except Exception:
                has_doc = False
        row["has_document"] = has_doc
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
    from routers.bid_challenges import assert_contract_allowed
    await assert_contract_allowed(bid_id)
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


@router.post("/mine/{envelope_id}/sign")
async def vendor_resume_signing(envelope_id: str, vendor=Depends(current_vendor)):
    """Vendor-facing: regenerate a fresh recipient-view (signing) URL for an
    envelope the calling vendor is the signer of.

    The vendor Signatures page shows envelopes awaiting signature; the
    'Review & sign' button needs a URL it can open. Recipient views expire
    after 5 minutes, so we mint a new one on every click rather than trying
    to persist one.
    """
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    ve = vendor.get("email")
    if row.get("signer_email") != ve:
        # Fall back: allow if the envelope belongs to a bid owned by this vendor
        bid = await db.bids.find_one({"id": row.get("bid_id")}) if row.get("bid_id") else None
        if not bid or bid.get("vendor_email") != ve:
            raise HTTPException(403, "This envelope is not yours to sign")
    if row.get("status") == "completed":
        raise HTTPException(409, "Envelope already signed")
    if row.get("status") in ("voided", "declined"):
        raise HTTPException(409, f"Envelope is {row.get('status')} — ask PMC to resend")
    client = _client()
    return_url = f"{config.FRONTEND_URL}/vendor/signatures?ds_signed=1"
    signer_name = row.get("signer_name") or ve
    signer_email = row.get("signer_email") or ve
    cuid = row.get("client_user_id") or f"pmc:vendor:{envelope_id}:{ve}"
    envelopes = ds.EnvelopesApi(client)

    # v49p — REPAIR PASS 1: email-mode envelopes have no client_user_id on the
    # recipient, so DocuSign refuses to mint an embedded recipient view.
    # Stamp one on if missing.
    try:
        recips = envelopes.list_recipients(DS_ACCOUNT_ID, envelope_id)
        signers = recips.signers or []
        target = next((s for s in signers
                       if (s.email or "").lower() == signer_email.lower()),
                      signers[0] if signers else None)
        if target and not getattr(target, "client_user_id", None):
            target.client_user_id = cuid
            envelopes.update_recipients(DS_ACCOUNT_ID, envelope_id,
                                        recipients=ds.Recipients(signers=signers))
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id}, {"$set": {"client_user_id": cuid}})
    except Exception as e:
        _log.warning("resumeSign: recipient repair failed for %s: %s", envelope_id, e)
        target = None

    # v49p — REPAIR PASS 2: the actual reason the user sees only "Close" —
    # the signer has NO tabs on the envelope (older envelopes were created
    # with a malformed anchor tab that DocuSign silently dropped). Without a
    # SignHere tab the recipient view is read-only. Add tabs if missing.
    if target is not None:
        try:
            tabs = envelopes.list_tabs(DS_ACCOUNT_ID, envelope_id, target.recipient_id)
            has_sign = bool(getattr(tabs, "sign_here_tabs", None))
            if not has_sign:
                envelopes.create_tabs(
                    DS_ACCOUNT_ID, envelope_id, target.recipient_id,
                    ds.Tabs(
                        sign_here_tabs=[ds.SignHere(
                            document_id="1", recipient_id=target.recipient_id,
                            page_number="1", x_position="330", y_position="240",
                            tab_label="Supplier signature")],
                        date_signed_tabs=[ds.DateSigned(
                            document_id="1", recipient_id=target.recipient_id,
                            page_number="1", x_position="330", y_position="285",
                            tab_label="Date signed")],
                    ),
                )
                await audit_log("docusign.tabs_repaired", None, "docusign_envelope",
                                envelope_id, {"vendor": ve})
        except Exception as e:
            _log.warning("resumeSign: tab repair failed for %s: %s", envelope_id, e)

    try:
        signing_url = _recipient_view(client, envelope_id, signer_name, signer_email, cuid, return_url)
    except ApiException as e:
        _log.warning("recipient-view failed for %s: %s", envelope_id, e)
        raise HTTPException(424, "DocuSign couldn't prepare the signing view — upstream DocuSign error (expired sandbox key in preview). Try again or ask PMC to resend.")
    await audit_log("docusign.vendor_resume_sign", None, "docusign_envelope",
                    envelope_id, {"vendor": ve})
    return {"envelope_id": envelope_id, "signing_url": signing_url, "expires_in": 300}
@router.get("/envelopes/{envelope_id}/combined-pdf")
async def download_combined_pdf(envelope_id: str, admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))):
    """Return the fully-signed combined PDF for a completed envelope.

    Only allowed when envelope status is `completed`. Streams the PDF bytes
    from DocuSign's `EnvelopeDocuments.get_document` (documentId="combined").
    """
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    if row.get("status") not in ("completed",):
        raise HTTPException(412, f"Envelope status is '{row.get('status')}' — must be 'completed' before downloading the signed PDF")
    # v51c — serve the PMC-storage copy first when one exists (same behaviour
    # as the vendor endpoints): keeps Print/download working even when the
    # live DocuSign API is unreachable.
    if row.get("archived_file_key"):
        arc = await db.uploads.find_one({"key": row["archived_file_key"]})
        if arc:
            from fastapi.responses import Response as _R
            fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}-signed.pdf"
            return _R(content=base64.b64decode(arc["data_b64"]), media_type="application/pdf",
                      headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    try:
        # v51d — read raw HTTP bytes directly instead of relying on the SDK's
        # tempfile hop. The old `pdf_path = get_document(...)` path returned a
        # NamedTemporaryFile that was auto-deleted before read_bytes() ran on
        # AWS EB → "Could not read the fetched PDF from disk" 500s.
        pdf_bytes = _fetch_document_bytes(envelopes, envelope_id, "combined")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(424, f"DocuSign document fetch failed — upstream DocuSign error (verify DOCUSIGN_* in this environment): {e}")
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
    # v50q — serve the archived copy first when an admin has re-archived the
    # envelope (repair path for envelopes whose DocuSign documents are no
    # longer retrievable from DocuSign).
    if row.get("archived_file_key"):
        arc = await db.uploads.find_one({"key": row["archived_file_key"]})
        if arc:
            from fastapi.responses import Response as _R
            fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}-signed.pdf"
            return _R(content=base64.b64decode(arc["data_b64"]), media_type="application/pdf",
                      headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    try:
        pdf_bytes = _fetch_document_bytes(envelopes, envelope_id, "combined")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(424, f"DocuSign document fetch failed — upstream DocuSign error (verify DOCUSIGN_* in this environment): {e}")
    fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}-signed.pdf"
    from fastapi.responses import Response as _R
    return _R(content=pdf_bytes, media_type="application/pdf",
              headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/mine/envelopes/{envelope_id}/document.pdf")
async def vendor_download_document(envelope_id: str, disposition: str = "inline", vendor=Depends(current_vendor)):
    """Vendor-facing: download/preview the envelope's current document PDF in
    ANY status — the unsigned original while pending, the signed combined PDF
    once completed. disposition=inline opens in a browser tab (Preview/View),
    attachment triggers a download (Download button)."""
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    ve = vendor.get("email")
    if row.get("signer_email") != ve:
        bid = await db.bids.find_one({"id": row.get("bid_id")}) or {}
        if bid.get("vendor_email") != ve:
            raise HTTPException(403, "Not your envelope")
    # v50q — archived copy first for completed envelopes (see archive-pdf).
    if row.get("status") == "completed" and row.get("archived_file_key"):
        arc = await db.uploads.find_one({"key": row["archived_file_key"]})
        if arc:
            from fastapi.responses import Response as _R
            fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}.pdf"
            disp = "attachment" if disposition == "attachment" else "inline"
            return _R(content=base64.b64decode(arc["data_b64"]), media_type="application/pdf",
                      headers={"Content-Disposition": f'{disp}; filename="{fname}"'})
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    doc_id = "combined" if row.get("status") == "completed" else "1"
    try:
        pdf_bytes = _fetch_document_bytes(envelopes, envelope_id, doc_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(424, f"DocuSign document fetch failed — upstream DocuSign error (verify DOCUSIGN_* in this environment): {e}")
    fname = f"{row.get('award_ref') or row.get('bid_ref') or envelope_id}.pdf"
    disp = "attachment" if disposition == "attachment" else "inline"
    from fastapi.responses import Response as _R
    return _R(content=pdf_bytes, media_type="application/pdf",
              headers={"Content-Disposition": f'{disp}; filename="{fname}"'})


# ---------------- Connect webhook ----------------

@router.post("/envelopes/{envelope_id}/archive-pdf")
async def archive_envelope_pdf(envelope_id: str,
                               admin=Depends(require_role("admin", "legal_counsel", "reviewer", "accounting"))):
    """v50q — Admin repair tool. Fetches the combined signed PDF from DocuSign
    and archives it in our own storage (db.uploads). Vendor + admin downloads
    then serve from the archive, so envelopes whose documents DocuSign can no
    longer return are repaired from the console without DocuSign support.

    v51c — was require_role("admin") (bundles the cookie-based CSRF check);
    every other endpoint in this router uses current_admin (Bearer token).
    The cookie check 403'd whenever the csrf_token cookie couldn't flow —
    e.g. the preview iframe or any SameSite=Lax-blocked context."""
    row = await db.docusign_envelopes.find_one({"envelope_id": envelope_id})
    if not row:
        raise HTTPException(404, "Envelope not found")
    if row.get("status") != "completed":
        raise HTTPException(412, "Only completed envelopes can be archived")
    client = _client()
    envelopes = ds.EnvelopesApi(client)
    try:
        pdf_bytes = _fetch_document_bytes(envelopes, envelope_id, "combined")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(424, f"DocuSign document fetch failed — upstream DocuSign error (verify DOCUSIGN_* in this environment): {e}")
    key = f"docusign-archived/{envelope_id}.pdf"
    now = datetime.now(timezone.utc).isoformat()
    await db.uploads.update_one(
        {"key": key},
        {"$set": {"key": key, "content_type": "application/pdf",
                  "size_bytes": len(pdf_bytes),
                  "data_b64": base64.b64encode(pdf_bytes).decode("ascii"),
                  "created_at": now}},
        upsert=True)
    await db.docusign_envelopes.update_one(
        {"_id": row["_id"]},
        {"$set": {"archived_file_key": key, "archived_at": now,
                  "archived_by": admin["id"]}})
    await audit_log("docusign.archive_pdf", admin, "docusign_envelope",
                    envelope_id, {"key": key, "size_bytes": len(pdf_bytes)})
    return {"ok": True, "key": key, "size_bytes": len(pdf_bytes)}


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
            # v49y — route through _apply_live_status so completions fire
            # admin/vendor notifications, audit and bid markers.
            await _apply_live_status(envelope_id, new_status)
            await db.docusign_envelopes.update_one(
                {"envelope_id": envelope_id},
                {"$set": {"webhook_at": datetime.now(timezone.utc).isoformat()}},
            )
    return {"received": True}
