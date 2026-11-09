import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { coverOf, marketApi, mediaUrl, MODE_LABEL, money } from "@/lib/marketApi";

function priceLine(l) {
  if (l.sale_modes.includes("fixed") && l.buy_now_price) return `Buy now ${money(l.currency, l.buy_now_price)}`;
  if (l.sale_modes.includes("auction")) return l.top_bid ? `Top bid ${money(l.currency, l.top_bid)}` : `From ${money(l.currency, l.start_price)}`;
  return "Best offer";
}

function ProductTile({ l }) {
  return (
    <Link to={`/market/${l.id}`} className="pmc-card" style={{ display: "block", overflow: "hidden", textDecoration: "none", color: "inherit" }} data-testid={`home-mkt-item-${l.id}`}>
      <div style={{ aspectRatio: "4 / 3", background: "var(--surface-sunken)" }}>
        {coverOf(l) && <img src={coverOf(l)} alt={l.title} loading="lazy" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />}
      </div>
      <div style={{ padding: "12px 14px" }}>
        <div className="pmc-eyebrow" style={{ fontSize: "10px" }}>{l.sale_modes.map((m) => MODE_LABEL[m]).join(" · ")}</div>
        <div style={{ fontWeight: 600, fontSize: "15px", lineHeight: "20px", margin: "4px 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{l.title}</div>
        <div className="pmc-muted" style={{ fontSize: "13px" }}>{priceLine(l)}</div>
      </div>
    </Link>);
}

function AdvertSlot({ ads }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (ads.length < 2) return undefined;
    const t = setInterval(() => setI((x) => (x + 1) % ads.length), 7000);
    return () => clearInterval(t);
  }, [ads.length]);
  if (!ads.length) {
    return (
      <div className="pmc-card" style={{ height: "100%", minHeight: "320px", padding: "32px", display: "flex", flexDirection: "column", justifyContent: "center", border: "1px dashed var(--line)" }} data-testid="home-ad-placeholder">
        <div className="pmc-eyebrow">Advertise here</div>
        <h3 style={{ fontSize: "24px", margin: "8px 0 10px" }}>Reach buyers and suppliers worldwide</h3>
        <p className="pmc-muted" style={{ margin: "0 0 18px", fontSize: "15px" }}>This space is available for your brand, programme or event.</p>
        <a href="/contact" className="pmc-btn pmc-btn--secondary" style={{ alignSelf: "flex-start" }} data-testid="home-ad-contact">Contact PMC</a>
      </div>);
  }
  const a = ads[i % ads.length];
  const ext = /^https:/.test(a.link_url || "");
  return (
    <div className="pmc-card" style={{ height: "100%", overflow: "hidden", display: "flex", flexDirection: "column" }} data-testid="home-ad-slot">
      <div style={{ aspectRatio: "4 / 3", background: "var(--surface-sunken)", position: "relative" }}>
        {a.image_id && <img src={mediaUrl(a.image_id)} alt={a.title} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} data-testid="home-ad-image" />}
        <span className="pmc-tag" style={{ position: "absolute", top: "12px", left: "12px" }}>Advertisement</span>
      </div>
      <div style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
        <h3 style={{ fontSize: "22px", margin: 0 }} data-testid="home-ad-title">{a.title}</h3>
        {a.subtitle && <p className="pmc-muted" style={{ margin: 0, fontSize: "14px" }}>{a.subtitle}</p>}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "auto" }}>
          {a.link_url && <a href={a.link_url} {...(ext ? { target: "_blank", rel: "noopener noreferrer sponsored" } : {})} className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid="home-ad-cta">{a.cta_label || "Learn more"}</a>}
          {ads.length > 1 && <div style={{ display: "flex", gap: "6px", marginLeft: "auto" }}>{ads.map((x, k) => (
            <button key={x.id} type="button" aria-label={`Advert ${k + 1}`} onClick={() => setI(k)} data-testid={`home-ad-dot-${k}`}
              style={{ width: "24px", height: "24px", border: "none", background: "transparent", display: "grid", placeItems: "center", cursor: "pointer" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: k === i % ads.length ? "var(--ink)" : "var(--line)" }} /></button>))}</div>}
        </div>
      </div>
    </div>);
}

export default function HomeMarketShowcase() {
  const [d, setD] = useState(null);
  useEffect(() => { marketApi.showcase().then(setD).catch(() => setD({ products: [], adverts: [] })); }, []);
  if (!d) return null;
  return (
    <section className="pmc-wrap" style={{ padding: "72px 0 24px" }} data-testid="home-market-showcase">
      <div className="pmc-split-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", alignItems: "stretch" }}>
        <div data-testid="home-mkt-products">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", marginBottom: "16px", gap: "12px" }}>
            <div><div className="pmc-eyebrow">Supplier marketplace</div><h2 className="pmc-display" style={{ fontSize: "32px", lineHeight: "38px", margin: "6px 0 0" }}>Buy direct from verified suppliers</h2></div>
            <Link to="/market" className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid="home-mkt-browse">Browse all →</Link>
          </div>
          {d.products.length > 0 ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>{d.products.map((l) => <ProductTile key={l.id} l={l} />)}</div>
          ) : (
            <div className="pmc-card" style={{ padding: "28px" }} data-testid="home-mkt-empty">
              <p style={{ margin: "0 0 14px" }}>Approved suppliers can list products here for auction, best offer or buy now.</p>
              <a href="/vendor/market" className="pmc-btn pmc-btn--primary pmc-btn--sm">List your products</a>
            </div>)}
        </div>
        <AdvertSlot ads={d.adverts || []} />
      </div>
    </section>);
}
