import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { marketApi, mediaUrl } from "@/lib/marketApi";
import { api, showApiError } from "@/lib/api";

const BLANK = { title: "", subtitle: "", image_id: "", link_url: "", cta_label: "Learn more", starts_at: "", ends_at: "", sort: 0, is_active: true };
const toLocal = (iso) => (iso ? new Date(new Date(iso).getTime() - new Date(iso).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "");
const toIso = (v) => (v ? new Date(v).toISOString() : null);

function AdForm({ initial, onSaved, onCancel }) {
  const [f, setF] = useState({ ...BLANK, ...initial, starts_at: toLocal(initial?.starts_at), ends_at: toLocal(initial?.ends_at) });
  const [busy, setBusy] = useState(false);
  const ref = useRef();
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    try { set("image_id", (await marketApi.adImage(file)).id); } catch (e) { showApiError(e); }
    setBusy(false);
  };
  const save = async () => {
    try {
      await marketApi.saveAd(f.id, { ...f, sort: Number(f.sort) || 0, starts_at: toIso(f.starts_at), ends_at: toIso(f.ends_at), id: undefined, created_at: undefined, created_by: undefined, updated_at: undefined });
      toast.success("Advert saved"); onSaved();
    } catch (e) { showApiError(e); }
  };
  const inp = (k, ph, type = "text") => <input type={type} className="pmc-input w-full" placeholder={ph} value={f[k] ?? ""} onChange={(e) => set(k, e.target.value)} data-testid={`ad-f-${k}`} />;
  return (
    <div className="pmc-panel p-3 mt-2 grid gap-2 md:grid-cols-2" data-testid="ad-form">
      {inp("title", "Headline *")}{inp("subtitle", "Short line under the headline")}
      {inp("link_url", "Link: https://… or /page")}{inp("cta_label", "Button text")}
      <label className="text-xs">Show from{inp("starts_at", "", "datetime-local")}</label>
      <label className="text-xs">Show until (optional){inp("ends_at", "", "datetime-local")}</label>
      <label className="text-xs">Order (lower shows first){inp("sort", "0", "number")}</label>
      <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={f.is_active} onChange={(e) => set("is_active", e.target.checked)} data-testid="ad-f-active" /> Active</label>
      <div className="md:col-span-2 flex items-center gap-3">
        {f.image_id && <img src={mediaUrl(f.image_id)} alt="" className="w-32 h-24 object-cover rounded" data-testid="ad-f-preview" />}
        <button type="button" className="pmc-btn pmc-btn--secondary pmc-btn--sm" disabled={busy} onClick={() => ref.current?.click()} data-testid="ad-f-image-btn">{busy ? "Uploading…" : f.image_id ? "Replace image" : "Upload image"}</button>
        <span className="text-xs opacity-70">Shown at 4:3 (1200 × 900); images are centre-cropped to fit.</span>
        <input ref={ref} type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={(e) => { upload(e.target.files[0]); e.target.value = ""; }} data-testid="ad-f-image-input" />
      </div>
      <div className="md:col-span-2 flex gap-2">
        <button className="pmc-btn pmc-btn--primary pmc-btn--sm" disabled={f.title.trim().length < 2} onClick={save} data-testid="ad-save">Save advert</button>
        <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={onCancel} data-testid="ad-cancel">Cancel</button>
      </div>
    </div>);
}

export function HomeAdverts() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const load = () => marketApi.ads().then((r) => setItems(r.items)).catch(showApiError);
  useEffect(() => { load(); }, []);
  const remove = (id) => { if (window.confirm("Remove this advert from the home page?")) marketApi.removeAd(id).then(() => { toast.success("Advert removed"); load(); }).catch(showApiError); };
  return (
    <section className="mt-6" data-testid="home-adverts-admin">
      <div className="flex items-center gap-3"><b>Home page advert slot</b>
        {!edit && <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => setEdit({})} data-testid="ad-new">Add advert</button>}</div>
      <p className="text-xs opacity-70 mt-1">Shown beside the marketplace products on the home page. Several active adverts rotate every 7 seconds; with none, an "Advertise here" panel is shown.</p>
      {edit && <AdForm initial={edit} onSaved={() => { setEdit(null); load(); }} onCancel={() => setEdit(null)} />}
      {items.map((a) => (
        <div key={a.id} className="pmc-panel p-3 mt-2 flex flex-wrap items-center gap-3 text-sm" data-testid={`ad-row-${a.id}`}>
          {a.image_id && <img src={mediaUrl(a.image_id)} alt="" className="w-20 h-[60px] object-cover rounded" />}
          <div className="flex-1 min-w-[200px]"><b>{a.title}</b> <span className="text-xs opacity-70" data-testid={`ad-state-${a.id}`}>· {a.state || (a.is_active ? "active" : "off")}{a.ends_at ? ` · until ${new Date(a.ends_at).toLocaleDateString()}` : ""}</span><div className="text-xs opacity-70">{a.link_url}</div>
            <div className="text-xs mt-1" data-testid={`ad-stats-${a.id}`}><b>{a.views || 0}</b> saw it · <b>{a.clicks || 0}</b> clicked · {a.views ? ((100 * (a.clicks || 0)) / a.views).toFixed(1) : "0.0"}% click rate
              {" · "}<a href={marketApi.adStatsCsv(a.id)} className="underline" data-testid={`ad-report-${a.id}`}>Daily report (CSV)</a></div></div>
          <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => setEdit(a)} data-testid={`ad-edit-${a.id}`}>Edit</button>
          <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => remove(a.id)} data-testid={`ad-remove-${a.id}`}>Remove</button>
        </div>))}
    </section>);
}

function ReviewRow({ c, cats, reload }) {
  const [mode, setMode] = useState(null);
  const [name, setName] = useState(c.name);
  const [target, setTarget] = useState("");
  const go = (b) => marketApi.catReview(c.id, b).then((r) => { toast.success(`Done${r.listings_moved ? ` · ${r.listings_moved} listing(s) updated` : ""}`); reload(); }).catch(showApiError);
  const [q, setQ] = useState("");
  const shown = cats.filter((x) => x.id !== c.id && (!q || x.name.toLowerCase().includes(q.toLowerCase())));
  return (
    <div className="pmc-panel p-3 mt-2 text-sm" data-testid={`catrev-row-${c.id}`}>
      <div className="flex flex-wrap items-center gap-2">
        <b className="flex-1 min-w-[180px]">{c.name}</b>
        <span className="text-xs opacity-70">added by {c.added_by} · used by {c.listings} listing(s)</span>
        <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => go({ action: "approve" })} data-testid={`catrev-approve-${c.id}`}>Approve</button>
        <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => setMode(mode === "rename" ? null : "rename")} data-testid={`catrev-rename-${c.id}`}>Rename</button>
        <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => setMode(mode === "merge" ? null : "merge")} data-testid={`catrev-merge-${c.id}`}>Merge</button>
      </div>
      {mode === "rename" && <div className="flex gap-2 mt-2">
        <input className="pmc-input w-full" value={name} onChange={(e) => setName(e.target.value)} data-testid={`catrev-name-${c.id}`} />
        <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => go({ action: "rename", name })} data-testid={`catrev-rename-save-${c.id}`}>Save name</button>
      </div>}
      {mode === "merge" && <div className="flex flex-wrap gap-2 mt-2">
        <input className="pmc-input" placeholder="Search categories" value={q} onChange={(e) => setQ(e.target.value)} data-testid={`catrev-search-${c.id}`} />
        <select className="pmc-input flex-1 min-w-[200px]" value={target} onChange={(e) => setTarget(e.target.value)} data-testid={`catrev-target-${c.id}`}>
          <option value="">Merge into…</option>
          {shown.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
        </select>
        <button className="pmc-btn pmc-btn--primary pmc-btn--sm" disabled={!target} onClick={() => go({ action: "merge", target_id: target })} data-testid={`catrev-merge-save-${c.id}`}>Merge</button>
      </div>}
    </div>);
}

export function CategoryReviewQueue() {
  const [items, setItems] = useState(null);
  const [cats, setCats] = useState([]);
  const load = () => {
    marketApi.catQueue().then((r) => setItems(r.items)).catch(showApiError);
    api.get("/api/v1/masters/categories/public").then((r) => setCats(r.data || [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  return (
    <section className="mt-6" data-testid="category-review-queue">
      <b>New categories added by suppliers</b>
      <p className="text-xs opacity-70 mt-1">Approve keeps the name. Rename fixes spelling and updates every listing using it. Merge moves its listings into an existing category and switches the duplicate off.</p>
      {items && items.length === 0 && <p className="text-sm opacity-70 mt-2" data-testid="catrev-empty">Nothing to review.</p>}
      {(items || []).map((c) => <ReviewRow key={c.id} c={c} cats={cats} reload={load} />)}
    </section>);
}
