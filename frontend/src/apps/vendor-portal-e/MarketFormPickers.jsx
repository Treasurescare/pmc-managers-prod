import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";
import { marketApi } from "@/lib/marketApi";
import { useCountries } from "@/components/CountryPicker";

let _cats = null;

export function CategoryPicker({ value, onChange, testid = "mkt-f-category" }) {
  const [cats, setCats] = useState(_cats || []);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  useEffect(() => {
    if (_cats) return;
    api.get("/api/v1/masters/categories/public").then((r) => { _cats = r.data || []; setCats(_cats); }).catch(() => {});
  }, []);
  const known = !value || cats.some((c) => c.name === value);
  const add = async () => {
    try {
      const r = await marketApi.addCategory(name.trim());
      if (!cats.some((c) => c.name === r.name)) { _cats = [...cats, { id: r.id, name: r.name }].sort((a, b) => a.name.localeCompare(b.name)); setCats(_cats); }
      onChange(r.name); setAdding(false); setName("");
      toast.success(r.created ? `"${r.name}" added to the category list` : `"${r.name}" is already in the list — selected`);
    } catch (e) { showApiError(e); }
  };
  if (adding) {
    return (
      <div className="flex gap-2" data-testid={`${testid}-add-box`}>
        <input className="pmc-input w-full" autoFocus placeholder="New category name" value={name} onChange={(e) => setName(e.target.value)} data-testid={`${testid}-new-name`} />
        <button type="button" className="pmc-btn pmc-btn--primary pmc-btn--sm" disabled={name.trim().length < 2} onClick={add} data-testid={`${testid}-new-save`}>Add</button>
        <button type="button" className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => setAdding(false)} data-testid={`${testid}-new-cancel`}>Cancel</button>
      </div>);
  }
  return (
    <div>
      <select className="pmc-input w-full" value={value || ""} onChange={(e) => (e.target.value === "__new" ? (setName(value && !known ? value : ""), setAdding(true)) : onChange(e.target.value))} data-testid={testid}>
        <option value="">Choose a category…</option>
        {!known && <option value={value}>{value} (not in the list yet)</option>}
        {cats.map((c) => <option key={c.id || c.name} value={c.name}>{c.name}</option>)}
        <option value="__new">+ Add a new category…</option>
      </select>
      {!known && <button type="button" className="text-xs underline mt-1" onClick={() => { setName(value); setAdding(true); }} data-testid={`${testid}-save-suggested`}>Add "{value}" to the category list</button>}
    </div>);
}

function useList(url) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    if (!url) { setRows([]); return; }
    api.get(url).then((r) => setRows(r.data || [])).catch(() => setRows([]));
  }, [url]);
  return rows;
}

export function LocationPicker({ f, setF }) {
  const countries = useCountries();
  const states = useList(f.country_code ? `/api/v1/masters/states?country_code=${f.country_code}` : null);
  const cities = useList(f.country_code ? `/api/v1/masters/cities?country_code=${f.country_code}${f.state_code ? `&state_code=${encodeURIComponent(f.state_code)}` : ""}&limit=500` : null);
  const meta = countries.find((c) => c.code === f.country_code);
  const patch = (p) => setF((x) => ({ ...x, ...p }));
  return (
    <div className="grid gap-2 grid-cols-2" data-testid="mkt-location">
      <select className="pmc-input" value={f.country_code || ""} onChange={(e) => patch({ country_code: e.target.value, state_code: "", state_name: "", city: "", zip: "" })} data-testid="mkt-f-country">
        <option value="">Country…</option>
        {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
      </select>
      <select className="pmc-input" value={f.state_code || ""} disabled={!states.length} onChange={(e) => patch({ state_code: e.target.value, state_name: states.find((s) => s.state_code === e.target.value)?.name || "", city: "" })} data-testid="mkt-f-state">
        <option value="">{states.length ? "State / province…" : "No states listed"}</option>
        {states.map((s) => <option key={s.state_code} value={s.state_code}>{s.name}</option>)}
      </select>
      <select className="pmc-input" value={f.city || ""} disabled={!cities.length} onChange={(e) => patch({ city: e.target.value })} data-testid="mkt-f-city">
        <option value="">{cities.length ? "City…" : "No cities listed"}</option>
        {f.city && !cities.some((c) => c.name === f.city) && <option value={f.city}>{f.city}</option>}
        {cities.map((c) => <option key={`${c.state_code}-${c.name}`} value={c.name}>{c.name}</option>)}
      </select>
      <input className="pmc-input" placeholder={meta?.postal_code_format ? `ZIP (${meta.postal_code_format})` : "ZIP / postal code"} value={f.zip || ""} onChange={(e) => patch({ zip: e.target.value })} data-testid="mkt-f-zip" />
    </div>);
}
