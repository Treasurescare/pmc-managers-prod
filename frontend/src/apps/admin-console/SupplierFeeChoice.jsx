import { useEffect, useState } from "react";
import { pricingApi } from "@/lib/api";

export const SupplierFeeChoice = ({ country, value, onChange }) => {
  const [d, setD] = useState(null);
  useEffect(() => {
    pricingApi.supplierDefaults(country).then((r) => {
      setD(r);
      onChange({ fees: Object.fromEntries(r.fees.map((f) => [f.code, f.default])), reason: "" });
    }).catch(() => setD(null));
  }, [country]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d || !value) return null;
  const waiving = Object.values(value.fees).includes("waive");
  return (
    <div className="w-full mb-3 border border-brand-navy/15 bg-brand-pale/40 p-3 text-xs" data-testid="supplier-fee-choice">
      <div className="pmc-label mb-1">Supplier fees for this vendor{d.band ? ` · ${d.band} band default` : ""}</div>
      {d.fees.map((f) => (
        <div key={f.code} className="flex flex-wrap items-center gap-3 py-1" data-testid={`supplier-fee-${f.code}`}>
          <span className="min-w-[200px]">{f.name}</span>
          {["charge", "waive"].map((opt) => (
            <label key={opt} className="flex items-center gap-1"><input type="radio" checked={value.fees[f.code] === opt}
              onChange={() => onChange({ ...value, fees: { ...value.fees, [f.code]: opt } })} data-testid={`supplier-fee-${f.code}-${opt}`} />
              {opt === "charge" ? "Charge" : "Waive"}</label>))}
        </div>))}
      {waiving && <input className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 bg-white" placeholder="Reason for waiving (required)"
        value={value.reason} onChange={(e) => onChange({ ...value, reason: e.target.value })} data-testid="supplier-fee-reason" />}
      <div className="text-brand-navy/50 mt-1">Charge keeps the usual rule: first category free, extra categories and document downloads priced by Fee rules.</div>
    </div>);
};
