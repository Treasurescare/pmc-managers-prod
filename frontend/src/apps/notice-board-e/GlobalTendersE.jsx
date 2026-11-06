import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { growthApi } from "@/lib/growthApi";

export default function GlobalTendersE() {
  useSeo({ title: "Global tenders — World Bank, EU TED and more | Global Tender Grid", description: "Live international tenders collected from official open sources, with the original source, reference and link." });
  const [f, setF] = useState({ q: "", country: "", category: "", source: "" });
  const [d, setD] = useState({ items: [], total: 0, categories: [], sources: [] });
  const [page, setPage] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => {
      growthApi.globalTenders({ ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), limit: 30, offset: page * 30 }).then(setD).catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [f, page]);
  const up = (k) => (e) => { setPage(0); setF({ ...f, [k]: e.target.value }); };
  return (
    <PublicChrome active="global" testid="global-tenders-page">
      <div className="pmc-wrap py-10">
        <div className="pmc-eyebrow">Global Tender Grid</div>
        <h1 className="text-4xl sm:text-5xl font-semibold mt-1">Global tenders</h1>
        <p className="mt-2 max-w-2xl text-sm">International tenders collected from official open sources. Each one shows its original source and reference — bids are submitted on the source portal. <Link to="/tenders/all" className="underline">See tenders hosted on PMC</Link>.</p>
        <div className="grid md:grid-cols-4 gap-2 mt-6">
          <input className="pmc-input" placeholder="Search titles…" value={f.q} onChange={up("q")} data-testid="global-search" />
          <input className="pmc-input" placeholder="Country code (e.g. DE)" maxLength={2} value={f.country} onChange={up("country")} data-testid="global-country" />
          <select className="pmc-input" value={f.category} onChange={up("category")} data-testid="global-category"><option value="">All categories</option>{d.categories.map((c) => <option key={c}>{c}</option>)}</select>
          <select className="pmc-input" value={f.source} onChange={up("source")} data-testid="global-source"><option value="">All sources</option>{d.sources.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}</select>
        </div>
        <div className="text-sm opacity-70 mt-4" data-testid="global-total">{d.total.toLocaleString()} open tenders</div>
        <div className="mt-3 grid gap-2" data-testid="global-list">
          {d.items.map((t) => (
            <a key={`${t.source}-${t.ref}`} href={t.url} target="_blank" rel="noreferrer" className="block bg-white border border-black/10 p-4 hover:border-black/30" data-testid={`global-item-${t.ref}`}>
              <div className="font-semibold">{t.title}</div>
              <div className="text-xs opacity-70 mt-1">{t.buyer} · {t.country || t.country_name || "—"} · {t.category || "General"}{t.deadline ? ` · closes ${String(t.deadline).slice(0, 10)}` : ""}{t.value ? ` · ${t.currency || ""} ${Number(t.value).toLocaleString()}` : ""}</div>
              <div className="text-xs mt-1">Source: <b>{t.source_name}</b> · Ref {t.ref}{t.status === "amended" ? " · Amended" : ""}</div>
            </a>))}
        </div>
        <div className="flex gap-2 mt-4">
          <button className="pmc-btn pmc-btn--ghost" disabled={!page} onClick={() => setPage(page - 1)} data-testid="global-prev">Previous</button>
          <button className="pmc-btn pmc-btn--ghost" disabled={(page + 1) * 30 >= d.total} onClick={() => setPage(page + 1)} data-testid="global-next">Next</button>
        </div>
      </div>
    </PublicChrome>);
}
