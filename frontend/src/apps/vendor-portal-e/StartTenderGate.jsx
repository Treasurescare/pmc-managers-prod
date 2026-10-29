import { useEffect, useState } from "react";
import { vendorTenderApi, showApiError } from "@/lib/api";

const money = (c, n) => `${(c || "").toUpperCase()} ${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export const StartTenderGate = ({ onClose, onReady }) => {
  const [cats, setCats] = useState([]);
  const [category, setCategory] = useState("");
  const [value, setValue] = useState("");
  const [quote, setQuote] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { vendorTenderApi.scope().then((s) => setCats(s.approved_categories || [])).catch(() => {}); }, []);
  const body = () => ({ category, tender_value: value === "" ? null : Number(value) });
  const getQuote = async () => {
    setBusy(true);
    try { setQuote(await vendorTenderApi.startQuote(body())); } catch (e) { showApiError(e); setQuote(null); }
    finally { setBusy(false); }
  };
  const pay = async () => {
    setBusy(true);
    try {
      const r = await vendorTenderApi.startCheckout({ ...body(), origin_url: window.location.origin });
      if (r.free) { onReady(r.credit_id); return; }
      window.location.href = r.checkout_url;
    } catch (e) { showApiError(e); setBusy(false); }
  };
  return (
    <div data-testid="start-gate" onClick={onClose}
         style={{ position: "fixed", inset: 0, background: "rgba(10,16,30,.55)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
      <div className="bg-white border border-brand-navy/20 p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="pmc-label mb-1">Before you start</div>
        <h3 className="text-lg font-semibold text-brand-navy mb-1">Pay the tender start fee</h3>
        <p className="text-sm text-brand-navy/60 mb-4">Choose the category and estimated value of the tender you want to build. The fee is set by PMC's fee rules.</p>
        <label className="block mb-3"><span className="pmc-label">Category *</span>
          <select value={category} onChange={(e) => { setCategory(e.target.value); setQuote(null); }} data-testid="start-gate-category"
                  className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
            <option value="">— choose an approved category —</option>
            {cats.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          {cats.length === 0 && <span className="text-xs text-red-700">You have no approved categories yet — request one under Categories.</span>}
        </label>
        <label className="block mb-4"><span className="pmc-label">Estimated tender value</span>
          <input type="number" min={0} value={value} onChange={(e) => { setValue(e.target.value); setQuote(null); }} data-testid="start-gate-value"
                 className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
        {quote && (
          <div className="border border-amber-500/50 bg-amber-50 p-3 mb-4 text-sm" data-testid="start-gate-quote">
            {quote.fees.length === 0 ? "No start fee applies to this category." : quote.fees.map((f) => (
              <div key={f.code} className="flex justify-between"><span>{f.name}</span><span>{money(f.currency, f.amount)}</span></div>
            ))}
            {quote.fees.length > 0 && <div className="flex justify-between font-semibold border-t border-amber-500/30 mt-2 pt-2"><span>Total</span><span data-testid="start-gate-total">{money(quote.currency, quote.total)}</span></div>}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} data-testid="start-gate-cancel" className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30">Cancel</button>
          {!quote ? (
            <button onClick={getQuote} disabled={!category || busy} data-testid="start-gate-quote-btn"
                    className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-40">See fee</button>
          ) : (
            <button onClick={pay} disabled={busy} data-testid="start-gate-pay"
                    className="px-4 py-2 text-[11px] uppercase tracking-widest bg-emerald-600 text-white disabled:opacity-40">
              {busy ? "Opening…" : quote.total > 0 ? "Pay with Stripe" : "Start building"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
