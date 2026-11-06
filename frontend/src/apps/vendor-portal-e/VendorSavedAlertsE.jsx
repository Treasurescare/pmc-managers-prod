import { useEffect, useState } from "react";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

const BLANK = { name: "", keywords: "", countries: "", categories: "", min_value: "", max_value: "", frequency: "daily", include_global: true, is_active: true };
const split = (s) => String(s || "").split(",").map((x) => x.trim()).filter(Boolean);
const toForm = (a) => ({ ...a, keywords: (a.keywords || []).join(", "), countries: (a.countries || []).join(", "), categories: (a.categories || []).join(", "),
  min_value: a.min_value ?? "", max_value: a.max_value ?? "" });

const AlertForm = ({ init, onSaved, onCancel }) => {
  const [f, setF] = useState(init);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = async () => {
    const b = { ...f, keywords: split(f.keywords), countries: split(f.countries).map((c) => c.toUpperCase()), categories: split(f.categories),
      min_value: f.min_value === "" ? null : Number(f.min_value), max_value: f.max_value === "" ? null : Number(f.max_value) };
    try { if (f.id) await growthApi.updateAlert(f.id, b); else await growthApi.createAlert(b); toast.success("Alert saved"); onSaved(); } catch (e) { showApiError(e); }
  };
  const inp = "pmc-input mt-1 w-full";
  return (
    <section className="pmc-panel p-4 mb-4 grid md:grid-cols-3 gap-3 text-sm" data-testid="alert-form">
      <label>Alert name<input className={inp} value={f.name} onChange={up("name")} data-testid="alert-name" /></label>
      <label>Keywords (comma separated)<input className={inp} value={f.keywords} onChange={up("keywords")} placeholder="solar, hospital" data-testid="alert-keywords" /></label>
      <label>Countries (2-letter codes)<input className={inp} value={f.countries} onChange={up("countries")} placeholder="IN, MY, KZ" data-testid="alert-countries" /></label>
      <label>Categories<input className={inp} value={f.categories} onChange={up("categories")} placeholder="Construction" data-testid="alert-categories" /></label>
      <label>Minimum value<input type="number" className={inp} value={f.min_value} onChange={up("min_value")} data-testid="alert-min" /></label>
      <label>Maximum value<input type="number" className={inp} value={f.max_value} onChange={up("max_value")} data-testid="alert-max" /></label>
      <label>How often<select className={inp} value={f.frequency} onChange={up("frequency")} data-testid="alert-frequency">
        <option value="instant">Instantly (PMC tenders)</option><option value="daily">Daily digest</option><option value="weekly">Weekly digest</option></select></label>
      <label className="flex items-center gap-2 mt-5"><input type="checkbox" checked={f.include_global} onChange={up("include_global")} data-testid="alert-global" />Include global tenders (World Bank, EU TED…)</label>
      <label className="flex items-center gap-2 mt-5"><input type="checkbox" checked={f.is_active} onChange={up("is_active")} data-testid="alert-active" />Active</label>
      <div className="md:col-span-3 flex gap-2 justify-end">
        <button className="pmc-btn pmc-btn--ghost" onClick={onCancel} data-testid="alert-cancel">Cancel</button>
        <button className="pmc-btn pmc-btn--primary" onClick={save} data-testid="alert-save">Save alert</button>
      </div>
    </section>);
};

export default function VendorSavedAlertsE() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [prev, setPrev] = useState(null);
  const load = () => growthApi.alerts().then((r) => setItems(r.items)).catch(showApiError);
  useEffect(() => { load(); }, []);
  const del = (id) => growthApi.deleteAlert(id).then(load).catch(showApiError);
  const preview = (id) => growthApi.previewAlert(id).then((r) => setPrev({ id, items: r.items })).catch(showApiError);
  return (
    <VendorPortalChrome active="/vendor/saved-alerts">
      <div className="sp-head"><div><div className="pmc-eyebrow">Tender alerts</div><h1>My saved alerts</h1></div>
        <button className="pmc-btn pmc-btn--primary" onClick={() => setEdit(BLANK)} data-testid="alert-new-btn">New alert</button></div>
      {edit && <AlertForm init={edit} onSaved={() => { setEdit(null); load(); }} onCancel={() => setEdit(null)} />}
      <section className="pmc-panel" data-testid="alert-list">
        {!items.length && <div className="p-4 text-sm opacity-70" data-testid="alert-empty">No saved alerts yet. Create one to get matching tenders by email.</div>}
        {items.map((a) => (
          <div key={a.id} className="p-4 border-b border-black/5" data-testid={`alert-row-${a.id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <b className="flex-1">{a.name} {!a.is_active && <span className="text-xs opacity-60">(paused)</span>}</b>
              <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" onClick={() => preview(a.id)} data-testid={`alert-preview-${a.id}`}>Preview matches</button>
              <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" onClick={() => setEdit(toForm(a))} data-testid={`alert-edit-${a.id}`}>Edit</button>
              <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" onClick={() => del(a.id)} data-testid={`alert-delete-${a.id}`}>Delete</button>
            </div>
            <div className="text-xs opacity-70 mt-1">{a.frequency} · {[a.keywords?.join(", "), a.countries?.join(" "), a.categories?.join(", ")].filter(Boolean).join(" · ") || "all tenders"}</div>
            {prev?.id === a.id && <ul className="text-sm mt-2 list-disc pl-5" data-testid={`alert-preview-list-${a.id}`}>
              {!prev.items.length && <li>No current matches.</li>}
              {prev.items.map((t, i) => <li key={i}><a className="underline" href={t.url} target={t.source === "PMC" ? undefined : "_blank"} rel="noreferrer">{t.title}</a> · {t.source} · {t.country || ""}</li>)}
            </ul>}
          </div>))}
      </section>
    </VendorPortalChrome>);
}
