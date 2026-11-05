import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { pricingApi, showApiError } from "@/lib/api";

const btn = "px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5";
const TONE = { paid: "text-emerald-700", unpaid: "text-amber-700", waived: "text-slate-500", nil: "text-slate-500" };

export default function AwardFeesPanel() {
  const [items, setItems] = useState([]);
  const load = useCallback(() => pricingApi.awardFees().then((r) => setItems(r.items || [])).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const resend = (id) => pricingApi.resendAwardFee(id).then(() => { toast.success("Payment link resent"); load(); }).catch(showApiError);
  const waive = (id) => {
    const reason = window.prompt("Reason for waiving this award fee");
    if (reason) pricingApi.waiveAwardFee(id, reason).then(() => { toast.success("Award fee waived"); load(); }).catch(showApiError);
  };
  return (
    <div className="bg-white border border-brand-navy/10 p-4 mb-4" data-testid="award-fees-panel">
      <div className="pmc-label mb-2">Award fees ({items.length})</div>
      {!items.length && <div className="text-sm text-brand-navy/50" data-testid="award-fees-empty">No award fees yet. They appear here automatically when a tender is awarded.</div>}
      <div className="divide-y divide-brand-navy/10">
        {items.map((a) => (
          <div key={a.id} className="py-2 flex flex-wrap items-center gap-3 text-sm" data-testid={`award-fee-row-${a.bid_id}`}>
            <div className="flex-1 min-w-[240px]">
              <b>{a.notice_ref}</b> · {a.company_name} <span className="text-brand-navy/50">· bid {a.bid_ref}</span>
              <div className="text-xs text-brand-navy/60">Paid by {a.payer} {a.payer_email ? `<${a.payer_email}>` : ""} · {a.rate || a.reason || ""}{a.links_sent ? ` · links sent ${a.links_sent}` : ""}</div>
            </div>
            <span className="font-mono" data-testid={`award-fee-amount-${a.bid_id}`}>{a.currency} {Number(a.amount || 0).toLocaleString()}</span>
            <span className={`text-xs uppercase font-semibold ${TONE[a.status] || ""}`} data-testid={`award-fee-status-${a.bid_id}`}>{a.status}</span>
            {a.status === "unpaid" && <>
              <button className={btn} onClick={() => resend(a.bid_id)} data-testid={`award-fee-resend-${a.bid_id}`}>Resend link</button>
              <button className={btn} onClick={() => waive(a.bid_id)} data-testid={`award-fee-waive-${a.bid_id}`}>Waive</button>
            </>}
          </div>))}
      </div>
    </div>);
}
