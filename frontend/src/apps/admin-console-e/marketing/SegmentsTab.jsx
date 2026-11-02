import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";
import UnspscMultiPicker from "@/components/UnspscMultiPicker";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const EMPTY = { name: "", audience: "vendor", countries: "", categories: [], sources: [] };

export const SegmentsTab = () => {
  const [rows, setRows] = useState([]);
  const [f, setF] = useState(EMPTY);
  const [size, setSize] = useState(null);
  const load = () => marketingApi.segments().then((r) => setRows(r.items || [])).catch(showApiError);
  useEffect(() => {
    load();
  }, []);
  const payload = () => ({ ...f, countries: f.countries.split(/[ ,]+/).filter(Boolean).map((c) => c.toUpperCase()) });
  useEffect(() => {
    const t = setTimeout(() => { marketingApi.previewSegment({ ...payload(), name: f.name || "preview" }).then((r) => setSize(r.size)).catch(() => {}); }, 300);
    return () => { clearTimeout(t); };
  }, [f]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    if (f.name.trim().length < 2) return toast.error("Give the list a name");
    try { await marketingApi.createSegment(payload()); toast.success("List saved"); setF(EMPTY); load(); } catch (e) { showApiError(e); }
  };
  const del = async (id) => { try { await marketingApi.deleteSegment(id); load(); } catch (e) { showApiError(e); } };
  const toggleSrc = (s) => setF({ ...f, sources: f.sources.includes(s) ? f.sources.filter((x) => x !== s) : [...f.sources, s] });
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]" data-testid="mkt-segments">
      <div className="border border-brand-navy/20 bg-white p-4 space-y-3">
        <div className="pmc-label">New contact list</div>
        <input className={inp + " w-full"} placeholder="List name, e.g. UK construction vendors" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="seg-name" />
        <select className={inp + " w-full"} value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })} data-testid="seg-audience">
          <option value="vendor">Vendors</option><option value="buyer">Buyers</option><option value="all">Vendors and buyers</option></select>
        <input className={inp + " w-full"} placeholder="Countries (blank = all), e.g. GB KZ IN" value={f.countries} onChange={(e) => setF({ ...f, countries: e.target.value })} data-testid="seg-countries" />
        <div className="text-xs text-brand-navy/60">Categories — UNSPSC (none = all)</div>
        <UnspscMultiPicker testidPrefix="seg-cats" value={f.categories.map((t) => ({ code: t, title: t }))}
          onChange={(v) => setF({ ...f, categories: v.map((x) => x.title) })} />
        <div className="flex gap-4 text-sm">
          {[["platform", "Platform users"], ["upload", "Uploaded"], ["manual", "Added by hand"]].map(([s, l]) => (
            <label key={s} className="flex gap-2 items-center"><input type="checkbox" checked={f.sources.includes(s)} onChange={() => toggleSrc(s)} data-testid={`seg-src-${s}`} />{l}</label>))}
        </div>
        <div className="text-sm" data-testid="seg-size">{size == null ? "…" : `${size} people can be emailed`}<span className="text-xs text-brand-navy/50"> (consented, not unsubscribed)</span></div>
        <button className="pmc-btn pmc-btn--primary" onClick={save} data-testid="seg-save">Save list</button>
      </div>
      <div className="space-y-2">
        {rows.map((s) => (
          <div key={s.id} className="border border-brand-navy/15 bg-white p-3 flex items-center gap-3" data-testid={`seg-row-${s.id}`}>
            <div className="flex-1">
              <div className="font-semibold">{s.name}</div>
              <div className="text-xs text-brand-navy/60">{s.audience} · {s.countries?.join(", ") || "all countries"} · {s.categories?.length ? s.categories.join(", ") : "all categories"}</div>
            </div>
            <div className="text-sm font-semibold" data-testid={`seg-row-size-${s.id}`}>{s.size}</div>
            <button className="text-xs text-red-700 underline" onClick={() => del(s.id)} data-testid={`seg-del-${s.id}`}>Delete</button>
          </div>))}
        {!rows.length && <div className="text-sm text-brand-navy/60 p-4 border border-dashed border-brand-navy/20">No lists yet.</div>}
      </div>
    </div>
  );
};
