"""v52x — Submission-close sweep cron.

Daily sweep (platform cron, see .emergent/crons.yml): finds notices whose
submission_deadline passed in the last 24h and have not been swept yet, then
fans out "submissions closed" notifications:

- Admin role: per-tender summary (bid count, EMD paid/pending, tech-cleared)
  with the next-step checklist.
- Committee members: same summary + Evaluation panel link.
- Vendors (per bidder): current pipeline stage + the full chain of events.
- Escrow agents: ONE summary email per day across all closed tenders listing
  bids whose EMD is still pending.

Contract: ack 2xx immediately, enqueue real work (platform dispatcher ~5s).
Idempotent per run_id (cron_runs) AND per notice (submission_close_notified_at).
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Header

import config
from db import db
from models.base import now_iso
from routers.cron_escrow import _verify_bearer

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])
log = logging.getLogger("cron.submission_close")

SWEEP_WINDOW_HOURS = 24

PIPELINE_STEPS = [
    ("EMD verification", "Escrow confirms your Earnest Money Deposit."),
    ("Technical evaluation", "Evaluators score/clear the technical envelope."),
    ("Legal & accounting sign-off", "Legal counsel and accounting review the cleared bid."),
    ("Committee decision", "The bid committee runs the L1 comparison or rubric scoring."),
    ("Award & contract", "Winner is awarded; PO/SLA/contract documents are issued for e-signature."),
]

# bid status -> 1-based pipeline step
_STATUS_STEP = {
    "draft": 1, "submitted": 1, "emd_pending": 1,
    "emd_paid": 1, "escrow_accepted": 2,
    "admin_flagged": 2, "certifier_cleared": 2, "technical_cleared": 2,
    "legal_cleared": 3, "accounting_cleared": 3,
    "commercial_open": 4, "under_evaluation": 4,
    "awarded": 5, "non_winner": 5,
}


def _chain_html(current_step: int) -> str:
    rows = []
    for i, (name, desc) in enumerate(PIPELINE_STEPS, start=1):
        marker = "&#9654;" if i == current_step else ("&#10003;" if i < current_step else "&#8226;")
        style = "font-weight:bold;" if i == current_step else ""
        rows.append(f"<li style='{style}'>{marker} Step {i} — {name}: {desc}</li>")
    return "<ul style='list-style:none;padding-left:0'>" + "".join(rows) + "</ul>"


@router.post("/submission-close-sweep")
async def submission_close_sweep(
    authorization: str = Header(default=""),
    x_webhook_id: str = Header(default=""),
):
    _verify_bearer(authorization)
    run_id = x_webhook_id or now_iso()
    seen = await db.cron_runs.find_one({"run_id": run_id, "name": "submission-close-sweep"})
    if seen:
        return {"ok": True, "duplicate": True}
    await db.cron_runs.insert_one({"run_id": run_id,
                                    "name": "submission-close-sweep",
                                    "started_at": now_iso()})
    asyncio.create_task(_do_sweep(run_id))
    return {"ok": True, "run_id": run_id, "status": "queued"}


async def _do_sweep(run_id: str) -> None:
    from notify import notify_role, vendor_confirm

    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=SWEEP_WINDOW_HOURS)).isoformat()
    stats = {"tenders": 0, "vendor_emails": 0, "skipped_already_notified": 0}
    escrow_pending_rows = []  # (notice_ref, bid_ref, vendor, amount, currency)
    try:
        cursor = db.notices.find({
            "submission_deadline": {"$gte": window_start, "$lte": now.isoformat()},
            "submission_close_notified_at": {"$exists": False},
        })
        async for notice in cursor:
            ref = notice.get("notice_ref")
            title = notice.get("title") or ref
            bids = [b async for b in db.bids.find(
                {"notice_ref": ref,
                 "status": {"$nin": ["draft", "withdrawn"]}})]
            if not bids:
                # Nothing to evaluate — still mark swept so we don't rescan daily.
                await db.notices.update_one(
                    {"_id": notice["_id"]},
                    {"$set": {"submission_close_notified_at": now_iso()}})
                continue

            total = len(bids)
            emd_paid = [b for b in bids if (b.get("emd_paid_amount") or 0) > 0]
            emd_pending = [b for b in bids
                           if b.get("status") == "emd_pending"
                           and (b.get("emd_paid_amount") or 0) <= 0]
            tech_cleared = [b for b in bids if b.get("technical_cleared_at")]

            summary_rows = "".join(
                f"<tr><td>{b.get('bid_ref')}</td>"
                f"<td>{b.get('company_name') or b.get('vendor_email')}</td>"
                f"<td>{b.get('status')}</td>"
                f"<td>{'paid' if (b.get('emd_paid_amount') or 0) > 0 else 'pending'}</td>"
                f"<td>{'yes' if b.get('technical_cleared_at') else 'no'}</td></tr>"
                for b in bids)
            summary_table = (
                "<table border='1' cellpadding='6' cellspacing='0' "
                "style='border-collapse:collapse;font-size:13px'>"
                "<tr><th>Bid ref</th><th>Vendor</th><th>Stage</th>"
                "<th>EMD</th><th>Tech cleared</th></tr>"
                f"{summary_rows}</table>")

            # --- Admin + committee: per-tender summary -------------------
            staff_subject = f"Submissions closed — {ref} ({total} bid{'s' if total != 1 else ''})"
            staff_body = (
                f"<p>The submission window for <strong>{title}</strong> "
                f"(<code>{ref}</code>) closed at "
                f"<strong>{notice.get('submission_deadline')}</strong>.</p>"
                f"<p><strong>{total}</strong> bid(s) received · "
                f"EMD paid: <strong>{len(emd_paid)}</strong> · "
                f"EMD pending: <strong>{len(emd_pending)}</strong> · "
                f"Technically cleared: <strong>{len(tech_cleared)}</strong></p>"
                f"{summary_table}"
                f"<p><strong>Next steps:</strong> Bidding Ops &rarr; confirm EMD "
                f"with escrow &rarr; technical clearance &rarr; legal/accounting "
                f"sign-off &rarr; run the <em>L1 Comparison</em> or score the "
                f"<em>Rubric</em> in the Evaluation panel &rarr; award.</p>")
            await notify_role("admin", staff_subject, staff_body,
                              related_type="notice", related_id=ref)
            await notify_role(
                "committee_member", staff_subject,
                staff_body +
                f"<p>Open the <a href='{config.FRONTEND_URL}/admin'>Evaluation "
                f"panel</a> to score or review the L1 comparison.</p>",
                related_type="notice", related_id=ref)

            # --- Vendors: per-bidder stage + full chain ------------------
            for b in bids:
                step = _STATUS_STEP.get(b.get("status"), 1)
                step_name = PIPELINE_STEPS[step - 1][0]
                body = (
                    f"<p>Thank you for your bid <strong>{b.get('bid_ref')}</strong> on "
                    f"<strong>{title}</strong> (<code>{ref}</code>).</p>"
                    f"<p>The submission window has now closed. Your bid is currently "
                    f"at <strong>Step {step} — {step_name}</strong> "
                    f"(status: <code>{b.get('status')}</code>).</p>")
                if b.get("status") == "emd_pending":
                    body += ("<p><strong>Action needed:</strong> our records show your "
                             "EMD payment is still pending. Please complete it or contact "
                             "PMC support — bids without a confirmed EMD cannot enter "
                             "technical evaluation.</p>")
                body += ("<p>Here is the full evaluation journey your bid follows:</p>"
                         + _chain_html(step)
                         + "<p>You will receive an email each time your bid moves to "
                           "the next step.</p>")
                await vendor_confirm(b.get("vendor_email"),
                                     f"Submissions closed — {ref}", body,
                                     "Track my bid",
                                     f"{config.FRONTEND_URL}/vendor/mybids")
                stats["vendor_emails"] += 1

            # --- Collect for the daily escrow summary --------------------
            for b in emd_pending:
                escrow_pending_rows.append((ref, b.get("bid_ref"),
                                            b.get("company_name") or b.get("vendor_email"),
                                            b.get("emd_amount") or b.get("emd_due_amount") or 0,
                                            b.get("emd_currency") or ""))

            await db.notices.update_one(
                {"_id": notice["_id"]},
                {"$set": {"submission_close_notified_at": now_iso()}})
            stats["tenders"] += 1

        # --- Escrow agents: ONE summary email for the whole run ----------
        if escrow_pending_rows:
            rows_html = "".join(
                f"<tr><td>{ref}</td><td>{bid_ref}</td><td>{vendor}</td>"
                f"<td>{ccy} {amt:,.2f}</td></tr>"
                for ref, bid_ref, vendor, amt, ccy in escrow_pending_rows)
            await notify_role(
                "escrow_agent",
                f"Daily EMD watchlist — {len(escrow_pending_rows)} pending across "
                f"{stats['tenders']} closed tender(s)",
                "<p>The following bids belong to tenders whose submission window "
                "closed in the last 24h, but their EMD is still marked pending. "
                "Please verify receipt or flag for disqualification:</p>"
                "<table border='1' cellpadding='6' cellspacing='0' "
                "style='border-collapse:collapse;font-size:13px'>"
                "<tr><th>Tender</th><th>Bid ref</th><th>Vendor</th>"
                "<th>EMD due</th></tr>"
                f"{rows_html}</table>",
                related_type="cron", related_id=run_id)
    except Exception as e:
        log.exception("submission-close sweep failed: %s", e)
        stats["error"] = str(e)
    finally:
        await db.cron_runs.update_one(
            {"run_id": run_id, "name": "submission-close-sweep"},
            {"$set": {"finished_at": now_iso(), **stats}})
