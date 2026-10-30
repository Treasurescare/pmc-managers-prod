import asyncio
import re
from html import escape as h
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from audit import audit_log
from db import db
from models.base import now_iso
from pdf_brand import brand_html
from routers.vendor_auth import current_vendor
from security import require_csrf, require_role

router = APIRouter(tags=["site"])

DEFAULT_SOCIAL = {
    "linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7521796802216611840/",
    "facebook": "https://www.facebook.com/profile.php?id=61596254811635",
    "instagram": "",
    "whatsapp": "",
}
_URL = re.compile(r"^https://[^\s<>\"']+$")


class SocialIn(BaseModel):
    linkedin: Optional[str] = ""
    facebook: Optional[str] = ""
    instagram: Optional[str] = ""
    whatsapp: Optional[str] = ""


async def _social() -> dict:
    doc = await db.site_settings.find_one({"_id": "social"}) or {}
    return {k: doc.get(k, v) for k, v in DEFAULT_SOCIAL.items()}


@router.get("/api/v1/site/social")
async def public_social():
    return await _social()


@router.put("/api/v1/marketing/site-social", dependencies=[Depends(require_csrf)])
async def save_social(body: SocialIn, admin=Depends(require_role("admin"))):
    data = {k: (getattr(body, k) or "").strip() for k in DEFAULT_SOCIAL}
    if data["whatsapp"]:
        digits = re.sub(r"[\s+()-]", "", data["whatsapp"])
        if not re.fullmatch(r"\d{8,15}", digits):
            raise HTTPException(status_code=422, detail="WhatsApp number: country code + number, digits only, e.g. 447700900123")
        data["whatsapp"] = digits
    for k, v in data.items():
        if k != "whatsapp" and v and not _URL.match(v):
            raise HTTPException(status_code=422, detail=f"{k.title()} link must start with https://")
    await db.site_settings.update_one({"_id": "social"}, {"$set": {**data, "updated_at": now_iso()}}, upsert=True)
    await audit_log("site.social_links_updated", admin, "site_settings", "social", data)
    return data


PURPOSE = {"tender_start": "Tender start fee", "tender_fee": "Tender fee", "doc_fee": "Tender document fee",
           "data_intel": "Data Intel", "category_fee": "Additional category"}


def render_receipt_pdf(rec: dict, vendor: dict) -> bytes:
    from weasyprint import HTML
    cur = h(rec.get("currency") or "")
    rows = "".join(f"<tr><td>{h(str(x.get('name', '')))}</td><td class='r'>{cur} {float(x.get('amount') or 0):,.2f}</td></tr>"
                   for x in rec.get("lines") or [])
    extra = "".join(f"<div><b>{lbl}</b>{h(str(rec[k]))}</div>" for k, lbl in
                    (("tender_name", "Tender"), ("category", "Category")) if rec.get(k))
    html = f"""<html><head><style>
      @page {{ size:A4; margin:18mm; }}
      body {{ font-family:Helvetica,Arial,sans-serif; font-size:11px; color:#14261F; }}
      h1 {{ font-size:22px; color:#0F3B2E; margin:6px 0 2px; }}
      .meta {{ display:flex; justify-content:space-between; gap:20px; margin:16px 0 22px; }}
      .meta b {{ display:block; font-size:9px; letter-spacing:1px; text-transform:uppercase; color:#5B6B63; }}
      .meta div div {{ margin-bottom:8px; }}
      table {{ width:100%; border-collapse:collapse; }}
      th, td {{ padding:8px 10px; text-align:left; border-bottom:1px solid rgba(15,59,46,.12); }}
      th {{ font-size:9px; letter-spacing:1px; text-transform:uppercase; color:#5B6B63; }}
      .r {{ text-align:right; }}
      .tot td {{ font-weight:700; font-size:13px; border-top:2px solid #0F3B2E; }}
      .paid {{ display:inline-block; padding:3px 10px; background:#DEEEE1; color:#0F3B2E; font-weight:700; letter-spacing:1px; font-size:10px; }}
      .foot {{ margin-top:40px; font-size:9px; color:#7B8B83; }}
    </style></head><body>
      <h1>Payment receipt</h1><span class="paid">PAID</span>
      <div class="meta">
        <div><div><b>Receipt no.</b>{h(rec.get('receipt_no', ''))}</div><div><b>Date paid</b>{h(str(rec.get('paid_at', ''))[:10])}</div>
             <div><b>For</b>{h(PURPOSE.get(rec.get('purpose'), str(rec.get('purpose', '')).replace('_', ' ').title()))}</div>{extra}</div>
        <div><div><b>Received from</b>{h(vendor.get('company_name') or 'Supplier')}</div>
             <div><b>Supplier ref.</b>{h(vendor.get('vendor_ref') or '—')}</div><div><b>Email</b>{h(vendor.get('email') or '—')}</div></div>
      </div>
      <table><thead><tr><th>Item</th><th class="r">Amount</th></tr></thead>
        <tbody>{rows}<tr class="tot"><td>Total paid</td><td class="r">{cur} {float(rec.get('total') or 0):,.2f}</td></tr></tbody></table>
      <div class="foot">Payment reference: {h(str(rec.get('session_id', '')))}<br/>
        Issued by PMC Managers Limited · Global Tender Board · pmcmanagers.com</div>
    </body></html>"""
    return HTML(string=brand_html(html)).write_pdf()


async def _vendor_doc(vendor_id: str) -> dict:
    try:
        return await db.vendors.find_one({"_id": ObjectId(vendor_id)}) or {}
    except Exception:
        return {}


@router.get("/api/v1/vendor-tenders/receipts/{receipt_no}.pdf")
async def vendor_receipt_pdf(receipt_no: str, vendor=Depends(current_vendor)):
    rec = await db.fee_receipts.find_one({"receipt_no": receipt_no, "vendor_id": vendor["id"]})
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    pdf = await asyncio.to_thread(render_receipt_pdf, rec, await _vendor_doc(vendor["id"]))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{receipt_no}.pdf"'})
