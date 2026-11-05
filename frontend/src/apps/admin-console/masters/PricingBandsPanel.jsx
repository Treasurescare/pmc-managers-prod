import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { pricingApi, showApiError } from "@/lib/api";

const inp = "mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const btn = "px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5";

const BandForm = ({ band, onSaved, onCancel }) => {
  const [f, setF] = useState({ ...band, countries: (band.countries || []).join(", ") });
  const save = async () => {
    const p = { name: f.name, code: f.code, is_active: !!f.is_active, award_payer_default: f.award_payer_default,
      supplier_fees_default: f.supplier_fees_default, notes: f.notes || null,
      countries: f.countries.split(/[\s,]+/).filter(Boolean) };
    try {
      if (band.code) await pricingApi.updateBand(band.code, p); else await pricingApi.createBand(p);
      toast.success("Band saved"); onSaved();
    } catch (e) { showApiError(e); }
  };
  return (
    <div className="bg-white border border-brand-navy/20 p-4 mb-3 grid gap-3 md:grid-cols-4" data-testid="band-form">
      <label><span className="pmc-label">Band name</span>
        <input className={inp} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="band-name" /></label>
      <label><span className="pmc-label">Award fee paid by (default)</span>
        <select className={inp} value={f.award_payer_default} onChange={(e) => setF({ ...f, award_payer_default: e.target.value })} data-testid="band-award-payer">
          <option value="buyer">Buyer</option><option value="supplier">Winning supplier</option></select></label>
      <label><span className="pmc-label">Supplier fees (default)</span>
        <select className={inp} value={f.supplier_fees_default} onChange={(e) => setF({ ...f, supplier_fees_default: e.target.value })} data-testid="band-supplier-default">
          <option value="charge">Charge</option><option value="waive">Waive (suppliers bid free)</option></select></label>
      <label className="flex items-end gap-2 pb-2"><input type="checkbox" checked={!!f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} data-testid="band-active" />
        <span className="text-sm">Active</span></label>
      <label className="md:col-span-4"><span className="pmc-label">Countries (2-letter codes, comma separated)</span>
        <textarea rows={2} className={inp} value={f.countries} onChange={(e) => setF({ ...f, countries: e.target.value })} data-testid="band-countries" /></label>
      <div className="md:col-span-4 flex justify-end gap-2">
        <button className={btn} onClick={onCancel} data-testid="band-cancel">Cancel</button>
        <button className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white" onClick={save} data-testid="band-save">Save band</button>
      </div>
    </div>);
};

const Tiers = ({ tiers, onSaved }) => {
  const [v, setV] = useState(tiers.join(", "));
  useEffect(() => { setV(tiers.join(", ")); }, [tiers]);
  const save = () => pricingApi.setTiers(v.split(",").map((x) => x.trim()).filter(Boolean))
    .then(() => { toast.success("Tiers saved"); onSaved(); }).catch(showApiError);
  return (
    <div className="bg-white border border-brand-navy/10 p-4 mt-4 flex flex-wrap items-end gap-2" data-testid="tiers-editor">
      <label className="flex-1 min-w-[260px]"><span className="pmc-label">Buyer tiers (used to pick tier-specific fee rules)</span>
        <input className={inp} value={v} onChange={(e) => setV(e.target.value)} data-testid="tiers-input" /></label>
      <button className={btn} onClick={save} data-testid="tiers-save">Save tiers</button>
    </div>);
};

export default function PricingBandsPanel() {
  const [data, setData] = useState({ bands: [], tiers: [] });
  const [edit, setEdit] = useState(null);
  const load = useCallback(() => pricingApi.bands().then(setData).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const blank = { name: "", countries: [], is_active: true, award_payer_default: "buyer", supplier_fees_default: "charge" };
  return (
    <div data-testid="pricing-bands-panel">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-sm text-brand-navy/60 max-w-2xl">Countries are grouped into pricing bands. In Fee rules, a rule can apply to all countries, to a band, or to individual countries — a country rule always beats its band rule.</div>
        <button className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white" onClick={() => setEdit(blank)} data-testid="band-new-btn">New band</button>
      </div>
      {edit && <BandForm band={edit} onSaved={() => { setEdit(null); load(); }} onCancel={() => setEdit(null)} />}
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10" data-testid="band-list">
        {data.bands.map((b) => (
          <div key={b.code} className="p-4 flex items-start justify-between gap-3 flex-wrap" data-testid={`band-row-${b.code}`}>
            <div className="min-w-0 max-w-3xl">
              <div className="text-sm font-semibold text-brand-navy">{b.name} {!b.is_active && <span className="text-red-700 text-xs ml-2">INACTIVE</span>}</div>
              <div className="text-xs text-brand-navy/60 mt-0.5">Award fee paid by {b.award_payer_default === "supplier" ? "winning supplier" : "buyer"} · supplier fees: {b.supplier_fees_default}</div>
              <div className="text-xs font-mono text-brand-navy/70 mt-1 break-words">{(b.countries || []).join(" ") || "no countries"}</div>
            </div>
            <button className={btn} onClick={() => setEdit(b)} data-testid={`band-edit-${b.code}`}>Edit</button>
          </div>))}
      </div>
      <Tiers tiers={data.tiers} onSaved={load} />
    </div>);
}
