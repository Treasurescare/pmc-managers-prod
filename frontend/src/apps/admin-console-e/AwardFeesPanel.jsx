import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { pricingApi, showApiError } from "@/lib/api";

const btn = "px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5";
const TONE = { paid: "text-emerald-700", unpaid: "text-amber-700", waived: "text-slate-500", nil: "text-slate-500" };

const WaiveForm = ({ id, onDone }) => {
  const [reason, setReason] = useState("");
  const ok = reason.trim().length >= 3;
  const go = () => pricingApi.waiveAwardFee(id, reason.trim()).then(() => { toast.success("Award fee waived"); onDone(true); }).catch(showApiError);
  return (
    <div className="w-full flex flex-wrap gap-2 items-center" data-testid={`award-fee-waive-form-${id}`}>
      <input className="flex-1 min-w-[220px] px-2 py-1 border border-brand-navy/20 text-xs" placeholder="Reason for waiving (min 3 characters)"
        value={reason} onChange={(e) => setReason(e.target.value)} data-testid={`award-fee-waive-reason-${id}`} />
      <button className={btn} disabled={!ok} onClick={go} data-testid={`award-fee-waive-confirm-${id}`}>Confirm waive</button>
      <button className={btn} onClick={() => onDone(false)} data-testid={`award-fee-waive-cancel-${id}`}>Cancel</button>
    </div>);
};

export default function AwardFeesPanel() {
  const [items, setItems] = useState([]);
  const [waiving, setWaiving] = useState(null);
  const load = useCallback(() => pricingApi.awardFees().then((r) => setItems(r.items || [])).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const resend = (id) => pricingApi.resendAwardFee(id).then(() => { toast.success("Payment link resent"); load(); }).catch(showApiError);
  const waive = (id) => setWaiving(id);
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
            {a.note && <div className="w-full text-xs text-amber-700" data-testid={`award-fee-note-${a.bid_id}`}>{a.note}</div>}
            {waiving === a.bid_id && <WaiveForm id={a.bid_id} onDone={(changed) => { setWaiving(null); if (changed) load(); }} />}
          </div>))}
      </div>
    </div>);
}
