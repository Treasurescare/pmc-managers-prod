import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Sparkles, Upload } from "lucide-react";
import { marketApi, mediaUrl } from "@/lib/marketApi";
import { payNeeded } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";
import { PhotoStrip } from "./MarketMediaPicker";
import { CategoryPicker } from "./MarketFormPickers";

const toItem = (p, i) => ({ key: i, include: true, title: p.title, aiText: p.description, description: p.description, ownText: false,
  category: p.category, unit: p.unit, specs: p.specs || [], addSpecs: (p.specs || []).length > 0, page: p.page, photos: p.photos || [], attachCat: true });

function ProductCard({ it, set, pageImages, hasCat }) {
  const others = pageImages.filter((im) => !it.photos.includes(im.id));
  return (
    <div className={`pmc-panel p-3 space-y-2 ${it.include ? "" : "opacity-50"}`} data-testid={`cat-item-${it.key}`}>
      <label className="flex items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={it.include} onChange={(e) => set({ include: e.target.checked })} data-testid={`cat-include-${it.key}`} />
        List this product <span className="text-xs opacity-60">(page {it.page})</span>
      </label>
      <input className="pmc-input w-full" value={it.title} onChange={(e) => set({ title: e.target.value })} data-testid={`cat-title-${it.key}`} />
      <div className="flex flex-wrap gap-3 text-xs">
        <label className="flex items-center gap-1"><input type="radio" checked={!it.ownText} onChange={() => set({ ownText: false, description: it.aiText })} data-testid={`cat-ai-text-${it.key}`} /> Use the AI description (you can edit it)</label>
        <label className="flex items-center gap-1"><input type="radio" checked={it.ownText} onChange={() => set({ ownText: true, description: "" })} data-testid={`cat-own-text-${it.key}`} /> Write my own</label>
      </div>
      <textarea className="pmc-input w-full !h-auto" rows={5} placeholder="Describe the product" value={it.description} onChange={(e) => set({ description: e.target.value })} data-testid={`cat-desc-${it.key}`} />
      {it.specs.length > 0 && <label className="flex items-start gap-2 text-xs">
        <input type="checkbox" checked={it.addSpecs} onChange={(e) => set({ addSpecs: e.target.checked })} data-testid={`cat-specs-${it.key}`} />
        <span>Add specifications: {it.specs.join(" · ")}</span></label>}
      <div className="grid grid-cols-2 gap-2">
        <CategoryPicker value={it.category} onChange={(v) => set({ category: v })} testid={`cat-category-${it.key}`} />
        <input className="pmc-input" placeholder="Unit" value={it.unit} onChange={(e) => set({ unit: e.target.value })} data-testid={`cat-unit-${it.key}`} />
      </div>
      <div className="text-xs opacity-80">Photos for this listing (remove any you don't want, or upload your own)</div>
      <PhotoStrip photos={it.photos} onChange={(fn) => set((x) => ({ photos: fn(x.photos) }))} testid={`cat-photos-${it.key}`} />
      {others.length > 0 && <div>
        <div className="text-xs opacity-70">Other photos on this page — tap to add</div>
        <div className="flex flex-wrap gap-2 mt-1">{others.map((im) => (
          <button type="button" key={im.id} onClick={() => set({ photos: [...it.photos, im.id] })} data-testid={`cat-add-photo-${it.key}-${im.id}`}>
            <img src={mediaUrl(im.id)} alt="" className="w-14 h-14 object-cover rounded opacity-70 hover:opacity-100" /></button>))}</div>
      </div>}
      {hasCat && <label className="flex items-center gap-2 text-xs">
        <input type="checkbox" checked={it.attachCat} onChange={(e) => set({ attachCat: e.target.checked })} data-testid={`cat-attach-${it.key}`} /> Attach the catalogue PDF as a spec sheet</label>}
    </div>);
}

function ImportProgress({ job }) {
  const total = job.pages_total || 0;
  const done = job.pages_done || 0;
  const pct = job.status === "uploading" ? 3 : total ? Math.max(6, Math.round((100 * done) / total)) : 6;
  return (
    <div className="space-y-2" data-testid="cat-progress">
      <p className="text-sm">{job.status === "uploading" ? <>Uploading <b>{job.file_name}</b>…</> : total ? <>AI is reading pages {done + 1}–{Math.min(done + 15, total)} of {total} in <b>{job.file_name}</b>{job.found ? ` · ${job.found} product(s) found so far` : ""}</> : <>AI is reading <b>{job.file_name}</b>…</>}</p>
      <div className="h-2 rounded bg-black/10 overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full bg-emerald-700 transition-[width] duration-700" style={{ width: `${pct}%` }} data-testid="cat-progress-bar" />
      </div>
      <p className="text-xs opacity-70">Large catalogues are read 15 pages at a time (up to 200 pages). You can stay on this page.</p>
    </div>);
}

function EarlierImports({ onOpen }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { marketApi.imports().then((r) => setRows(r.items)).catch(() => {}); }, []);
  if (!rows.length) return null;
  const open = (id) => marketApi.getImport(id).then(onOpen).catch(showApiError);
  return (
    <div className="text-sm" data-testid="cat-earlier">
      <div className="font-medium mt-2">Or reopen an earlier import (no new upload, no new AI reading)</div>
      {rows.map((r) => (
        <button key={r.id} type="button" className="block underline text-left mt-1" onClick={() => open(r.id)} data-testid={`cat-earlier-${r.id}`}>
          {r.file_name} · {r.products} product(s) · {new Date(r.created_at).toLocaleDateString()}</button>))}
    </div>);
}

export default function CatalogueImportE({ onDone, onCancel }) {
  const ref = useRef();
  const [job, setJob] = useState(null);
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (job?.status !== "reading") return undefined;
    const t = setInterval(() => {
      marketApi.getImport(job.id).then((d) => {
        if (d.status !== "reading") { setJob(d); setItems((d.products || []).map(toItem)); if (d.status === "failed") toast.error(d.error); }
        else setJob((j) => ({ ...j, pages_total: d.pages_total, pages_done: d.pages_done, found: d.found }));
      }).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [job]);
  const start = async (file) => {
    if (!file) return;
    setJob({ status: "uploading", file_name: file.name });
    try { setJob({ ...(await marketApi.startImport(file)), file_name: file.name }); } catch (e) {
      setJob(null);
      const pay = payNeeded(e);
      if (pay?.checkout_url) toast(pay.message, { action: { label: "Pay", onClick: () => { window.location.href = pay.checkout_url; } } });
      else showApiError(e);
    }
  };
  const chosen = items.filter((x) => x.include);
  const save = async () => {
    setSaving(true);
    try {
      const r = await marketApi.bulk(chosen.map((x) => ({ title: x.title, category: x.category, unit: x.unit || "unit", photos: x.photos,
        description: x.addSpecs ? `${x.description}\n\nSpecifications:\n${x.specs.map((s) => `• ${s}`).join("\n")}`.trim() : x.description,
        documents: x.attachCat && job.catalogue_doc ? [job.catalogue_doc] : [] })));
      toast.success(`${r.created} draft listing(s) created — open Edit on each to set the price and how to sell`);
      onDone();
    } catch (e) { showApiError(e); }
    setSaving(false);
  };
  const upd = (k) => (patch) => setItems((xs) => xs.map((x) => (x.key === k ? { ...x, ...(typeof patch === "function" ? patch(x) : patch) } : x)));
  return (
    <section className="pmc-panel p-4 mt-4 space-y-3" data-testid="cat-import">
      <div className="flex items-center gap-2 font-semibold"><Sparkles size={16} /> Import products from a catalogue</div>
      <p className="text-sm opacity-80">Upload a PDF catalogue, brochure or a photo of a page. AI finds each product, its photo and a description. You then choose what to keep, edit the text or write your own, and pick the photos.</p>
      {!job && <div className="flex flex-wrap gap-2 items-center">
        <button type="button" className="pmc-btn pmc-btn--primary" onClick={() => ref.current?.click()} data-testid="cat-upload-btn"><Upload size={14} className="inline mr-1" />Choose catalogue</button>
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={onCancel} data-testid="cat-cancel">Cancel</button>
        <span className="text-xs opacity-70 w-full">PDF, JPG or PNG · max 25 MB · up to 200 pages</span>
      </div>}
      {!job && <EarlierImports onOpen={(d) => { setJob(d); setItems((d.products || []).map(toItem)); }} />}
      <input ref={ref} type="file" accept="application/pdf,image/jpeg,image/png" hidden onChange={(e) => start(e.target.files[0])} data-testid="cat-file-input" />
      {job && ["uploading", "reading"].includes(job.status) && <ImportProgress job={job} />}
      {job?.status === "failed" && <div className="flex gap-2 items-center text-sm" data-testid="cat-failed">{job.error}<button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => setJob(null)} data-testid="cat-retry">Try another file</button></div>}
      {job?.status === "done" && <>
        <p className="text-sm" data-testid="cat-found">Found <b>{items.length}</b> product(s) in {job.pages} page(s). Untick any you don't want.</p>
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((it) => <ProductCard key={it.key} it={it} set={upd(it.key)} hasCat={!!job.catalogue_doc} pageImages={(job.images || []).filter((im) => im.page === it.page)} />)}
        </div>
        <div className="flex gap-2 pb-14 md:pb-0">
          <button className="pmc-btn pmc-btn--primary" disabled={!chosen.length || saving} onClick={save} data-testid="cat-create-drafts">{saving ? "Creating…" : `Create ${chosen.length} draft listing(s)`}</button>
          <button className="pmc-btn pmc-btn--secondary" onClick={onCancel} data-testid="cat-close">Close</button>
        </div>
      </>}
    </section>);
}
