import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { growthApi } from "@/lib/growthApi";

export default function SupplierDirectoryE() {
  useSeo({ title: "Supplier directory | Global Tender Grid", description: "Find KYC-checked suppliers registered on the PMC Managers Global Tender Grid by country and category." });
  const [f, setF] = useState({ q: "", country: "", category: "" });
  const [d, setD] = useState({ items: [], total: 0 });
  useEffect(() => {
    const t = setTimeout(() => growthApi.directory(Object.fromEntries(Object.entries(f).filter(([, v]) => v))).then(setD).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [f]);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <PublicChrome testid="supplier-directory-page">
      <div className="pmc-wrap py-10">
        <div className="pmc-eyebrow">Global Tender Grid</div>
        <h1 className="text-4xl sm:text-5xl font-semibold mt-1">Supplier directory</h1>
        <p className="mt-2 max-w-2xl text-sm">Suppliers registered on PMC who chose to be listed. <Link to="/register" className="underline">Register as a supplier</Link> to appear here.</p>
        <div className="grid md:grid-cols-3 gap-2 mt-6">
          <input className="pmc-input" placeholder="Company, headline or category" value={f.q} onChange={up("q")} data-testid="directory-search" />
          <input className="pmc-input" placeholder="Country code (e.g. MY)" maxLength={2} value={f.country} onChange={up("country")} data-testid="directory-country" />
          <input className="pmc-input" placeholder="Category" value={f.category} onChange={up("category")} data-testid="directory-category" />
        </div>
        <div className="text-sm opacity-70 mt-4" data-testid="directory-total">{d.total} suppliers</div>
        <div className="grid md:grid-cols-3 gap-3 mt-3" data-testid="directory-list">
          {!d.items.length && <div className="text-sm opacity-70" data-testid="directory-empty">No suppliers listed yet.</div>}
          {d.items.map((v) => (
            <Link key={v.vendor_ref} to={`/vendors/${v.vendor_ref}`} className={`block bg-white p-4 border ${v.featured ? "border-[#B8963E] border-2" : "border-black/10"}`} data-testid={`directory-item-${v.vendor_ref}`}>
              {v.featured && <span className="text-[10px] uppercase tracking-widest font-semibold text-[#9A7B2F]" data-testid={`directory-featured-${v.vendor_ref}`}>Featured</span>}
              <div className="font-semibold">{v.company_name}</div>
              {v.headline && <div className="text-sm mt-1">{v.headline}</div>}
              <div className="text-xs opacity-70 mt-1">{v.country || "—"} · {(v.categories || []).slice(0, 3).join(", ")}</div>
              {v.kyc_verified && <div className="text-xs text-emerald-700 mt-1">KYC verified</div>}
            </Link>))}
        </div>
      </div>
    </PublicChrome>);
}
