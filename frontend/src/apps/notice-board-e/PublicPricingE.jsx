import { useEffect, useState } from "react";
import { feeTypesApi } from "@/lib/api";

const n = (v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
const WHEN = { upfront: "Paid before work starts", on_completion: "Paid on completion" };
const BILL = { one_time: "per tender / event", yearly: "per year" };
const COUNTRY = { IN: "India", GB: "United Kingdom", US: "United States", MY: "Malaysia" };
const cname = (c) => COUNTRY[c] || c;

const band = (s, cur) => {
  const lo = s.tender_value_min || 0;
  const hi = s.tender_value_max;
  if (!lo && !hi) return "Any tender value";
  return hi ? `${cur} ${n(lo)} – ${n(hi)}` : `Above ${cur} ${n(lo)}`;
};
const price = (s, cur) => (s.fee_type === "percentage"
  ? `${s.percentage}% of tender value${s.pct_min ? `, min ${cur} ${n(s.pct_min)}` : ""}${s.pct_max ? `, max ${cur} ${n(s.pct_max)}` : ""}`
  : `${cur} ${n(s.fixed_amount || 0)}`);

const Rule = ({ r }) => (
  <div className="py-3 border-t border-brand-navy/10" data-testid="pricing-rule">
    <div className="text-xs text-brand-navy/60">{r.countries.length ? r.countries.map(cname).join(", ") : "All countries"}{r.categories.length ? ` · ${r.categories.join(", ")}` : ""}</div>
    {r.progressive && <div className="text-[11px] text-brand-navy/60" data-testid="pricing-stepped">Stepped: each rate applies only to the part of the tender value inside its band.</div>}
    <table className="w-full text-sm mt-1"><tbody>{r.slabs.map((s, i) => (
      <tr key={i}><td className="py-1 pr-4 text-brand-navy/70">{band(s, r.currency)}</td><td className="py-1 font-semibold text-right">{price(s, r.currency)}</td></tr>))}</tbody></table>
  </div>);

const Fee = ({ f }) => (
  <div className="bg-white border border-brand-navy/15 p-6" data-testid={`pricing-fee-${f.code}`}>
    <h2 className="font-serif text-2xl text-brand-navy">{f.name}</h2>
    <div className="text-xs uppercase tracking-widest text-brand-gold mt-1">{WHEN[f.timing] || ""} · {BILL[f.billing] || ""}</div>
    {f.description && <p className="text-sm text-brand-navy/70 mt-2">{f.description}</p>}
    <div className="mt-3">{f.rules.length ? f.rules.map((r, i) => <Rule key={i} r={r} />) : <p className="text-sm text-brand-navy/60">Quoted per tender.</p>}</div>
  </div>);

export default function PublicPricingE() {
  const [d, setD] = useState(null);
  useEffect(() => { feeTypesApi.publicPricing().then(setD).catch(() => setD({ fees: [] })); }, []);
  return (
    <div className="min-h-screen bg-[#F3EFE4]" data-testid="pricing-page">
      <header className="bg-[#0F3B2E] text-[#F3EFE4]"><div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center flex-wrap gap-3">
        <a href="/" className="font-serif text-xl" data-testid="pricing-home">PMC Managers</a>
        <nav className="flex gap-5 text-sm"><a href="/">Tenders</a><a href="/trust">Trust &amp; security</a><a href="/help">Help</a><a href="/vendor/login">Sign in</a></nav>
      </div></header>
      <main className="max-w-6xl mx-auto px-6 py-14 space-y-8">
        <div><div className="text-xs uppercase tracking-widest text-brand-gold">Pricing</div>
          <h1 className="font-serif text-4xl sm:text-5xl text-brand-navy mt-2">What you pay, and when</h1>
          <p className="text-base text-brand-navy/70 mt-3 max-w-2xl">These figures come straight from the fee settings used to bill you, so the price here is the price charged. Taxes are added at the rate that applies in your country.</p></div>
        {!d ? <p className="text-sm">Loading…</p> : d.fees.length
          ? <div className="grid md:grid-cols-2 gap-5">{d.fees.map((f) => <Fee key={f.code} f={f} />)}</div>
          : <p className="text-sm text-brand-navy/70" data-testid="pricing-empty">Prices are being finalised. Contact tenders@pmcmanagers.com for a quote.</p>}
      </main>
    </div>);
}
