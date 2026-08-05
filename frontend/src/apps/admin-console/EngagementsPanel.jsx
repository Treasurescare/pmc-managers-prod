/**
 * EngagementsPanel — Wave 38 admin surface for the quote pipeline.
 *
 * Lists every engagement (quote request), lets admin set the quoted amount +
 * currency, and one-click generates a Stripe checkout URL for the buyer.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_STYLE = {
  quote_requested: "bg-amber-100 text-amber-900 border-amber-400",
  quoted:          "bg-sky-100 text-sky-900 border-sky-400",
  invoiced:        "bg-indigo-100 text-indigo-900 border-indigo-400",
  paid:            "bg-emerald-100 text-emerald-900 border-emerald-400",
  cancelled:       "bg-slate-100 text-slate-700 border-slate-300",
};

const CURRENCIES = ["USD", "GBP", "EUR", "KZT", "INR", "AED", "SAR"];

function QuoteModal({ engagement, onClose, onSaved }) {
  const [amount, setAmount] = useState(engagement?.quoted_amount || "");
  const [currency, setCurrency] = useState(engagement?.quoted_currency || engagement?.product_currency || "USD");
  const [notes, setNotes] = useState(engagement?.admin_notes || "");
  const [validUntil, setValidUntil] = useState(engagement?.quote_valid_until || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/v1/engagements/${engagement.id}/quote`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          quoted_amount: Number(amount),
          quoted_currency: currency,
          admin_notes: notes || null,
          valid_until: validUntil || null,
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success("Quote saved — buyer can now be invoiced");
      onSaved();
    } catch (e) { toast.error(`Save failed: ${e.message}`); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-brand-navy/40 backdrop-blur-sm z-50 flex items-start justify-center p-6 overflow-y-auto"
         data-testid="engagement-quote-modal">
      <div className="bg-white border-2 border-brand-navy w-full max-w-lg p-8 my-8">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-xl text-brand-navy">Quote engagement</h3>
          <button onClick={onClose} className="text-brand-navy/60 hover:text-brand-navy"
                  data-testid="engagement-quote-close">✕</button>
        </div>
        <div className="mt-2 text-xs text-brand-navy/60">
          <b>{engagement.product_name}</b> · buyer <span className="font-mono">{engagement.buyer_email}</span> · qty {engagement.quantity}
        </div>
        {engagement.buyer_notes && (
          <div className="mt-3 border-l-4 border-brand-navy/20 pl-3 text-sm italic text-brand-navy/70">
            "{engagement.buyer_notes}"
          </div>
        )}
        <div className="mt-6 grid gap-4">
          <label><div className="pmc-label">Quoted amount</div>
            <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                   data-testid="engagement-quote-amount"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/></label>
          <label><div className="pmc-label">Currency</div>
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}
                    data-testid="engagement-quote-currency"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white font-mono">
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </select></label>
          <label><div className="pmc-label">Valid until (optional)</div>
            <input type="date" value={validUntil?.slice(0, 10) || ""}
                   onChange={(e) => setValidUntil(e.target.value)}
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/></label>
          <label><div className="pmc-label">Admin notes (buyer sees)</div>
            <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                      data-testid="engagement-quote-notes"
                      className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/></label>
        </div>
        <div className="mt-8 flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-5 py-2 border border-brand-navy/20 text-sm">Cancel</button>
          <button onClick={save} disabled={saving || !amount || Number(amount) <= 0}
                  data-testid="engagement-quote-save"
                  className="px-5 py-2 bg-brand-navy text-white text-xs uppercase tracking-widest disabled:opacity-50">
            {saving ? "Saving…" : "Save quote"}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ s }) {
  const cls = STATUS_STYLE[s] || "bg-brand-navy/5 border-brand-navy/20";
  return (
    <span className={`inline-block px-2 py-0.5 border text-[10px] uppercase tracking-widest ${cls}`}>
      {s?.replace(/_/g, " ")}
    </span>
  );
}

function EngagementRow({ e, onQuote, onInvoice, onCancel }) {
  return (
    <tr className="border-b border-brand-navy/10" data-testid={`engagement-row-${e.id}`}>
      <td className="px-3 py-3">
        <div className="text-sm font-semibold text-brand-navy">{e.product_name}</div>
        <div className="text-xs text-brand-navy/60 font-mono">{e.product_code}</div>
      </td>
      <td className="px-3 py-3 text-xs">
        <div>{e.buyer_email}</div>
        {e.buyer_company && <div className="text-brand-navy/60">{e.buyer_company}</div>}
      </td>
      <td className="px-3 py-3 text-center text-sm">{e.quantity}</td>
      <td className="px-3 py-3 text-right font-mono tabular-nums text-sm">
        {e.quoted_amount
          ? `${e.quoted_currency || "USD"} ${Number(e.quoted_amount).toLocaleString()}`
          : <span className="text-brand-navy/40">—</span>}
      </td>
      <td className="px-3 py-3"><StatusPill s={e.status}/></td>
      <td className="px-3 py-3 text-right space-x-2">
        {e.status === "quote_requested" && (
          <button onClick={() => onQuote(e)} data-testid={`engagement-set-quote-${e.id}`}
                  className="text-xs uppercase tracking-widest text-sky-800 hover:underline">Set quote</button>
        )}
        {e.status === "quoted" && (
          <>
            <button onClick={() => onQuote(e)} className="text-xs uppercase tracking-widest text-brand-navy hover:underline">Re-quote</button>
            <button onClick={() => onInvoice(e)} data-testid={`engagement-invoice-${e.id}`}
                    className="text-xs uppercase tracking-widest text-indigo-800 hover:underline font-semibold">Invoice</button>
          </>
        )}
        {e.status === "invoiced" && e.checkout_url && (
          <a href={e.checkout_url} target="_blank" rel="noreferrer"
             className="text-xs uppercase tracking-widest text-indigo-800 hover:underline">Pay-link</a>
        )}
        {!["paid", "cancelled"].includes(e.status) && (
          <button onClick={() => onCancel(e)} data-testid={`engagement-cancel-${e.id}`}
                  className="text-xs uppercase tracking-widest text-red-700 hover:underline">Cancel</button>
        )}
      </td>
    </tr>
  );
}

export default function EngagementsPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [quoting, setQuoting] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/engagements`, { credentials: "include" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(d.items);
    } catch (e) { toast.error(`Load failed: ${e.message}`); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const invoice = async (e) => {
    try {
      const r = await fetch(`${API}/api/v1/engagements/${e.id}/checkout`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ origin_url: window.location.origin }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      const d = await r.json();
      toast.success(`Invoice generated — pay-link ready`);
      if (window.confirm("Open the Stripe pay-link now?")) window.open(d.checkout_url, "_blank");
      reload();
    } catch (err) { toast.error(`Invoice failed: ${err.message}`); }
  };

  const cancel = async (e) => {
    if (!window.confirm(`Cancel engagement for ${e.product_name}?`)) return;
    try {
      const r = await fetch(`${API}/api/v1/engagements/${e.id}/cancel`, {
        method: "POST", credentials: "include",
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success("Cancelled");
      reload();
    } catch (err) { toast.error(`Cancel failed: ${err.message}`); }
  };

  const filtered = useMemo(
    () => (statusFilter === "all" ? items : items.filter((i) => i.status === statusFilter)),
    [items, statusFilter],
  );

  const counts = useMemo(() => {
    const c = { all: items.length };
    for (const i of items) c[i.status] = (c[i.status] || 0) + 1;
    return c;
  }, [items]);

  return (
    <div className="space-y-6" data-testid="engagements-panel">
      <section>
        <div className="pmc-label">Quote & invoice pipeline</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">Engagements</h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-xl">
          Every "Request quote" click from the client / supplier purchase pages lands here. Set the amount,
          hit Invoice to generate a Stripe pay-link, and Track through to paid.
        </p>
      </section>

      <div className="flex flex-wrap gap-2 items-center">
        {["all", "quote_requested", "quoted", "invoiced", "paid", "cancelled"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
                  data-testid={`engagement-filter-${s}`}
                  className={`px-3 py-1.5 text-[11px] uppercase tracking-widest border ${
                    statusFilter === s ? "bg-brand-navy text-white border-brand-navy"
                      : "text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy"}`}>
            {s === "all" ? "All" : s.replace(/_/g, " ")} ({counts[s] || 0})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-brand-navy/60 py-10 text-center">Loading engagements…</div>
      ) : (
        <div className="border border-brand-navy/10 bg-white overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
              <tr>
                <th className="px-3 py-3 text-left">Product</th>
                <th className="px-3 py-3 text-left">Buyer</th>
                <th className="px-3 py-3 text-center">Qty</th>
                <th className="px-3 py-3 text-right">Quoted</th>
                <th className="px-3 py-3 text-left">Status</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <EngagementRow key={e.id} e={e} onQuote={setQuoting} onInvoice={invoice} onCancel={cancel}/>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="text-center py-10 text-brand-navy/60">
                  No engagements in this bucket yet.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {quoting && (
        <QuoteModal engagement={quoting}
                     onClose={() => setQuoting(null)}
                     onSaved={() => { setQuoting(null); reload(); }}/>
      )}
    </div>
  );
}
