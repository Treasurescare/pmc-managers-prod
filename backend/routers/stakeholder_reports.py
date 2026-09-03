"""G4 Rebuild — Stakeholder Reports (matches the description in the doc).

The prior /reports router surfaces the "asked vs delivered" statement, which is
useful for investors but doesn't answer the description in the observations doc:

    "Stakeholder-facing reports on tenders, awards, escrow, SLAs."

This module rebuilds G4 with four real reports keyed off live collections:

  1. GET /api/v1/stakeholder-reports/tenders    — pipeline snapshot per notice
  2. GET /api/v1/stakeholder-reports/awards     — awarded bids, PO#, contract value
  3. GET /api/v1/stakeholder-reports/escrow     — accounts + aging days per status
  4. GET /api/v1/stakeholder-reports/sla        — active contracts + milestone hit-rate

Each returns JSON summary + a downloadable CSV (Content-Disposition: attachment).
Admin/reviewer/auditor gated.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from db import db
from security import require_role

router = APIRouter(prefix="/api/v1/stakeholder-reports", tags=["stakeholder-reports"])


# ----- helpers ----------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_days_ago(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        s = iso.replace("Z", "+00:00") if iso.endswith("Z") else iso
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int((_now() - d).total_seconds() // 86400)
    except Exception:
        return None


def _csv_response(rows: list, headers: list, filename: str) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h, "") for h in headers])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


# ----- 1. TENDERS -------------------------------------------------------------

@router.get("/tenders")
async def tenders_report(
    format: str = "json",
    admin=Depends(require_role("admin", "reviewer", "auditor")),
):
    """Pipeline snapshot per published notice — bidder counts, EMDs held, corrigenda,
    days since publish. Answers 'where does every live tender stand right now?'."""
    rows = []
    async for n in db.notices.find({}).sort("published_at", -1).limit(500):
        nref = n.get("notice_ref")
        bid_total = await db.bids.count_documents({"notice_ref": nref})
        bid_awarded = await db.bids.count_documents(
            {"notice_ref": nref, "status": "awarded"},
        )
        bid_rejected = await db.bids.count_documents(
            {"notice_ref": nref, "status": "rejected"},
        )
        corr_count = await db.corrigenda.count_documents(
            {"notice_ref": nref, "is_active": True},
        )
        rows.append({
            "notice_ref": nref,
            "title": (n.get("title") or "")[:80],
            "status": "PUBLISHED" if n.get("is_published") else "DRAFT",
            "category": n.get("category") or "",
            "delivery_country": n.get("delivery_country") or "",
            "budget": f"{n.get('budget_currency','')} {n.get('budget_amount') or 0:.2f}",
            "submission_deadline": (n.get("submission_deadline") or "")[:10],
            "days_since_publish": _iso_days_ago(n.get("published_at")),
            "bids_total": bid_total,
            "bids_awarded": bid_awarded,
            "bids_rejected": bid_rejected,
            "active_corrigenda": corr_count,
        })
    if format == "csv":
        return _csv_response(rows,
            ["notice_ref", "title", "status", "category", "delivery_country",
             "budget", "submission_deadline", "days_since_publish",
             "bids_total", "bids_awarded", "bids_rejected", "active_corrigenda"],
            "stakeholder-tenders.csv")
    return {"generated_at": _now().isoformat(), "count": len(rows), "items": rows}


# ----- 2. AWARDS --------------------------------------------------------------

@router.get("/awards")
async def awards_report(
    format: str = "json",
    admin=Depends(require_role("admin", "reviewer", "auditor")),
):
    """Awarded bids with PO number, contract value, awarding officer, days elapsed."""
    rows = []
    cursor = db.bids.find({"status": "awarded"}).sort("awarded_at", -1).limit(500)
    async for b in cursor:
        rows.append({
            "bid_ref": b.get("bid_ref"),
            "notice_ref": b.get("notice_ref"),
            "vendor": b.get("company_name") or b.get("vendor_email") or "",
            "po_no": b.get("po_no") or "",
            "award_ref": b.get("award_ref") or "",
            "price": f"{b.get('price_currency') or 'USD'} {b.get('price_amount') or 0:.2f}",
            "awarded_at": (b.get("awarded_at") or "")[:19],
            "awarded_by": b.get("awarded_by") or "",
            "days_since_award": _iso_days_ago(b.get("awarded_at")),
            "regenerations": len(b.get("award_regenerations") or []),
        })
    if format == "csv":
        return _csv_response(rows,
            ["bid_ref", "notice_ref", "vendor", "po_no", "award_ref", "price",
             "awarded_at", "awarded_by", "days_since_award", "regenerations"],
            "stakeholder-awards.csv")
    return {"generated_at": _now().isoformat(), "count": len(rows), "items": rows}


# ----- 3. ESCROW --------------------------------------------------------------

@router.get("/escrow")
async def escrow_report(
    format: str = "json",
    admin=Depends(require_role("admin", "reviewer", "auditor")),
):
    """Escrow accounts + transactions with **aging** in days for each pending sign.
    Directly answers the observations doc ask: 'Escrow aging + SLA threshold'.
    """
    rows = []
    async for acc in db.escrow_accounts.find({}).sort("created_at", -1).limit(500):
        # Aging for a joint account = time since last status change.
        hist = acc.get("history") or []
        last_at = hist[-1].get("at") if hist else acc.get("created_at")
        rows.append({
            "account_id": str(acc.get("_id")),
            "name": acc.get("name") or "",
            "pmc_officer": acc.get("pmc_officer") or "",
            "vendor_officer": acc.get("vendor_officer") or "",
            "status": acc.get("status") or "unknown",
            "history_entries": len(hist),
            "aging_days": _iso_days_ago(last_at),
            "created_at": (acc.get("created_at") or "")[:19],
        })
    # Also flatten open transactions so aging is visible per transaction.
    tx_rows = []
    async for tx in db.escrow_transactions.find({}).sort("created_at", -1).limit(500):
        state = tx.get("status") or ""
        aging = _iso_days_ago(tx.get("created_at"))
        tx_rows.append({
            "transaction_id": str(tx.get("_id")),
            "account_ref": tx.get("account_ref") or "",
            "bid_ref": tx.get("bid_ref") or "",
            "amount": f"{tx.get('currency') or 'USD'} {tx.get('amount') or 0:.2f}",
            "state": state,
            "signed_by_pmc": bool(tx.get("pmc_signed_at")),
            "signed_by_vendor": bool(tx.get("vendor_signed_at")),
            "aging_days": aging,
            "sla_breach": (aging is not None and aging > 7 and
                           state not in ("released", "refunded", "forfeited")),
        })
    if format == "csv":
        # Simple: concat both. Two-header CSV keeps stakeholder file readable.
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["--- Escrow accounts ---"])
        acc_cols = ["account_id", "name", "pmc_officer", "vendor_officer",
                    "status", "history_entries", "aging_days", "created_at"]
        w.writerow(acc_cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in acc_cols])
        w.writerow([])
        w.writerow(["--- Escrow transactions ---"])
        tx_cols = ["transaction_id", "account_ref", "bid_ref", "amount", "state",
                   "signed_by_pmc", "signed_by_vendor", "aging_days", "sla_breach"]
        w.writerow(tx_cols)
        for r in tx_rows:
            w.writerow([r.get(c, "") for c in tx_cols])
        return Response(
            content=buf.getvalue(), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="stakeholder-escrow.csv"',
                     "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )
    return {
        "generated_at": _now().isoformat(),
        "accounts": rows,
        "transactions": tx_rows,
        "sla_threshold_days": 7,
        "sla_breaches": sum(1 for t in tx_rows if t["sla_breach"]),
    }


# ----- 4. SLA / Contracts -----------------------------------------------------

@router.get("/sla")
async def sla_report(
    format: str = "json",
    admin=Depends(require_role("admin", "reviewer", "auditor")),
):
    """Active contracts + milestone completion rate + variation orders per contract."""
    rows = []
    async for c in db.contracts.find({}).sort("created_at", -1).limit(500):
        milestones = c.get("milestones") or []
        completed = sum(1 for m in milestones if m.get("status") == "completed")
        rows.append({
            "contract_ref": c.get("contract_ref"),
            "bid_id": c.get("bid_id"),
            "vendor_id": c.get("vendor_id"),
            "title": (c.get("title") or "")[:80],
            "value": f"{c.get('currency') or 'USD'} {c.get('value') or 0:.2f}",
            "start_date": (c.get("start_date") or "")[:10],
            "end_date": (c.get("end_date") or "")[:10],
            "milestones_total": len(milestones),
            "milestones_done": completed,
            "milestone_hit_rate_pct": round(100 * completed / max(1, len(milestones)), 1),
            "variation_orders": len(c.get("variation_orders") or []),
            "status": c.get("status") or "unknown",
        })
    if format == "csv":
        return _csv_response(rows,
            ["contract_ref", "bid_id", "vendor_id", "title", "value",
             "start_date", "end_date", "milestones_total", "milestones_done",
             "milestone_hit_rate_pct", "variation_orders", "status"],
            "stakeholder-sla.csv")
    return {"generated_at": _now().isoformat(), "count": len(rows), "items": rows}
