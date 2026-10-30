"""Wave 39 — Post-Award document generator.

The moment a Bid transitions to `awarded`, this module drafts three PDFs
and stores them under `db.award_documents`:

  1. Purchase Order      — auto-numbered `PMC-PO-YYYY-#####`
  2. Service Level Agreement (SLA)
  3. Contract / Letter of Acceptance

All three are WeasyPrint-rendered A4 PDFs, watermarked, versioned, and
signed off by the awarding admin. The awarded vendor and any admin can
download them from their dashboards.
"""
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from bson import ObjectId
import base64
import html as _html

from db import db, next_sequence
from pdf_brand import brand_html
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/awards", tags=["awards"])


# ---------- Rendering primitives ---------------------------------------

def _fmt_money(amount: Optional[float], currency: str = "USD") -> str:
    if amount is None:
        return "—"
    return f"{currency} {amount:,.2f}"


def _base_style() -> str:
    return """<style>
      @page { size: A4; margin: 22mm 18mm 22mm 18mm;
              @top-right { content: "PMC Managers Ltd · Confidential"; font-size: 9pt; color: #64748b; }
              @bottom-left { content: "Page " counter(page) " / " counter(pages); font-size: 9pt; color: #64748b; }
              @bottom-right { content: "Rendered " string(gendate); font-size: 9pt; color: #64748b; } }
      body { font-family: 'Calibri', 'Helvetica', sans-serif; color: #0f172a; font-size: 10.5pt; line-height: 1.4; }
      .doc-kicker { font-size: 9pt; letter-spacing: 3px; text-transform: uppercase; color: #64748b; }
      h1 { font-size: 22pt; margin: 4pt 0 18pt; color: #0b1f3a; font-weight: 700; }
      h2 { font-size: 12pt; margin: 20pt 0 8pt; color: #0b1f3a; border-bottom: 1pt solid #0b1f3a; padding-bottom: 3pt; }
      h3 { font-size: 11pt; margin: 14pt 0 6pt; color: #0b1f3a; }
      table.meta { width: 100%; border-collapse: collapse; margin-top: 10pt; }
      table.meta td { padding: 6pt 8pt; border: 0.5pt solid #cbd5e1; vertical-align: top; }
      table.meta td.k { background: #f1f5f9; width: 32%; font-weight: 600; color: #334155; }
      table.li { width: 100%; border-collapse: collapse; margin-top: 8pt; }
      table.li th { background: #0b1f3a; color: #ffffff; padding: 7pt; text-align: left; font-size: 10pt; }
      table.li td { padding: 7pt; border: 0.5pt solid #cbd5e1; }
      table.li tr.total td { background: #f1f5f9; font-weight: 700; }
      .sig-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24pt; margin-top: 40pt; }
      .sig-box { border-top: 1pt solid #0b1f3a; padding-top: 6pt; font-size: 9.5pt; }
      .sig-box .role { text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-size: 8pt; }
      .stamp { position: fixed; top: 40mm; right: 20mm; transform: rotate(-18deg);
               border: 2pt solid #b91c1c; color: #b91c1c; padding: 6pt 14pt; font-weight: 700;
               font-size: 22pt; letter-spacing: 4px; opacity: 0.18; }
      .clause { margin: 6pt 0; }
      .clause b { display: inline-block; min-width: 32pt; }
      p.small { font-size: 9pt; color: #475569; }
    </style>"""


def _render_po_html(bid: dict, notice: dict, po_no: str, awarded_at: str, award_ref: str) -> str:
    price = _fmt_money(bid.get("price_amount"), bid.get("price_currency") or "USD")
    supplier = bid.get("company_name") or bid.get("vendor_email") or "—"
    return f"""<html><head>{_base_style()}</head><body>
      <div class='doc-kicker'>Purchase Order</div>
      <h1>Purchase Order — {po_no}</h1>
      <table class='meta'>
        <tr><td class='k'>PO Number</td><td>{po_no}</td></tr>
        <tr><td class='k'>Award Reference</td><td>{award_ref}</td></tr>
        <tr><td class='k'>Issue Date</td><td>{awarded_at[:10]}</td></tr>
        <tr><td class='k'>Buyer</td><td>PMC Managers Limited</td></tr>
        <tr><td class='k'>Supplier</td><td>{_html.escape(str(supplier))}</td></tr>
        <tr><td class='k'>Reference Tender</td><td>{notice.get('notice_ref','—')} — {_html.escape(notice.get('title',''))}</td></tr>
        <tr><td class='k'>Delivery Country</td><td>{notice.get('delivery_country','—')}</td></tr>
      </table>

      <h2>1 · Scope of Supply</h2>
      <p>{_html.escape(notice.get('description') or 'As per the awarded bid and tender documents.')}</p>

      <h2>2 · Commercial Summary</h2>
      <table class='li'>
        <thead><tr><th>Item</th><th style='width:18%; text-align:right;'>Amount</th></tr></thead>
        <tbody>
          <tr><td>Awarded contract value (per bid <b>{bid.get('bid_ref','')}</b>)</td>
              <td style='text-align:right;'>{price}</td></tr>
          <tr class='total'><td>Total Purchase Order Value</td>
              <td style='text-align:right;'>{price}</td></tr>
        </tbody>
      </table>

      <h2>3 · Key Terms</h2>
      <div class='clause'><b>3.1</b> Payment terms follow the tender documents and the accompanying SLA.</div>
      <div class='clause'><b>3.2</b> Delivery, taxes, warranties, and performance security are governed by the awarded bid.</div>
      <div class='clause'><b>3.3</b> Any variation must be approved in writing by the buyer's authorised signatory.</div>

      <div class='sig-grid'>
        <div class='sig-box'><div class='role'>For &amp; on behalf of the Buyer</div>
          PMC Managers Limited<br/>Authorised Signatory<br/>Date: {awarded_at[:10]}</div>
        <div class='sig-box'><div class='role'>For &amp; on behalf of the Supplier</div>
          <span style="color:#ffffff;font-size:1pt">/sig_here/</span><br/>{_html.escape(str(supplier))}<br/>Authorised Signatory<br/>Date: <span style="color:#ffffff;font-size:1pt">/ds_here/</span>______________</div>
      </div>
      <p class='small'>System-generated document — this Purchase Order is issued from the PMC Managers e-Tender platform.</p>
    </body></html>"""


def _render_sla_html(bid: dict, notice: dict, awarded_at: str, award_ref: str) -> str:
    supplier = bid.get("company_name") or bid.get("vendor_email") or "—"
    return f"""<html><head>{_base_style()}</head><body>
      <div class='doc-kicker'>Service Level Agreement</div>
      <h1>Service Level Agreement</h1>
      <table class='meta'>
        <tr><td class='k'>Award Reference</td><td>{award_ref}</td></tr>
        <tr><td class='k'>Effective Date</td><td>{awarded_at[:10]}</td></tr>
        <tr><td class='k'>Buyer</td><td>PMC Managers Limited</td></tr>
        <tr><td class='k'>Supplier</td><td>{_html.escape(str(supplier))}</td></tr>
        <tr><td class='k'>Reference Tender</td><td>{notice.get('notice_ref','—')}</td></tr>
      </table>

      <h2>1 · Service Objectives</h2>
      <p>The Supplier shall deliver the goods and/or services described in the tender
         documents at the quality, quantity, and schedule stated in its awarded bid.</p>

      <h2>2 · Service Level Targets</h2>
      <table class='li'>
        <thead><tr><th>Metric</th><th>Target</th><th>Measurement</th></tr></thead>
        <tbody>
          <tr><td>On-time delivery</td><td>&ge; 98% of milestones met</td><td>Monthly review</td></tr>
          <tr><td>Defect / rework rate</td><td>&lt; 2% of delivered units</td><td>Per acceptance test</td></tr>
          <tr><td>Response to incidents (High)</td><td>Within 4 business hours</td><td>Helpdesk log</td></tr>
          <tr><td>Response to incidents (Medium)</td><td>Within 1 business day</td><td>Helpdesk log</td></tr>
          <tr><td>Uptime (where applicable)</td><td>99.5% monthly</td><td>Platform report</td></tr>
        </tbody>
      </table>

      <h2>3 · Reporting &amp; Reviews</h2>
      <div class='clause'><b>3.1</b> Supplier submits monthly performance reports within 5 business days of month-end.</div>
      <div class='clause'><b>3.2</b> Quarterly performance review with the Buyer's designated officer.</div>

      <h2>4 · Remedies</h2>
      <div class='clause'><b>4.1</b> Sustained breach of SLA targets triggers a service credit as defined in the tender documents.</div>
      <div class='clause'><b>4.2</b> Persistent under-performance may lead to termination for cause under the Contract.</div>

      <div class='sig-grid'>
        <div class='sig-box'><div class='role'>Buyer — PMC Managers Limited</div>Authorised Signatory<br/>Date: {awarded_at[:10]}</div>
        <div class='sig-box'><div class='role'>Supplier</div><span style="color:#ffffff;font-size:1pt">/sig_here/</span><br/>{_html.escape(str(supplier))}<br/>Authorised Signatory<br/>Date: <span style="color:#ffffff;font-size:1pt">/ds_here/</span>______________</div>
      </div>
      <p class='small'>System-generated — governed by the master tender documents and applicable local law.</p>
    </body></html>"""


def _render_contract_html(bid: dict, notice: dict, awarded_at: str, award_ref: str) -> str:
    price = _fmt_money(bid.get("price_amount"), bid.get("price_currency") or "USD")
    supplier = bid.get("company_name") or bid.get("vendor_email") or "—"
    return f"""<html><head>{_base_style()}</head><body>
      <div class='stamp'>AWARDED</div>
      <div class='doc-kicker'>Contract Award — Letter of Acceptance</div>
      <h1>Contract Award &amp; Letter of Acceptance</h1>
      <table class='meta'>
        <tr><td class='k'>Award Reference</td><td>{award_ref}</td></tr>
        <tr><td class='k'>Date of Award</td><td>{awarded_at[:10]}</td></tr>
        <tr><td class='k'>Awarding Authority</td><td>PMC Managers Limited</td></tr>
        <tr><td class='k'>Awarded To</td><td>{_html.escape(str(supplier))}</td></tr>
        <tr><td class='k'>Reference Tender</td><td>{notice.get('notice_ref','—')}</td></tr>
        <tr><td class='k'>Awarded Bid Reference</td><td>{bid.get('bid_ref','—')}</td></tr>
        <tr><td class='k'>Contract Value</td><td>{price}</td></tr>
      </table>

      <h2>1 · Acceptance</h2>
      <p>Following the evaluation of bids received in response to tender
         <b>{notice.get('notice_ref','')} — {_html.escape(notice.get('title',''))}</b>,
         PMC Managers Limited is pleased to inform <b>{_html.escape(str(supplier))}</b>
         that its bid dated {bid.get('created_at','')[:10]} has been accepted for the sum of
         <b>{price}</b> (inclusive of all applicable duties and taxes unless otherwise stated).</p>

      <h2>2 · Contract Documents</h2>
      <div class='clause'><b>2.1</b> The Contract comprises: this Letter of Acceptance, the Purchase Order, the
         Service Level Agreement, the awarded bid, the tender documents (including any published corrigenda),
         and the General Conditions of Contract.</div>
      <div class='clause'><b>2.2</b> In the event of conflict, this Letter of Acceptance prevails.</div>

      <h2>3 · Performance Security</h2>
      <div class='clause'><b>3.1</b> The Supplier shall furnish the required Performance Security within 14 days of this letter.</div>
      <div class='clause'><b>3.2</b> The Earnest Money Deposit held in joint escrow shall be released or converted as agreed.</div>

      <h2>4 · Signature &amp; Effect</h2>
      <p>Please counter-sign the enclosed duplicate of this letter and return it to PMC Managers Limited
         within 7 (seven) days of receipt to formally conclude the Contract.</p>

      <div class='sig-grid'>
        <div class='sig-box'><div class='role'>PMC Managers Limited</div>Authorised Signatory<br/>Date: {awarded_at[:10]}</div>
        <div class='sig-box'><div class='role'>Accepted by Supplier</div><span style="color:#ffffff;font-size:1pt">/sig_here/</span><br/>{_html.escape(str(supplier))}<br/>Authorised Signatory<br/>Date: <span style="color:#ffffff;font-size:1pt">/ds_here/</span>______________</div>
      </div>
      <p class='small'>System-generated Letter of Acceptance — retain a signed copy for your records.</p>
    </body></html>"""


def _pdf_bytes(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=brand_html(html)).write_pdf()


# ---------- Public generator (called from bids.decide_bid on award) ----

async def generate_award_documents(bid_id: str, awarded_by_email: str) -> dict:
    """Idempotent — draws PO/SLA/Contract PDFs and stores them under
    `award_documents`. Returns the metadata dict."""
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise ValueError("Bid not found")
    notice = await db.notices.find_one({"notice_ref": bid.get("notice_ref")}) or {}

    seq = await next_sequence("po_seq")
    year = datetime.now(timezone.utc).year
    po_no = f"PMC-PO-{year}-{seq:05d}"
    award_ref = f"PMC-AWD-{year}-{seq:05d}"
    awarded_at = now_iso()

    docs = {
        "po":       _render_po_html(bid, notice, po_no, awarded_at, award_ref),
        "sla":      _render_sla_html(bid, notice, awarded_at, award_ref),
        "contract": _render_contract_html(bid, notice, awarded_at, award_ref),
    }
    stored = []
    for kind, html in docs.items():
        try:
            pdf = _pdf_bytes(html)
        except Exception as e:
            stored.append({"kind": kind, "ok": False, "error": str(e)})
            continue
        row = {
            "bid_id": bid_id,
            "bid_ref": bid.get("bid_ref"),
            "notice_ref": bid.get("notice_ref"),
            "vendor_id": bid.get("vendor_id"),
            "kind": kind,
            "po_no": po_no if kind == "po" else None,
            "award_ref": award_ref,
            "awarded_at": awarded_at,
            "awarded_by": awarded_by_email,
            "size_bytes": len(pdf),
            "pdf_b64": base64.b64encode(pdf).decode("ascii"),
            "created_at": now_iso(),
        }
        await db.award_documents.update_one(
            {"bid_id": bid_id, "kind": kind},
            {"$set": row},
            upsert=True,
        )
        stored.append({"kind": kind, "ok": True, "size_bytes": len(pdf)})

    # Stamp the bid so the award is visible from the bid record itself.
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"awarded_at": awarded_at, "awarded_by": awarded_by_email,
                  "award_ref": award_ref, "po_no": po_no}},
    )
    return {"ok": True, "award_ref": award_ref, "po_no": po_no,
            "documents": stored, "awarded_at": awarded_at}


# ---------- API endpoints ---------------------------------------------

def _meta_out(d: dict) -> dict:
    o = BaseDocument.out(d)
    o.pop("pdf_b64", None)  # never leak bytes on list
    return o


@router.get("/bid/{bid_id}")
async def list_award_docs_admin(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting", "auditor")),
) -> dict:
    cursor = db.award_documents.find({"bid_id": bid_id})
    items = [_meta_out(d) async for d in cursor]
    return {"bid_id": bid_id, "items": items, "total": len(items)}


@router.get("/bid/{bid_id}/mine")
async def list_award_docs_vendor(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    """Awarded vendor can also fetch their own award documents."""
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid or bid.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Bid not found")
    cursor = db.award_documents.find({"bid_id": bid_id})
    items = [_meta_out(d) async for d in cursor]
    return {"bid_id": bid_id, "items": items, "total": len(items)}


async def _stream_pdf(bid_id: str, kind: str) -> Response:
    d = await db.award_documents.find_one({"bid_id": bid_id, "kind": kind})
    if not d:
        raise HTTPException(status_code=404, detail=f"Award document '{kind}' not found")
    pdf = base64.b64decode(d["pdf_b64"])
    fname = f"{d.get('award_ref','award')}-{kind}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/bid/{bid_id}/pdf/{kind}")
async def download_award_doc_admin(
    bid_id: str, kind: str,
    admin=Depends(require_role("admin", "committee_member", "accounting", "auditor")),
) -> Response:
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(status_code=400, detail="Unknown document kind")
    return await _stream_pdf(bid_id, kind)


@router.get("/bid/{bid_id}/pdf/{kind}/mine")
async def download_award_doc_vendor(bid_id: str, kind: str, vendor=Depends(current_vendor)) -> Response:
    if kind not in ("po", "sla", "contract"):
        raise HTTPException(status_code=400, detail="Unknown document kind")
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid or bid.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Bid not found")
    return await _stream_pdf(bid_id, kind)


# ---------- v51ba: Award record summary + printable views ------------

def _signoff_role_map() -> dict:
    """Which workflow_history role codes map to each signoff slot.

    Order defines display order on the Award Record panel.
    """
    return {
        "escrow_agent":    {"label": "Escrow sign-off",   "roles": ["escrow_agent"]},
        "admin":           {"label": "PMC admin sign-off", "roles": ["admin"]},
        "certifier":       {"label": "Site certifier",    "roles": ["certifier"]},
        "legal_counsel":   {"label": "Legal sign-off",    "roles": ["legal_counsel"]},
        "accounting":      {"label": "Accounts sign-off", "roles": ["accounting"]},
        "committee_member":{"label": "Committee award",   "roles": ["committee_member"]},
    }


def _collect_signoffs(bid: dict) -> list:
    """Walk workflow_history and surface the final `accept` entry per role
    together with any explicit cleared_at stamps the bid record carries.
    """
    history = bid.get("workflow_history") or []
    accepted_by_role: dict = {}
    for entry in history:
        if (entry.get("action") or "").lower() != "accept":
            continue
        role = entry.get("role")
        if not role:
            continue
        # Keep the LAST accept — some rules allow re-signing.
        accepted_by_role[role] = entry

    out = []
    for slot_key, meta in _signoff_role_map().items():
        entry = None
        for r in meta["roles"]:
            if r in accepted_by_role:
                entry = accepted_by_role[r]
                break
        out.append({
            "key": slot_key,
            "label": meta["label"],
            "signed": bool(entry),
            "by": (entry or {}).get("by"),
            "at": (entry or {}).get("at"),
            "notes": (entry or {}).get("notes"),
            "to_status": (entry or {}).get("to_status"),
        })
    return out


async def _collect_docusign_envelopes(bid_id: str) -> list:
    rows = []
    async for env in db.docusign_envelopes.find({"bid_id": bid_id}).sort("created_at", -1):
        rows.append({
            "envelope_id": env.get("envelope_id"),
            "kind":        env.get("kind"),
            "sub_kind":    env.get("sub_kind"),
            "status":      env.get("status"),
            "signer_name": env.get("signer_name"),
            "signer_email":env.get("signer_email"),
            "created_at":  env.get("created_at"),
            "completed_at":env.get("webhook_at") or env.get("updated_at"),
            "archived":    bool(env.get("archived")),
        })
    return rows


async def _collect_escrow_transactions(bid_ref: str) -> list:
    rows = []
    async for tx in db.escrow_transactions.find({"bid_ref": bid_ref}).sort("created_at", -1):
        sigs = tx.get("signatures") or {}
        pmc = sigs.get("pmc") or {}
        esc = sigs.get("escrow_institution") or {}
        rows.append({
            "transaction_id": str(tx.get("_id")) if tx.get("_id") else None,
            "amount":   tx.get("amount"),
            "currency": tx.get("currency"),
            "status":   tx.get("status"),
            "released_at":  tx.get("released_at"),
            "released_to":  tx.get("released_to"),
            "pmc_officer":  (pmc.get("officer_email") or pmc.get("email")),
            "pmc_signed_at": pmc.get("signed_at"),
            "escrow_officer": (esc.get("officer_email") or esc.get("email")),
            "escrow_signed_at": esc.get("signed_at"),
        })
    return rows


async def _build_award_summary(bid: dict) -> dict:
    """Assemble a single JSON payload the Award Record panel needs."""
    bid_id = str(bid.get("_id") or bid.get("id") or "")
    notice = await db.notices.find_one({"notice_ref": bid.get("notice_ref")}) or {}

    award_docs = [
        _meta_out(d) async for d in db.award_documents.find({"bid_id": bid_id})
    ]
    envelopes  = await _collect_docusign_envelopes(bid_id)
    escrow_tx  = await _collect_escrow_transactions(bid.get("bid_ref") or "")

    return {
        "is_awarded": bid.get("status") == "awarded",
        "award_ref":  bid.get("award_ref"),
        "po_no":      bid.get("po_no"),
        "awarded_at": bid.get("awarded_at"),
        "awarded_by": bid.get("awarded_by"),
        "tender": {
            "notice_ref":            notice.get("notice_ref") or bid.get("notice_ref"),
            "title":                 notice.get("title"),
            "description":           notice.get("description"),
            "category":              notice.get("category"),
            "delivery_country":      notice.get("delivery_country"),
            "budget_currency":       notice.get("budget_currency"),
            "budget_amount":         notice.get("budget_amount"),
            "published_at":          notice.get("published_at"),
            "submission_deadline":   notice.get("submission_deadline"),
            "technical_locked_at":   notice.get("technical_locked_at"),
        },
        "winner": {
            "company_name":  bid.get("company_name"),
            "vendor_ref":    bid.get("vendor_ref"),
            "vendor_email":  bid.get("vendor_email"),
            "price_amount":  bid.get("price_amount"),
            "price_currency": bid.get("price_currency"),
            "bid_ref":       bid.get("bid_ref"),
            "submitted_at":  bid.get("submitted_at") or bid.get("created_at"),
            "technical_cleared_at":   bid.get("technical_cleared_at"),
            "technical_cleared_by":   bid.get("technical_cleared_by"),
            "financial_opened_at":    bid.get("financial_opened_at"),
            "financial_opened_by":    bid.get("financial_opened_by"),
        },
        "signoffs":  _collect_signoffs(bid),
        "envelopes": envelopes,
        "escrow":    escrow_tx,
        "documents": award_docs,
    }


@router.get("/bid/{bid_id}/summary")
async def get_award_summary(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting",
                                "auditor", "reviewer", "legal_counsel",
                                "escrow_agent", "certifier")),
) -> dict:
    """v51ba — Admin / staff lifecycle summary for a bid's award record."""
    try:
        oid = ObjectId(bid_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed bid id")
    bid = await db.bids.find_one({"_id": oid})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return await _build_award_summary(bid)


# ---------- Printable Award Letter + Contract HTML (admin only) --------

def _print_style() -> str:
    return """<style>
      :root { color-scheme: light; }
      * { box-sizing: border-box; }
      html, body { margin: 0; padding: 0; background: #F8FAFC; color: #0F172A;
                    font-family: 'Public Sans', 'Segoe UI', system-ui, sans-serif; }
      .page { max-width: 820px; margin: 32px auto; padding: 48px;
              background: #ffffff; border: 1px solid #E2E8F0;
              box-shadow: 0 10px 30px rgba(15,27,61,0.08); }
      .toolbar { max-width: 820px; margin: 20px auto 0; display: flex; gap: 10px;
                 justify-content: flex-end; }
      .toolbar button { font: inherit; padding: 10px 18px; border: 1px solid #0F3B2E;
                        background: #0F3B2E; color: #F3EFE4; cursor: pointer;
                        text-transform: uppercase; letter-spacing: 0.15em;
                        font-size: 11px; font-weight: 600; }
      .toolbar button.ghost { background: #FFFFFF; color: #0F3B2E; }
      .kicker { text-transform: uppercase; letter-spacing: 0.22em;
                 font-size: 10px; color: #64748B; font-weight: 600; }
      h1 { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 32px;
           margin: 6px 0 20px; color: #0B1F3A; font-weight: 600; }
      h2 { font-size: 13px; margin: 24px 0 8px; color: #0B1F3A;
           text-transform: uppercase; letter-spacing: 0.2em; border-bottom: 1px solid #0B1F3A;
           padding-bottom: 4px; }
      p { margin: 8px 0; line-height: 1.55; font-size: 14px; }
      table.meta { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
      table.meta td { padding: 8px 10px; border: 1px solid #E2E8F0; vertical-align: top; }
      table.meta td.k { background: #F1F5F9; width: 36%; font-weight: 600; color: #334155;
                         text-transform: uppercase; letter-spacing: 0.1em; font-size: 11px; }
      .sig-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 40px; }
      .sig-box { border-top: 1px solid #0B1F3A; padding-top: 8px; font-size: 12px; }
      .sig-box .role { text-transform: uppercase; letter-spacing: 0.2em; color: #64748B;
                        font-size: 10px; margin-bottom: 6px; }
      .foot { margin-top: 32px; font-size: 11px; color: #64748B; }
      ul.signoffs { list-style: none; padding: 0; margin: 0; }
      ul.signoffs li { padding: 6px 0; border-bottom: 1px dashed #E2E8F0; font-size: 13px; }
      ul.signoffs li b { color: #0F172A; }
      ul.signoffs li .ts { color: #64748B; font-size: 11px; margin-left: 8px; }
      @media print {
        .toolbar { display: none !important; }
        .page { box-shadow: none; border: none; margin: 0; padding: 20mm 16mm; }
        body { background: #ffffff; }
      }
    </style>"""


def _toolbar_html() -> str:
    return """
      <div class='toolbar'>
        <button class='ghost' onclick='window.close()'>Close</button>
        <button onclick='window.print()'>Print / Save PDF</button>
      </div>
    """


def _render_signoffs_html(summary: dict) -> str:
    items = []
    for s in (summary.get("signoffs") or []):
        if s.get("signed"):
            ts = (s.get("at") or "")[:19].replace("T", " ")
            items.append(f"<li><b>{_html.escape(s['label'])}</b> — "
                         f"{_html.escape(str(s.get('by') or '—'))}"
                         f"<span class='ts'>{ts}</span></li>")
        else:
            items.append(f"<li><b>{_html.escape(s['label'])}</b> — "
                         f"<span style='color:#94A3B8;'>pending</span></li>")
    for tx in (summary.get("escrow") or []):
        if tx.get("pmc_signed_at"):
            ts = (tx["pmc_signed_at"] or "")[:19].replace("T", " ")
            items.append(f"<li><b>Escrow — PMC officer</b> — "
                         f"{_html.escape(str(tx.get('pmc_officer') or '—'))}"
                         f"<span class='ts'>{ts}</span></li>")
        if tx.get("escrow_signed_at"):
            ts = (tx["escrow_signed_at"] or "")[:19].replace("T", " ")
            items.append(f"<li><b>Escrow — Institution officer</b> — "
                         f"{_html.escape(str(tx.get('escrow_officer') or '—'))}"
                         f"<span class='ts'>{ts}</span></li>")
    return "<ul class='signoffs'>" + ("".join(items) or "<li>No sign-offs recorded.</li>") + "</ul>"


def _render_award_letter_print(summary: dict) -> str:
    t = summary.get("tender") or {}
    w = summary.get("winner") or {}
    price = _fmt_money(w.get("price_amount"), w.get("price_currency") or "USD")
    return f"""<!doctype html><html><head><meta charset='utf-8'>
    <title>Award Letter · {_html.escape(summary.get('award_ref') or '')}</title>
    {_print_style()}</head><body>
      {_toolbar_html()}
      <div class='page'>
        <div class='kicker'>Letter of Acceptance</div>
        <h1>Contract Award &amp; Letter of Acceptance</h1>

        <table class='meta'>
          <tr><td class='k'>Award reference</td><td>{_html.escape(summary.get('award_ref') or '—')}</td></tr>
          <tr><td class='k'>Purchase order no.</td><td>{_html.escape(summary.get('po_no') or '—')}</td></tr>
          <tr><td class='k'>Date of award</td><td>{(summary.get('awarded_at') or '')[:10] or '—'}</td></tr>
          <tr><td class='k'>Awarding authority</td><td>PMC Managers Limited</td></tr>
          <tr><td class='k'>Awarded to</td><td>{_html.escape(w.get('company_name') or w.get('vendor_email') or '—')}</td></tr>
          <tr><td class='k'>Vendor reference</td><td>{_html.escape(w.get('vendor_ref') or '—')}</td></tr>
          <tr><td class='k'>Bid reference</td><td>{_html.escape(w.get('bid_ref') or '—')}</td></tr>
          <tr><td class='k'>Contract value</td><td>{price}</td></tr>
        </table>

        <h2>Tender timeline</h2>
        <table class='meta'>
          <tr><td class='k'>Tender reference</td><td>{_html.escape(t.get('notice_ref') or '—')}</td></tr>
          <tr><td class='k'>Tender title</td><td>{_html.escape(t.get('title') or '—')}</td></tr>
          <tr><td class='k'>Tender opened (published)</td><td>{(t.get('published_at') or '')[:19].replace('T',' ') or '—'}</td></tr>
          <tr><td class='k'>Submission deadline</td><td>{(t.get('submission_deadline') or '')[:19].replace('T',' ') or '—'}</td></tr>
          <tr><td class='k'>Bid submitted at</td><td>{(w.get('submitted_at') or '')[:19].replace('T',' ') or '—'}</td></tr>
          <tr><td class='k'>Technical envelope cleared</td><td>{(w.get('technical_cleared_at') or '')[:19].replace('T',' ') or '—'}</td></tr>
          <tr><td class='k'>Financial envelope opened</td><td>{(w.get('financial_opened_at') or '')[:19].replace('T',' ') or '—'}</td></tr>
        </table>

        <h2>Lifecycle sign-offs</h2>
        {_render_signoffs_html(summary)}

        <h2>Acceptance</h2>
        <p>Following evaluation of bids received in response to tender
         <b>{_html.escape(t.get('notice_ref') or '')} — {_html.escape(t.get('title') or '')}</b>,
         PMC Managers Limited is pleased to inform
         <b>{_html.escape(w.get('company_name') or w.get('vendor_email') or '—')}</b>
         that its bid has been accepted for the sum of <b>{price}</b>
         (inclusive of all applicable duties and taxes unless otherwise stated).</p>

        <div class='sig-grid'>
          <div class='sig-box'><div class='role'>PMC Managers Limited</div>
            Authorised Signatory<br/>Date: {(summary.get('awarded_at') or '')[:10] or '—'}
          </div>
          <div class='sig-box'><div class='role'>Accepted by Supplier</div>
            {_html.escape(w.get('company_name') or w.get('vendor_email') or '—')}<br/>
            Authorised Signatory<br/>Date: ______________
          </div>
        </div>
        <p class='foot'>System-generated — print or save as PDF for your records.</p>
      </div>
    </body></html>"""


def _render_contract_print(summary: dict) -> str:
    t = summary.get("tender") or {}
    w = summary.get("winner") or {}
    price = _fmt_money(w.get("price_amount"), w.get("price_currency") or "USD")
    return f"""<!doctype html><html><head><meta charset='utf-8'>
    <title>Contract · {_html.escape(summary.get('award_ref') or '')}</title>
    {_print_style()}</head><body>
      {_toolbar_html()}
      <div class='page'>
        <div class='kicker'>Procurement contract</div>
        <h1>Procurement contract &mdash; {_html.escape(summary.get('award_ref') or '')}</h1>

        <table class='meta'>
          <tr><td class='k'>Contract reference</td><td>{_html.escape(summary.get('award_ref') or '—')}</td></tr>
          <tr><td class='k'>Purchase order no.</td><td>{_html.escape(summary.get('po_no') or '—')}</td></tr>
          <tr><td class='k'>Effective date</td><td>{(summary.get('awarded_at') or '')[:10] or '—'}</td></tr>
          <tr><td class='k'>Buyer</td><td>PMC Managers Limited</td></tr>
          <tr><td class='k'>Supplier</td><td>{_html.escape(w.get('company_name') or w.get('vendor_email') or '—')}</td></tr>
          <tr><td class='k'>Supplier email</td><td>{_html.escape(w.get('vendor_email') or '—')}</td></tr>
          <tr><td class='k'>Contract value</td><td>{price}</td></tr>
          <tr><td class='k'>Reference tender</td><td>{_html.escape(t.get('notice_ref') or '—')} — {_html.escape(t.get('title') or '')}</td></tr>
          <tr><td class='k'>Delivery country</td><td>{_html.escape(t.get('delivery_country') or '—')}</td></tr>
        </table>

        <h2>1 · Scope of supply</h2>
        <p>{_html.escape(t.get('description') or 'As per the awarded bid and tender documents.')}</p>

        <h2>2 · Commercial summary</h2>
        <table class='meta'>
          <tr><td class='k'>Awarded contract value</td><td>{price}</td></tr>
          <tr><td class='k'>Reference bid</td><td>{_html.escape(w.get('bid_ref') or '—')}</td></tr>
          <tr><td class='k'>Bid submitted</td><td>{(w.get('submitted_at') or '')[:19].replace('T',' ') or '—'}</td></tr>
        </table>

        <h2>3 · Key terms</h2>
        <p><b>3.1</b> Payment terms, warranties and delivery milestones follow the tender documents and accompanying SLA.</p>
        <p><b>3.2</b> The Supplier shall furnish performance security within 14 days of this contract.</p>
        <p><b>3.3</b> The Earnest Money Deposit held in joint escrow shall be released or converted per the award decision.</p>
        <p><b>3.4</b> Any variation must be approved in writing by the Buyer's authorised signatory.</p>

        <h2>4 · Governance &amp; sign-offs</h2>
        {_render_signoffs_html(summary)}

        <h2>5 · Signature &amp; effect</h2>
        <p>Please counter-sign and return a copy of this contract within 7 (seven) days of receipt.</p>

        <div class='sig-grid'>
          <div class='sig-box'><div class='role'>PMC Managers Limited</div>
            Authorised Signatory<br/>Date: {(summary.get('awarded_at') or '')[:10] or '—'}
          </div>
          <div class='sig-box'><div class='role'>Supplier</div>
            {_html.escape(w.get('company_name') or w.get('vendor_email') or '—')}<br/>
            Authorised Signatory<br/>Date: ______________
          </div>
        </div>
        <p class='foot'>System-generated procurement contract — governed by the master tender documents and applicable local law.</p>
      </div>
    </body></html>"""


async def _resolve_bid_for_print(bid_id: str) -> dict:
    try:
        oid = ObjectId(bid_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed bid id")
    bid = await db.bids.find_one({"_id": oid})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@router.get("/bid/{bid_id}/award-letter.html")
async def print_award_letter_html(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting",
                                "auditor", "legal_counsel")),
) -> Response:
    """v51ba — browser-print view of the Award Letter."""
    bid = await _resolve_bid_for_print(bid_id)
    summary = await _build_award_summary(bid)
    html = _render_award_letter_print(summary)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/bid/{bid_id}/contract.html")
async def print_contract_html(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting",
                                "auditor", "legal_counsel")),
) -> Response:
    """v51ba — browser-print view of the Procurement Contract."""
    bid = await _resolve_bid_for_print(bid_id)
    summary = await _build_award_summary(bid)
    html = _render_contract_print(summary)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/bid/{bid_id}/award-letter.pdf")
async def download_award_letter_pdf(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting",
                                "auditor", "legal_counsel")),
) -> Response:
    """v51ba — PDF export of the Award Letter print view."""
    bid = await _resolve_bid_for_print(bid_id)
    summary = await _build_award_summary(bid)
    html = _render_award_letter_print(summary)
    try:
        pdf = _pdf_bytes(html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF render failed: {e}")
    fname = f"{summary.get('award_ref') or 'award'}-award-letter.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/bid/{bid_id}/contract.pdf")
async def download_contract_pdf(
    bid_id: str,
    admin=Depends(require_role("admin", "committee_member", "accounting",
                                "auditor", "legal_counsel")),
) -> Response:
    """v51ba — PDF export of the Procurement Contract print view."""
    bid = await _resolve_bid_for_print(bid_id)
    summary = await _build_award_summary(bid)
    html = _render_contract_print(summary)
    try:
        pdf = _pdf_bytes(html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF render failed: {e}")
    fname = f"{summary.get('award_ref') or 'award'}-procurement-contract.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/bid/{bid_id}/regenerate")
async def regenerate_award_docs(
    bid_id: str,
    admin=Depends(require_role("admin")),
) -> dict:
    """Manual re-run — useful after an admin edits a bid/notice post-award
    or if the initial WeasyPrint render failed on any of the three.

    Bug #41 — response now includes a version stamp so the UI can show
    'Regenerated at YYYY-MM-DD HH:MM by <admin>' as confirmation.
    """
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.get("status") != "awarded":
        raise HTTPException(status_code=400, detail="Bid is not in awarded status")
    result = await generate_award_documents(bid_id, admin.get("email"))
    regenerated_at = now_iso()
    result["regenerated_at"] = regenerated_at
    result["regenerated_by"] = admin.get("email")
    # Also stamp the bid record so future queries can show version history.
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$push": {"award_regenerations": {
            "at": regenerated_at,
            "by": admin.get("email"),
            "award_ref": result.get("award_ref"),
        }}},
    )
    await audit_log("award.regenerate", admin, "bid", bid.get("bid_ref"),
                    {"award_ref": result.get("award_ref"),
                     "regenerated_at": regenerated_at})
    return result
