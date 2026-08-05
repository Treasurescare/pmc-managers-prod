/**
 * PurchaseGrid — shared, reusable component that renders the public product
 * catalog for either side (client or supplier). Handles filtering by
 * category, computes the display price per pricing model, and wires up a
 * Stripe Checkout button that never trusts the browser with amounts.
 */
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

const MODEL_LABEL = {
  fixed: "One-off", range: "Quote", percentage: "% of value",
  monthly: "per month", annual: "per year",
  per_delegate: "per delegate", per_user_monthly: "per user / mo",
  cost_recovery: "at cost", package: "package",
};

function fmtMoney(v, curr) {
  if (v == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: curr || "USD", maximumFractionDigits: 0,
    }).format(v);
  } catch { return `${curr || ""} ${Number(v).toLocaleString()}`; }
}

function priceDisplay(p) {
  if (p.pricing_model === "percentage")
    return { main: `${p.percentage}%`, sub: `of ${p.percentage_of || "value"}` };
  if (p.pricing_model === "range")
    return { main: `${fmtMoney(p.min_amount, p.currency)} – ${fmtMoney(p.max_amount, p.currency)}`, sub: "quoted" };
  if (p.pricing_model === "cost_recovery")
    return { main: "At cost", sub: "invoiced on delivery" };
  const suffix = MODEL_LABEL[p.pricing_model] || "";
  return { main: fmtMoney(p.amount, p.currency), sub: suffix };
}

function ProductCard({ p, onBuy, working }) {
  const price = priceDisplay(p);
  const isQuote = ["range", "percentage", "cost_recovery"].includes(p.pricing_model);
  return (
    <div className="border border-brand-navy/15 bg-white p-6 flex flex-col justify-between"
         data-testid={`purchase-card-${p.code}`}>
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="pmc-label">{p.category}{p.package_tier ? ` · ${p.package_tier}` : ""}</div>
          <span className="text-[10px] uppercase tracking-widest text-brand-navy/50 font-mono">{p.code}</span>
        </div>
        <h3 className="font-display text-xl text-brand-navy mt-2 leading-snug">{p.name}</h3>
        <p className="text-sm text-brand-navy/70 mt-3 leading-6">{p.description}</p>
        {p.conditions && (
          <p className="text-xs text-brand-navy/50 mt-3 italic leading-relaxed">
            {p.conditions}
          </p>
        )}
      </div>
      <div className="mt-6 border-t border-brand-navy/10 pt-4 flex items-end justify-between gap-3">
        <div>
          <div className="font-display text-2xl text-brand-navy tabular-nums">{price.main}</div>
          <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">{price.sub}</div>
        </div>
        <button onClick={() => onBuy(p)} disabled={working === p.code}
                data-testid={`purchase-buy-${p.code}`}
                className={`px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border-2 transition-colors ${
                  isQuote
                    ? "border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white"
                    : "border-brand-navy bg-brand-navy text-white hover:bg-brand-navy-deep"
                } disabled:opacity-50`}>
          {working === p.code ? "…" : (isQuote ? "Request quote" : "Subscribe")}
        </button>
      </div>
    </div>
  );
}

export default function PurchaseGrid({ side, title, kicker }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [working, setWorking] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${API}/api/v1/products/public?side=${side}`)
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setItems(d.items || []); })
      .catch((e) => toast.error(`Catalog load failed: ${e.message}`))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [side]);

  const categories = useMemo(() => Array.from(new Set(items.map((i) => i.category).filter(Boolean))).sort(), [items]);
  const filtered = useMemo(
    () => (category === "all" ? items : items.filter((i) => i.category === category)),
    [items, category],
  );

  const startCheckout = async (p) => {
    const isQuote = ["range", "percentage", "cost_recovery"].includes(p.pricing_model);
    if (isQuote) {
      toast.info(`Quote request recorded for ${p.name}. Our team will contact you.`);
      // Stub — record the quote request server-side in a future wave.
      try {
        await fetch(`${API}/api/v1/audit/note`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ event: "quote_request", product_code: p.code }),
        }).catch(() => {});
      } catch { /* non-blocking */ }
      return;
    }
    setWorking(p.code);
    try {
      const r = await fetch(`${API}/api/v1/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          product_code: p.code, quantity: 1,
          origin_url: window.location.origin,
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      const d = await r.json();
      if (d.checkout_url) window.location.href = d.checkout_url;
      else throw new Error("No checkout URL returned");
    } catch (e) {
      toast.error(`Checkout failed: ${e.message}`);
    } finally {
      setWorking(null);
    }
  };

  return (
    <section className="space-y-8" data-testid={`purchase-grid-${side}`}>
      <header>
        {kicker && <div className="pmc-label">{kicker}</div>}
        <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">{title}</h1>
      </header>

      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs uppercase tracking-widest text-brand-navy/60 mr-2">Filter:</span>
        <button onClick={() => setCategory("all")}
                data-testid="cat-all"
                className={`px-3 py-1.5 text-[11px] uppercase tracking-widest border ${category === "all" ? "bg-brand-navy text-white border-brand-navy" : "text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy"}`}>
          All ({items.length})
        </button>
        {categories.map((c) => {
          const n = items.filter((i) => i.category === c).length;
          return (
            <button key={c} onClick={() => setCategory(c)}
                    data-testid={`cat-${c.toLowerCase().replace(/\W+/g, "-")}`}
                    className={`px-3 py-1.5 text-[11px] uppercase tracking-widest border ${category === c ? "bg-brand-navy text-white border-brand-navy" : "text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy"}`}>
              {c} ({n})
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="text-brand-navy/60 py-10 text-center">Loading catalog…</div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((p) => (
            <ProductCard key={p.code} p={p} onBuy={startCheckout} working={working}/>
          ))}
        </div>
      )}
    </section>
  );
}
