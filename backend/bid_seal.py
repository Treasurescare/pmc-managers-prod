"""Sealed-bid envelopes: encryption at rest + who may see what before committee opening."""
import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

SEALED_FIELDS_TECH = ("technical_notes",)
SEALED_FIELDS_COMM = ("price_amount", "commercial_notes")
EMD_CONFIRMED = {"escrow_accepted", "admin_flagged", "certifier_cleared", "legal_cleared",
                 "accounting_cleared", "committee_review", "awarded"}


def _fernet() -> Fernet:
    secret = os.environ.get("BID_SEAL_KEY", "").strip()
    if len(secret) < 20:
        raise HTTPException(status_code=503, detail="Bid sealing key is not configured on the server (BID_SEAL_KEY, 20+ characters)")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def enc_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def dec_bytes(data: bytes) -> bytes:
    try:
        return _fernet().decrypt(data)
    except InvalidToken:
        raise HTTPException(status_code=500, detail="Sealed file could not be decrypted")


def enc_text(v) -> Optional[str]:
    return None if v is None else _fernet().encrypt(str(v).encode()).decode()


def dec_text(v: Optional[str]) -> Optional[str]:
    return None if not v else dec_bytes(v.encode()).decode()


def seal_fields(doc: dict, src: dict) -> dict:
    """Move plaintext tech/commercial fields from `src` into encrypted `sealed` sub-doc on `doc`."""
    sealed = dict(doc.get("sealed") or {})
    for f in SEALED_FIELDS_TECH + SEALED_FIELDS_COMM:
        if f in src and src[f] is not None:
            sealed[f] = enc_text(src[f])
            doc[f] = None
    doc["sealed"] = sealed
    doc["seal_v"] = 1
    return doc


def unsealed_view(b: dict) -> dict:
    """Plaintext copy for the bid's own vendor."""
    if not b.get("seal_v"):
        return b
    b = dict(b)
    for f, tok in (b.get("sealed") or {}).items():
        if b.get(f) is None and tok:
            val = dec_text(tok)
            b[f] = float(val) if f == "price_amount" else val
    b.pop("sealed", None)
    return b


def _parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.strptime(str(s)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def opening_at(notice: dict) -> Optional[datetime]:
    return _parse(notice.get("bid_opening_date")) or _parse(notice.get("submission_deadline"))


def is_sealed_bid(b: dict) -> bool:
    return bool(b.get("seal_v")) and not b.get("auction_id")


def stage_open(notice: dict, stage: str) -> bool:
    return bool((notice or {}).get(f"{stage}_opened_at"))


def bid_stage_visible(b: dict, notice: dict, stage: str) -> bool:
    """Technical/commercial content of this bid may be shown to staff."""
    if not is_sealed_bid(b):
        return True
    if stage == "technical":
        return bool(b.get("technical_unsealed_at"))
    return bool(b.get("commercial_unsealed_at"))


def redact_for_staff(b: dict, notice: dict) -> dict:
    if not is_sealed_bid(b):
        return b
    b = dict(b)
    b.pop("sealed", None)
    tech, comm = bid_stage_visible(b, notice, "technical"), bid_stage_visible(b, notice, "commercial")
    docs = b.get("documents") or []
    if not tech:
        b["documents"] = []
        b["technical_notes"] = None
        b["sealed_documents_count"] = len(docs)
    elif not comm:
        b["documents"] = [d for d in docs if d.get("kind") != "commercial"]
    if not comm:
        b["price_amount"] = None
        b["commercial_notes"] = None
        b["commercial_redacted"] = True
    b["envelope_state"] = "commercial_open" if comm else ("technical_open" if tech else "sealed")
    return b
