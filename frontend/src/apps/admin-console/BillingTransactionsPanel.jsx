import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { feeBillingApi, showApiError } from "@/lib/api";

/**
 * v46c — Admin transactions panel with Stripe refund.
 * Lists all payment_transactions rows (checkouts + fee-checkouts). Admin can
 * refund paid rows via Stripe Refunds API.
 */
export default function BillingTransactionsPanel() {
  const [rows, setRows]     = useState([]);
  const [busy, setBusy]     = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await feeBillingApi.listTransactions(100);
      setRows(r.items || []);
    } catch (e) { showApiError(e); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const refund = async (row) => {
    // eslint-disable-next-line no-alert
    const reason = window.prompt(`Refund ${row.currency?.toUpperCase()} ${row.amount} for ${row.buyer_email}?\nOptional reason:`, "");
    if (reason === null) return;
    setBusy(row.session_id);
    try {
      const r = await feeBillingApi.refund(row.session_id, reason || null);
      toast.success(`Refunded · ${r.refund_id}`);
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(null); }
  };

  return (
    <div data-testid="billing-transactions-panel">
      <div className="mb-3 flex justify-between items-baseline">
        <div>
          <div className="pmc-label">Payment transactions</div>
          <p className="text-xs text-brand-navy/60 mt-1">
            All Stripe checkout sessions (subscriptions, fees, EMD). Refund a paid
            transaction to trigger a Stripe refund on the underlying PaymentIntent.
          </p>
        </div>
        <button onClick={load} data-testid="btp-refresh"
                className="text-[11px] uppercase tracking-widest px-3 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
          Refresh
        </button>
      </div>
      <div className="bg-white border">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-sm min-w-[860px]">
            <thead className="text-xs text-brand-navy/60 border-b">
              <tr>
                <th className="text-left px-3 py-2">Session</th>
                <th className="text-left px-3 py-2">Buyer</th>
                <th className="text-left px-3 py-2">Product / Fee</th>
                <th className="text-right px-3 py-2">Amount</th>
                <th className="px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Created</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t align-top" data-testid={`btp-row-${r.session_id}`}>
                  <td className="px-3 py-2 font-mono text-[10px] max-w-[180px]"><div className="truncate">{r.session_id}</div></td>
                  <td className="px-3 py-2 text-xs">
                    <div>{r.buyer_email}</div>
                    <div className="text-[10px] text-slate-500">{r.buyer_role}</div>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <div>{r.product_code}</div>
                    {r.fee_kind && <div className="text-[10px] text-slate-500">Fee kind: {r.fee_kind}</div>}
                    {r.context_ref && <div className="text-[10px] text-slate-500">Ref: {r.context_ref}</div>}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {(r.currency || "").toUpperCase()} {r.amount?.toLocaleString?.() ?? r.amount}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 ${r.payment_status === "paid" ? "bg-emerald-100 text-emerald-800" : r.payment_status === "refunded" ? "bg-slate-300 text-slate-700" : "bg-amber-100 text-amber-800"}`}>
                      {r.payment_status || r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-[10px] text-slate-500 font-mono">{(r.created_at || "").slice(0, 19).replace("T", " ")}</td>
                  <td className="px-3 py-2 text-center">
                    {r.payment_status === "paid" ? (
                      <button onClick={() => refund(r)} disabled={busy === r.session_id}
                              data-testid={`btp-refund-${r.session_id}`}
                              className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-600 hover:bg-red-600 hover:text-white disabled:opacity-40">
                        Refund
                      </button>
                    ) : r.payment_status === "refunded" ? (
                      <span className="text-[10px] uppercase tracking-widest text-slate-500">refunded</span>
                    ) : (
                      <span className="text-[10px] uppercase tracking-widest text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={7} className="p-6 text-center text-slate-500">No transactions yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
