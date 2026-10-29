import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { feeTypesApi, publicApi, mastersApi, showApiError } from "@/lib/api";
import { CategoryPicker } from "./CategoryPicker";

const EMPTY = { name: "", code: "", timing: "upfront", calc: "fixed", amount_mode: "single",
  category_scope: "all", billing: "one_time", used_in_tender_builder: false, is_active: true, description: "",
  country_scope: "all", countries: [], categories: [] };

const OPTS = {
  timing: [["upfront", "At the beginning (before work starts)"], ["on_completion", "At the end (before submitting)"]],
  calc: [["fixed", "Fixed amount"], ["percentage", "Percentage of tender value"], ["either", "Fixed or % (per range)"]],
  amount_mode: [["single", "One amount"], ["range", "Range by tender value"]],
  category_scope: [["all", "All categories"], ["selected", "Selected categories"]],
  billing: [["one_time", "One-time (per tender / per event)"], ["yearly", "Yearly (access)"]],
};
const label = (k, v) => (OPTS[k].find(([x]) => x === v) || [v, v])[1];

const Choice = ({ k, form, setForm }) => (
  <div>
    <div className="pmc-label mb-1">{{ timing: "When is payment taken", calc: "Fixed or percentage", amount_mode: "Amount", category_scope: "Categories", billing: "Billing" }[k]}</div>
    <div className="flex flex-col gap-1">
      {OPTS[k].map(([v, l]) => (
        <label key={v} className="text-sm flex items-center gap-2">
          <input type="radio" name={k} checked={form[k] === v} onChange={() => setForm({ ...form, [k]: v, ...(k === "category_scope" && v === "all" ? { categories: [] } : {}) })} data-testid={`ft-${k}-${v}`} /> {l}
        </label>
      ))}
    </div>
  </div>
);

export default function FeeTypesPanel() {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [allCountries, setAllCountries] = useState([]);
  useEffect(() => { publicApi.countries().then((c) => setAllCountries((c || []).map((x) => Array.isArray(x) ? { code: x[0], name: x[1] } : { code: x.code || x.iso || x.value, name: x.name || x.label || x.code }))).catch(() => {}); }, []);
  const [cats, setCats] = useState([]);
  useEffect(() => { mastersApi.listCategories({ limit: 500 }).then((c) => setCats(Array.isArray(c) ? c : (c.items || []))).catch(() => {}); }, []);
  const load = useCallback(() => feeTypesApi.list().then(setRows).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.name.trim()) return toast.error("Name is required");
    try {
      if (editing === "new") await feeTypesApi.create(form); else await feeTypesApi.update(editing, form);
      toast.success("Fee type saved"); setEditing(null); load();
    } catch (e) { showApiError(e); }
  };
  const remove = async (r) => {
    if (!window.confirm(`Delete fee type "${r.name}"?`)) return;
    try { await feeTypesApi.remove(r.id); toast.success("Deleted"); load(); } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="fee-types-panel">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-sm text-brand-navy/60">Each fee type decides how its fee rules behave. Prices are set per country in <b>Fee rules</b>.</div>
        <button onClick={() => { setForm(EMPTY); setEditing("new"); }} data-testid="ft-new-btn"
          className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white">New fee type</button>
      </div>
      {editing && (
        <div className="bg-white border border-brand-navy/20 p-4 mb-4" data-testid="ft-form">
          <div className="grid gap-3 md:grid-cols-3 mb-4">
            <label><span className="pmc-label">Name *</span>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="ft-name"
                className="mt-1 w-full px-3 py-2 border border-brand-navy/20" placeholder="e.g. Tender management fee" /></label>
            <label className="md:col-span-2"><span className="pmc-label">Description</span>
              <input value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="ft-description"
                className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
          </div>
          <div className="grid gap-4 md:grid-cols-5">
            {["timing", "calc", "amount_mode", "category_scope", "billing"].map((k) => <Choice key={k} k={k} form={form} setForm={setForm} />)}
          </div>
          {form.category_scope === "selected" && (
            <div className="mt-4" data-testid="ft-categories">
              <div className="pmc-label mb-1">Which categories (rules start with these ticked)</div>
              <CategoryPicker categories={cats} value={form.categories || []} onChange={(v) => setForm({ ...form, categories: v })} />
            </div>
          )}
          <div className="mt-4" data-testid="ft-country-scope">
            <div className="pmc-label mb-1">Countries</div>
            <div className="flex gap-4 text-sm mb-2">
              <label className="flex items-center gap-2"><input type="radio" checked={form.country_scope !== "selected"} onChange={() => setForm({ ...form, country_scope: "all", countries: [] })} data-testid="ft-country_scope-all" /> All countries</label>
              <label className="flex items-center gap-2"><input type="radio" checked={form.country_scope === "selected"} onChange={() => setForm({ ...form, country_scope: "selected" })} data-testid="ft-country_scope-selected" /> Selected countries</label>
            </div>
            {form.country_scope === "selected" && (
              <div className="max-h-40 overflow-y-auto border border-brand-navy/20 p-2 grid gap-1 md:grid-cols-4">
                {allCountries.map((c) => (
                  <label key={c.code} className="text-sm flex items-center gap-2">
                    <input type="checkbox" checked={(form.countries || []).includes(c.code)} data-testid={`ft-country-${c.code}`}
                      onChange={() => setForm({ ...form, countries: (form.countries || []).includes(c.code) ? form.countries.filter((x) => x !== c.code) : [...(form.countries || []), c.code] })} /> {c.name}
                  </label>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-6 mt-4 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.used_in_tender_builder} data-testid="ft-tender-builder"
              onChange={(e) => setForm({ ...form, used_in_tender_builder: e.target.checked })} /> Charge this in the vendor Tender Builder</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} data-testid="ft-active"
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active</label>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setEditing(null)} data-testid="ft-cancel" className="px-4 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/30">Cancel</button>
            <button onClick={save} data-testid="ft-save" className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white">Save</button>
          </div>
        </div>
      )}
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10" data-testid="ft-list">
        {rows.map((r) => (
          <div key={r.id} className="p-4 flex justify-between gap-3 flex-wrap" data-testid={`ft-row-${r.code}`}>
            <div>
              <div className="text-sm font-semibold text-brand-navy">{r.name} <span className="font-mono font-normal text-brand-navy/40 text-xs">{r.code}</span>
                {r.used_in_tender_builder && <span className="ml-2 text-[10px] uppercase tracking-widest bg-emerald-100 text-emerald-800 px-1.5 py-0.5">Tender Builder</span>}
                {!r.is_active && <span className="ml-2 text-red-700 text-xs font-semibold">INACTIVE</span>}</div>
              <div className="text-xs text-brand-navy/60 mt-1">
                {label("timing", r.timing)} · {label("calc", r.calc)} · {label("amount_mode", r.amount_mode)} · {r.category_scope === "selected" && r.categories?.length ? `Categories: ${r.categories.join(", ")}` : label("category_scope", r.category_scope)} · {label("billing", r.billing)} · {r.country_scope === "selected" ? `Countries: ${(r.countries || []).join(", ") || "none"}` : "All countries"}
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => { setForm({ ...EMPTY, ...r }); setEditing(r.id); }} data-testid={`ft-edit-${r.code}`}
                className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30">Edit</button>
              <button onClick={() => remove(r)} data-testid={`ft-delete-${r.code}`}
                className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-red-300 text-red-700">Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
