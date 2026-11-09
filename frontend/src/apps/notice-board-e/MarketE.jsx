import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { coverOf, marketApi, mediaUrl, MODE_LABEL, money } from "@/lib/marketApi";
import { showApiError } from "@/lib/api";

const signInHint = (e) => {
  if (e?.response?.status === 401) {
    toast.info("Please sign in first", { description: "Buyers sign in to the admin console; suppliers to the supplier portal.", action: { label: "Sign in", onClick: () => { window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`; } } });
  } else showApiError(e);
};

function Card({ l }) {
  return (
    <Link to={`/market/${l.id}`} className="pmc-panel p-4 block hover:opacity-90" data-testid={`market-card-${l.id}`}>
      {coverOf(l) && <img src={coverOf(l)} alt="" className="w-full h-40 object-cover rounded mb-2" />}
      <div className="font-semibold">{l.title}</div>
      <div className="text-xs opacity-75 mt-1">{l.seller_name} · {l.quantity} {l.unit}{l.location ? ` · ${l.location}` : ""}</div>
      <div className="text-sm mt-2">{l.sale_modes.map((m) => MODE_LABEL[m]).join(" · ")}</div>
      <div className="text-sm mt-1">
        {l.sale_modes.includes("auction") && <>Current bid <b>{money(l.currency, l.top_bid ?? l.start_price)}</b> </>}
        {l.sale_modes.includes("fixed") && <>· Price <b>{money(l.currency, l.buy_now_price)}</b></>}
      </div>
      {l.closes_at && <div className="text-xs opacity-75 mt-1">Closes {new Date(l.closes_at).toLocaleString()}</div>}
    </Link>);
}

function Gallery({ l }) {
  const pics = l.photos?.length ? l.photos.map((p) => mediaUrl(p)) : l.image_url ? [l.image_url] : [];
  const [i, setI] = useState(0);
  if (!pics.length) return null;
  return (
    <div className="mb-3" data-testid="market-gallery">
      <img src={pics[Math.min(i, pics.length - 1)]} alt="" className="w-full max-h-96 object-contain rounded bg-black/20" data-testid="market-gallery-main" />
      {pics.length > 1 && <div className="flex flex-wrap gap-2 mt-2">{pics.map((u, k) => (
        <button key={u} type="button" onClick={() => setI(k)} data-testid={`market-thumb-${k}`}><img src={u} alt="" className={`w-14 h-14 object-cover rounded ${k === i ? "ring-2 ring-white" : "opacity-70"}`} /></button>))}</div>}
    </div>);
}

function Detail({ id }) {
  const [l, setL] = useState(null);
  const [amt, setAmt] = useState("");
  const [note, setNote] = useState("");
  const load = () => marketApi.detail(id).then(setL).catch(showApiError);
  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!l) return <p className="opacity-70">Loading…</p>;
  const live = l.status === "live";
  const run = async (fn, ok) => { try { await fn(); toast.success(ok); setAmt(""); load(); } catch (e) { signInHint(e); } };
  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="market-detail">
      <div>
        <Gallery l={l} />
        <h1 className="text-2xl font-semibold" data-testid="market-detail-title">{l.title}</h1>
        <div className="text-sm opacity-80 mt-1">Sold by {l.seller_name} · {l.quantity} {l.unit}{l.location ? ` · ${l.location}` : ""}{l.category ? ` · ${l.category}` : ""}</div>
        <p className="mt-3 whitespace-pre-wrap text-sm">{l.description}</p>
        {l.documents?.length > 0 && <div className="mt-3 text-sm" data-testid="market-docs"><b>Spec sheets</b>{l.documents.map((d) => (
          <a key={d.id} href={mediaUrl(d.id)} target="_blank" rel="noreferrer" className="underline block" data-testid={`market-doc-${d.id}`}>{d.name}</a>))}</div>}
        <p className="text-xs opacity-70 mt-3">{l.eligibility === "verified_buyers" ? "Open to verified buyer organisations." : "Open to any verified buyer or supplier."} Payment is made to PMC by secure card link; PMC pays the seller.</p>
      </div>
      <div className="pmc-panel p-4 space-y-3">
        <div className="text-sm">Status: <b data-testid="market-detail-status">{live ? "Open" : l.status === "sold" ? "Sold" : "Closed"}</b>{l.closes_at ? ` · closes ${new Date(l.closes_at).toLocaleString()}` : ""}</div>
        {l.sale_modes.includes("auction") && <div className="text-sm">Current bid <b data-testid="market-top-bid">{money(l.currency, l.top_bid)}</b> · {l.bid_count} bids · starting {money(l.currency, l.start_price)}{l.top_bid != null && !l.reserve_met ? " · reserve not yet met" : ""}</div>}
        {live && (l.sale_modes.includes("auction") || l.sale_modes.includes("best_offer")) &&
          <input type="number" min="0" className="pmc-input w-full" placeholder={`Amount in ${l.currency}`} value={amt} onChange={(e) => setAmt(e.target.value)} data-testid="market-amount" />}
        {live && l.sale_modes.includes("auction") &&
          <button className="pmc-btn pmc-btn--primary w-full" onClick={() => run(() => marketApi.bid(id, Number(amt)), "Bid placed")} data-testid="market-bid-btn">Place bid</button>}
        {live && l.sale_modes.includes("best_offer") && <>
          <input className="pmc-input w-full" placeholder="Note to the seller (optional)" value={note} onChange={(e) => setNote(e.target.value)} data-testid="market-note" />
          <button className="pmc-btn pmc-btn--secondary w-full" onClick={() => run(() => marketApi.offer(id, Number(amt), note), "Offer sent to the seller")} data-testid="market-offer-btn">Send offer</button>
        </>}
        {live && l.sale_modes.includes("fixed") &&
          <button className="pmc-btn pmc-btn--primary w-full" onClick={() => run(() => marketApi.buy(id), "Order placed — pay from My purchases")} data-testid="market-buy-btn">Buy now for {money(l.currency, l.buy_now_price)}</button>}
        <Link to="/market/purchases" className="text-sm underline block" data-testid="market-my-purchases-link">My bids & purchases</Link>
      </div>
    </div>);
}

function Purchases() {
  const [d, setD] = useState(null);
  const load = () => marketApi.purchases().then(setD).catch(signInHint);
  useEffect(() => {
    const oid = new URLSearchParams(window.location.search).get("order");
    (oid ? marketApi.orderStatus(oid).then((o) => o.status === "paid" && toast.success("Payment received — thank you")).catch(() => {}) : Promise.resolve()).then(load);
  }, []);
  const pay = async (oid) => { try { window.location.href = (await marketApi.pay(oid)).checkout_url; } catch (e) { showApiError(e); } };
  if (!d) return <p className="opacity-70">Sign in to see your bids and purchases.</p>;
  return (
    <div data-testid="market-purchases">
      <h1 className="text-2xl font-semibold">My bids & purchases</h1>
      <h2 className="font-semibold mt-4">Orders</h2>
      {d.orders.length === 0 && <p className="text-sm opacity-70">No orders yet.</p>}
      {d.orders.map((o) => (
        <div key={o.id} className="pmc-panel p-3 mt-2 text-sm flex flex-wrap justify-between gap-2" data-testid={`market-order-${o.id}`}>
          <span><b>{o.title}</b> — {money(o.currency, o.amount)} from {o.seller_name} · {o.status.replace("_", " ")}</span>
          {o.status === "awaiting_payment" && <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => pay(o.id)} data-testid={`market-pay-${o.id}`}>Pay securely</button>}
        </div>))}
      <h2 className="font-semibold mt-4">Bids & offers</h2>
      {d.bids.map((b) => <div key={b.id} className="text-sm mt-1"><Link className="underline" to={`/market/${b.listing_id}`}>{b.kind === "bid" ? "Bid" : "Offer"} {Number(b.amount).toLocaleString()}</Link> · {b.status || "placed"}</div>)}
    </div>);
}

export default function MarketE() {
  const { id } = useParams();
  const [items, setItems] = useState(null);
  const [q, setQ] = useState("");
  useSeo({ title: "Supplier Marketplace — PMC Managers", description: "Buy products directly from verified suppliers by auction, best offer or fixed price." });
  useEffect(() => { if (!id) { marketApi.browse({ q }).then((r) => setItems(r.items)).catch(showApiError); } }, [id, q]);
  return (
    <PublicChrome>
      <main className="max-w-6xl mx-auto px-4 py-8" data-testid="market-page">
        {id === "purchases" ? <Purchases /> : id ? <Detail id={id} /> : <>
          <h1 className="text-3xl font-semibold">Supplier Marketplace</h1>
          <p className="opacity-80 mt-1 max-w-2xl">Products offered directly by verified suppliers — bid in a timed auction, make an offer, or buy at a fixed price. Every listing is approved by PMC.</p>
          <input className="pmc-input mt-4 w-full max-w-md" placeholder="Search products" value={q} onChange={(e) => setQ(e.target.value)} data-testid="market-search" />
          <div className="grid gap-4 mt-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="market-grid">
            {items && items.length === 0 && <p className="opacity-70">No products are listed right now.</p>}
            {(items || []).map((l) => <Card key={l.id} l={l} />)}
          </div>
        </>}
      </main>
    </PublicChrome>);
}
