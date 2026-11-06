import { useEffect, useState } from "react";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";
import { growthApi, payNeeded } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

export default function VendorListingE() {
  const [f, setF] = useState(null);
  const [price, setPrice] = useState(null);
  const load = () => growthApi.myListing().then(setF).catch(showApiError);
  useEffect(() => { load(); growthApi.aiPrices().then((p) => setPrice(p.featured_listing)).catch(() => {}); }, []);
  if (!f) return <VendorPortalChrome active="/vendor/listing"><div className="p-4">Loading…</div></VendorPortalChrome>;
  const up = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = () => growthApi.setMyListing({ listed: !!f.listed, headline: f.headline || null, description: f.description || null, website: f.website || null })
    .then((r) => { setF(r); toast.success("Directory listing saved"); }).catch(showApiError);
  const feature = () => growthApi.buyFeature().then(() => { toast.success("You are featured for 30 days"); load(); }).catch((e) => {
    const p = payNeeded(e);
    if (p) window.location.href = p.checkout_url;
    else if (e?.response?.status === 409) toast.info(e.response.data?.detail || "Featured listings are not on sale right now.");
    else showApiError(e);
  });
  return (
    <VendorPortalChrome active="/vendor/listing">
      <div className="sp-head"><div><div className="pmc-eyebrow">Supplier directory</div><h1>My directory listing</h1></div>
        <a className="pmc-btn pmc-btn--ghost" href="/suppliers/directory" data-testid="listing-view-public">View directory</a></div>
      <section className="pmc-panel p-4 grid gap-3 text-sm" data-testid="listing-form">
        <label className="flex items-center gap-2"><input type="checkbox" checked={!!f.listed} onChange={up("listed")} data-testid="listing-listed" />
          Show my company in the public supplier directory (company name, country, categories and KYC status)</label>
        <label>Headline<input className="pmc-input mt-1 w-full" maxLength={120} value={f.headline || ""} onChange={up("headline")} data-testid="listing-headline" /></label>
        <label>About us<textarea rows={4} className="pmc-input mt-1 w-full" maxLength={1500} value={f.description || ""} onChange={up("description")} data-testid="listing-description" /></label>
        <label>Website<input className="pmc-input mt-1 w-full" value={f.website || ""} onChange={up("website")} placeholder="https://" data-testid="listing-website" /></label>
        <div><button className="pmc-btn pmc-btn--primary" onClick={save} data-testid="listing-save">Save listing</button></div>
      </section>
      <section className="pmc-panel p-4 mt-4 text-sm" data-testid="listing-feature">
        <div className="pmc-eyebrow">Premium visibility</div>
        <p className="mt-1">Featured suppliers appear first in the directory with a Featured badge for 30 days.
          {f.featured_until && f.featured ? ` Featured until ${String(f.featured_until).slice(0, 10)}.` : ""}</p>
        <button className="pmc-btn pmc-btn--secondary mt-2" disabled={!f.listed} onClick={feature} data-testid="listing-feature-btn">
          {price?.amount ? `Get featured — ${price.currency} ${price.amount}` : "Get featured"}</button>
        {!f.listed && <div className="text-xs opacity-60 mt-1">Turn on your listing first.</div>}
      </section>
    </VendorPortalChrome>);
}
