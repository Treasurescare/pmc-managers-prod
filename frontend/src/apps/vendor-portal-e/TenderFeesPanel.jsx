import { useEffect, useState, useCallback } from "react";
import { vendorTenderApi, showApiError } from "@/lib/api";

const fmt = (c, n) => `${c} ${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export const TenderFeesPanel = ({ tid, dirty }) => {
  const [fees, setFees] = useState(null);
  const [busy, setBusy] = useState(null);
  const load = useCallback(() => vendorTenderApi.fees(tid).then((r) => setFees(r.fees)).catch(() => setFees([])), [tid]);
  useEffect(() => { if (!dirty) { load(); } }, [load, dirty]);
  if (!fees || fees.length === 0) return null;
  const pay = async (code) => {
    setBusy(code);
    try { const r = await vendorTenderApi.feeCheckout(tid, code, window.location.origin); window.location.href = r.checkout_url; }
    catch (e) { showApiError(e); setBusy(null); }
  };
  return (
    <div data-testid="tb-fees-panel" className="border border-amber-500/50 bg-amber-50 p-4">
      <div className="pmc-label mb-2">Fees for this tender</div>
      {dirty && <div className="text-[11px] text-amber-800 mb-2">Save your changes to recalculate fees.</div>}
      <div className="space-y-2">
        {fees.map((f) => (
          <div key={f.code} data-testid={`tb-fee-${f.code}`} className="flex items-center justify-between gap-3 flex-wrap text-sm">
            <div>
              <b>{f.name}</b>
              <span className="text-brand-navy/60"> · {f.timing === "upfront" ? "pay before you start" : "pay before submitting"}</span>
              <div className="text-xs text-brand-navy/70" data-testid={`tb-fee-amount-${f.code}`}>
                {f.needs_value ? "Enter the tender value and save to calculate this fee"
                  : f.paid ? `Paid ${fmt(f.currency, f.paid_amount)}`
                  : `${fmt(f.currency, f.outstanding)} due${f.paid_amount ? ` (already paid ${fmt(f.currency, f.paid_amount)})` : ""}`}
              </div>
            </div>
            {f.paid ? <span className="text-[11px] uppercase tracking-widest text-emerald-700" data-testid={`tb-fee-paid-${f.code}`}>✓ Paid</span>
              : !f.needs_value && (
                <button onClick={() => pay(f.code)} disabled={!!busy || dirty} data-testid={`tb-fee-pay-${f.code}`}
                        className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-40">
                  {busy === f.code ? "Opening Stripe…" : "Pay now"}
                </button>
              )}
          </div>
        ))}
      </div>
    </div>
  );
};
