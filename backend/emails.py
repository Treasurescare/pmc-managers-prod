import logging
import httpx
from typing import Optional
import config


def _wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    # PMC v50 — Option E email chrome (forest green + brass, cream background).
    # Applied here so every legacy send_email(..., wrap(...)) call-site auto-
    # renders in the new design without touching individual routers.
    cta = ""
    if cta_label and cta_url:
        cta = (
            f'<tr><td style="padding:24px 0">'
            f'<a href="{cta_url}" style="background:#B08E4A;color:#0B1A14;text-decoration:none;'
            f'padding:14px 28px;font-family:\'Public Sans\',Helvetica,Arial,sans-serif;font-size:14px;'
            f'font-weight:600;letter-spacing:0.02em;border-radius:2px;display:inline-block">'
            f'{cta_label}</a></td></tr>'
        )
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F6F0DC;padding:32px 0;font-family:'Public Sans',Helvetica,Arial,sans-serif">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #B08E4A22">
      <tr><td style="background:#0B1A14;color:#FFFFFF;padding:22px 32px">
        <img src="{config.FRONTEND_URL}/pmc-logo-mark.png" width="44" height="44" alt="PMC Managers" style="display:block;border-radius:8px;margin-bottom:10px">
        <div style="font:11px/16px 'Public Sans',Helvetica,Arial,sans-serif;color:#B08E4A;letter-spacing:0.22em;text-transform:uppercase">PMC Managers Limited</div>
        <div style="font:400 22px/28px Georgia,'Cormorant Garamond',serif;color:#FFFFFF;margin-top:6px">Global Tender Board</div>
      </td></tr>
      <tr><td style="padding:36px 32px 28px">
        <h1 style="margin:0 0 12px;font:400 26px/32px Georgia,'Cormorant Garamond',serif;color:#0F3B2E">{title}</h1>
        <div style="color:#1C1C1B;font:15px/24px 'Public Sans',Helvetica,Arial,sans-serif;margin-top:14px">{body_html}</div>
        {cta}
      </td></tr>
      <tr><td style="border-top:1px solid #B08E4A44;padding:18px 32px;background:#FAFAF7;color:#5A5A57;font:11px/16px 'Public Sans',Helvetica,Arial,sans-serif">
        Sent by PMC Managers Limited &middot; Global Tender Board &middot; This message is time-stamped and hash-chained to the audit ledger.
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_email(to_email: str, subject: str, html: str,
                     attachments: Optional[list] = None,
                     cc: Optional[list] = None) -> bool:
    # Direct Resend path — sends from the verified pmcmanagers.com domain so
    # recipients see PMC's own address, never a third-party relay domain.
    # v52bo — optional `attachments` list ({filename, content_b64, content_type})
    # is forwarded to Resend so corrigendum PDFs reach bidders inline.
    # v56s — optional `cc` list (escrow signatory emails) carried alongside the
    # base recipient so every escrow mail CCs all registered signatories.
    cc_clean = sorted({(e or "").strip().lower() for e in (cc or [])
                       if (e or "").strip() and (e or "").strip().lower() != (to_email or "").strip().lower()})
    if config.RESEND_API_KEY:
        payload = {
            "from": f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM_ADDRESS}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        if cc_clean:
            payload["cc"] = cc_clean
        if config.EMAIL_REPLY_TO:
            payload["reply_to"] = config.EMAIL_REPLY_TO
        if attachments:
            payload["attachments"] = [
                {"filename": a["filename"], "content": a["content_b64"]}
                for a in attachments if a.get("filename") and a.get("content_b64")
            ]
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post("https://api.resend.com/emails",
                                 headers={"Authorization": f"Bearer {config.RESEND_API_KEY}",
                                          "Content-Type": "application/json"},
                                 json=payload)
            if r.status_code >= 400:
                logging.error(f"Resend failed {r.status_code}: {r.text}")
                return False
            return True
        except Exception as e:
            logging.exception(f"Resend exception: {e}")
            return False

    # Legacy relay fallback (sender domain is managed by the relay provider).
    if not config.EMAIL_KEY:
        logging.warning("EMAIL_API_KEY not set — email skipped")
        return False
    payload = {"to": [to_email], "subject": subject, "html": html, "from_name": config.EMAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(f"{config.EMAIL_BASE_URL}/api/v1/email/send",
                             headers={"X-Email-Key": config.EMAIL_KEY}, json=payload)
        if r.status_code >= 400:
            logging.error(f"Email failed {r.status_code}: {r.text}")
            return False
        return True
    except Exception as e:
        logging.exception(f"Email exception: {e}")
        return False


def wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    return _wrap(title, body_html, cta_label, cta_url)
