import logging
import httpx
from typing import Optional
import config


def _wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    cta = ""
    if cta_label and cta_url:
        cta = (f'<tr><td style="padding:24px 0"><a href="{cta_url}" '
               f'style="background:#3b6fa0;color:#fff;text-decoration:none;padding:12px 22px;'
               f'font-family:system-ui,sans-serif;font-size:14px">{cta_label}</a></td></tr>')
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#e8edf3;padding:32px 0;font-family:'IBM Plex Sans',system-ui,sans-serif">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #cbd2dd">
      <tr><td style="background:#0f1b3d;color:#fff;padding:20px 28px">
        <div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.6)">PMC Managers Limited</div>
        <div style="font-family:'Libre Baskerville',Georgia,serif;font-size:22px;margin-top:4px">Global Tender Board</div>
      </td></tr>
      <tr><td style="padding:32px 28px">
        <h1 style="font-family:'Libre Baskerville',Georgia,serif;font-size:24px;margin:0 0 12px;color:#0f1b3d">{title}</h1>
        <div style="color:#3f3f46;font-size:14px;line-height:1.6">{body_html}</div>
        {cta}
      </td></tr>
      <tr><td style="border-top:1px solid #cbd2dd;padding:16px 28px;color:#71717a;font-size:11px">
        PMC Managers Limited · Global Tender Board · Automated notification
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_email(to_email: str, subject: str, html: str) -> bool:
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
