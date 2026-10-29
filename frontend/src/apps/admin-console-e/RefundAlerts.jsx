import { useEffect, useState } from "react";
import { toast } from "sonner";
import { extraPayApi, showApiError } from "@/lib/api";

export const RefundAlerts = () => {
  const [rows, setRows] = useState(null);
  const load = () => extraPayApi.refundAlerts().then((r) => setRows(r.items || [])).catch(() => setRows([]));
  useEffect(() => { load(); }, []);
  const refund = async (sid) => {
    if (!window.confirm("Refund this payment in full through Stripe?")) return;
    try { await extraPayApi.refund(sid); toast.success("Refund issued"); load(); } catch (e) { showApiError(e); load(); }
  };
  if (!rows || rows.length === 0) return null;
  return (
    <div className="bg-white border border-red-300 p-4 mb-4" data-testid="refund-alerts">
      <div className="text-sm font-semibold text-red-800 mb-2">Payments that need a refund ({rows.length})</div>
      <div className="text-xs text-brand-navy/60 mb-3">Duplicate or stale payments — e.g. an old link paid after the request was already settled.</div>
      {rows.map((r) => (
        <div key={r.session_id} className="flex justify-between items-center gap-3 py-2 border-t border-brand-navy/10 text-sm flex-wrap" data-testid={`refund-row-${r.session_id}`}>
          <div>
            <b>{(r.currency || "").toUpperCase()} {Number(r.amount || 0).toLocaleString()}</b> · {String(r.purpose || "").replace(/_/g, " ")} · {r.vendor_ref || r.payer_email || "—"}
            <div className="text-[11px] font-mono text-brand-navy/50">{r.session_id}</div>
            {r.refund_error && <div className="text-xs text-red-700">Last attempt failed: {r.refund_error}</div>}
          </div>
          <button onClick={() => refund(r.session_id)} data-testid={`refund-btn-${r.session_id}`}
                  className="px-3 py-1.5 text-[10px] uppercase tracking-widest bg-red-700 text-white">Refund</button>
        </div>
      ))}
    </div>
  );
};
