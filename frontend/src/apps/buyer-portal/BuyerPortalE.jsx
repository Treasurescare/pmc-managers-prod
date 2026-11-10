import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { toast } from "sonner";
import BuyerChrome, { useBuyer } from "./BuyerChrome";
import { BuyerTeam, BuyerProfile } from "./BuyerAccount";
import { buyerApi, money, day } from "@/lib/buyerApi";
import { marketApi, mediaUrl } from "@/lib/marketApi";
import { showApiError } from "@/lib/api";

const BADGE = { leading: "bg-emerald-100 text-emerald-900", won: "bg-emerald-200 text-emerald-950", outbid: "bg-amber-100 text-amber-900",
  lost: "bg-gray-100 text-gray-700", open: "bg-sky-100 text-sky-900", accepted: "bg-emerald-200 text-emerald-950", declined: "bg-gray-100 text-gray-700",
  replaced: "bg-gray-100 text-gray-500", awaiting_payment: "bg-amber-100 text-amber-900", paid: "bg-emerald-100 text-emerald-900" };
const Badge = ({ s, id }) => <span className={`text-[11px] uppercase tracking-wide px-2 py-0.5 rounded ${BADGE[s] || "bg-gray-100"}`} data-testid={id}>{String(s || "").replace(/_/g, " ")}</span>;
const H = ({ t, sub }) => <div className="mb-4"><h1 className="text-2xl font-semibold">{t}</h1>{sub && <p className="text-sm opacity-70">{sub}</p>}</div>;
const Empty = ({ t, id }) => <p className="text-sm opacity-60 pmc-panel p-4" data-testid={id}>{t}</p>;

function useDash() {
  const [d, setD] = useState(null);
  const load = useCallback(() => buyerApi.dashboard().then(setD).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  return [d, load];
}

function Home() {
  const [d] = useDash();
  const { me } = useBuyer();
  if (!d) return null;
  const c = d.counts;
  const tiles = [["Active bids & offers", c.active_bids, "/buyer/bids"], ["To pay", c.to_pay, "/buyer/orders"], ["In delivery", c.in_delivery, "/buyer/orders"], ["Won / bought", c.won, "/buyer/orders"], ["Unread notifications", d.unread, "/buyer/notifications"]];
  return (
    <div data-testid="buyer-home">
      <H t={`Welcome, ${me.name || "buyer"}`} sub={me.org ? `${me.org.name} · ${me.org.code}` : "Your account is awaiting PMC verification"} />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {tiles.map(([t, n, to]) => <Link key={t} to={to} className="pmc-panel p-4 hover:shadow" data-testid={`buyer-tile-${t.toLowerCase().replace(/[^a-z]+/g, "-")}`}><div className="text-3xl font-semibold">{n}</div><div className="text-xs opacity-70">{t}</div></Link>)}
      </div>
      <h2 className="font-semibold mb-2">Latest activity</h2>
      <BidTable rows={d.bids.slice(0, 5)} />
      <Link to="/market" className="pmc-btn pmc-btn--primary mt-4 inline-block" data-testid="buyer-browse-btn">Browse the marketplace</Link>
    </div>);
}

function BidTable({ rows }) {
  if (!rows.length) return <Empty t="No bids or offers yet. Open a product on the marketplace to bid, offer or buy." id="buyer-bids-empty" />;
  return (
    <div className="pmc-panel overflow-x-auto"><table className="w-full text-sm" data-testid="buyer-bids-table">
      <thead><tr className="text-left text-xs opacity-60"><th className="p-2">Product</th><th>Type</th><th>My amount</th><th>Highest bid</th><th>Closes</th><th>Status</th></tr></thead>
      <tbody>{rows.map((b) => (
        <tr key={b.id} className="border-t" data-testid={`buyer-bid-${b.id}`}>
          <td className="p-2"><Link className="underline" to={`/market/${b.listing_id}`}>{b.title || "Product"}</Link></td>
          <td>{b.kind === "bid" ? "Auction bid" : "Offer"}</td><td>{money(b.currency, b.amount)}</td>
          <td>{b.kind === "bid" ? money(b.currency, b.top_bid) : "—"}</td><td>{day(b.closes_at)}</td>
          <td><Badge s={b.my_status} id={`buyer-bid-status-${b.id}`} /></td>
        </tr>))}</tbody></table></div>);
}

function Bids() {
  const [d] = useDash();
  return <div data-testid="buyer-bids"><H t="Bids & auctions" sub="Where each of your bids and offers stands right now." />{d && <BidTable rows={d.bids} />}</div>;
}

const DELIV = { awaiting_dispatch: "Awaiting dispatch", dispatched: "Dispatched", delivered: "Delivered", received: "Received by you" };

function Orders() {
  const [d, load] = useDash();
  const loc = useLocation();
  useEffect(() => {
    const oid = new URLSearchParams(loc.search).get("order");
    if (oid) marketApi.orderStatus(oid).then((o) => { if (o.status === "paid") toast.success("Payment received — thank you"); load(); }).catch(() => {});
  }, [loc.search, load]);
  const pay = async (oid) => { try { window.location.href = (await marketApi.pay(oid)).checkout_url; } catch (e) { showApiError(e); } };
  const got = (oid) => buyerApi.received(oid).then(() => { toast.success("Thanks — marked as received"); load(); }).catch(showApiError);
  if (!d) return null;
  return (
    <div data-testid="buyer-orders"><H t="Purchases & deliveries" sub="Pay for won items and follow delivery." />
      {!d.orders.length && <Empty t="No purchases yet." id="buyer-orders-empty" />}
      <div className="grid gap-2">{d.orders.map((o) => (
        <div key={o.id} className="pmc-panel p-3 text-sm flex flex-wrap gap-3 items-center" data-testid={`buyer-order-${o.id}`}>
          <div className="flex-1 min-w-[220px]"><b>{o.title}</b><div className="text-xs opacity-70">From {o.seller_name || "seller"} · {day(o.created_at)}</div></div>
          <b>{money(o.currency, o.amount)}</b><Badge s={o.status} id={`buyer-order-status-${o.id}`} />
          {o.status === "paid" && <span className="text-xs" data-testid={`buyer-order-delivery-${o.id}`}>Delivery: <b>{DELIV[o.delivery_status] || "Awaiting dispatch"}</b>{o.delivery_note ? ` · ${o.delivery_note}` : ""}</span>}
          {o.status === "awaiting_payment" && <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => pay(o.id)} data-testid={`buyer-order-pay-${o.id}`}>Pay securely</button>}
          {o.status === "paid" && ["dispatched", "delivered"].includes(o.delivery_status) && <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => got(o.id)} data-testid={`buyer-order-received-${o.id}`}>I received it</button>}
        </div>))}</div>
    </div>);
}

function Payments() {
  const [d] = useDash();
  if (!d) return null;
  return (
    <div data-testid="buyer-payments"><H t="Payments & refunds" sub="Every payment you made, and any refund paid back to you." />
      <h2 className="font-semibold mb-2">Payments</h2>
      {!d.payments.length ? <Empty t="No payments yet." id="buyer-payments-empty" /> : (
        <div className="pmc-panel overflow-x-auto"><table className="w-full text-sm" data-testid="buyer-payments-table"><thead><tr className="text-left text-xs opacity-60"><th className="p-2">Date</th><th>Product</th><th>Amount</th></tr></thead>
          <tbody>{d.payments.map((o) => <tr key={o.id} className="border-t"><td className="p-2">{day(o.paid_at)}</td><td>{o.title}</td><td>{money(o.currency, o.amount)}</td></tr>)}</tbody></table></div>)}
      <h2 className="font-semibold mt-6 mb-2">Refunds & payouts to you</h2>
      {!d.refunds.length ? <Empty t="No refunds or payouts to you." id="buyer-refunds-empty" /> : d.refunds.map((o) => (
        <div key={o.id} className="pmc-panel p-3 text-sm" data-testid={`buyer-refund-${o.id}`}>{o.title} · {money(o.currency, o.refund_amount ?? o.amount)} · {String(o.refund_status).replace(/_/g, " ")}</div>))}
    </div>);
}

function Notifications() {
  const { refreshUnread } = useBuyer();
  const [items, setItems] = useState(null);
  const load = useCallback(() => buyerApi.notifications().then((r) => setItems(r.items)).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const read = (id) => buyerApi.readOne(id).then(() => { load(); refreshUnread(); });
  const all = () => buyerApi.readAll().then(() => { load(); refreshUnread(); });
  if (!items) return null;
  return (
    <div data-testid="buyer-notifications">
      <div className="flex items-center"><H t="Notifications" sub="Outbid alerts, wins, accepted offers, payments and deliveries. Important ones are emailed too." />
        <button className="pmc-btn pmc-btn--secondary pmc-btn--sm ml-auto" onClick={all} data-testid="buyer-notif-read-all">Mark all read</button></div>
      {!items.length && <Empty t="No notifications yet." id="buyer-notif-empty" />}
      <div className="grid gap-2">{items.map((n) => (
        <div key={n.id} className={`pmc-panel p-3 text-sm ${n.read ? "opacity-60" : "border-l-4 border-emerald-700"}`} data-testid={`buyer-notif-${n.id}`}>
          <div className="flex gap-2"><b className="flex-1">{n.subject}</b><span className="text-xs opacity-60">{day(n.created_at)}</span></div>
          <div className="text-xs mt-1 whitespace-pre-line" data-testid={`buyer-notif-body-${n.id}`}>{String(n.body || "").replace(/<[^>]*>/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, "\"").replace(/&#x27;/g, "'").replace(/&amp;/g, "&").replace(/\s+/g, " ").replace(/\s+([.,])/g, "$1").trim()}</div>
          <div className="flex gap-3 mt-1 text-xs">{n.link && <Link className="underline" to={n.link} onClick={() => read(n.id)}>Open</Link>}
            {!n.read && <button className="underline" onClick={() => read(n.id)} data-testid={`buyer-notif-read-${n.id}`}>Mark read</button>}</div>
        </div>))}</div>
    </div>);
}

function Watchlist() {
  const [d, setD] = useState(null);
  const load = useCallback(() => buyerApi.watchlist().then(setD).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const rm = (id) => buyerApi.unwatch(id).then(() => { toast.success("Removed from your watchlist"); load(); }).catch(showApiError);
  if (!d) return null;
  return (
    <div data-testid="buyer-watchlist"><H t="Watchlist" sub="Products you saved. For auctions we remind you (bell + email) about an hour before they close." />
      {!d.items.length && <Empty t="Nothing saved yet. Tap ♡ Save on any marketplace product." id="buyer-watch-empty" />}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">{d.items.map((w) => (
        <div key={w.listing_id} className="pmc-panel p-3 text-sm grid gap-1" data-testid={`buyer-watch-${w.listing_id}`}>
          {w.photo && <img src={mediaUrl(w.photo)} alt="" className="w-full h-32 object-cover rounded" />}
          <Link className="font-semibold underline" to={`/market/${w.listing_id}`}>{w.title}</Link>
          <div className="text-xs opacity-70">{w.status === "live" ? (w.closes_at ? `Closes ${new Date(w.closes_at).toLocaleString()}` : "Open") : w.status}{w.reminded ? " · reminder sent" : ""}</div>
          <button className="pmc-btn pmc-btn--secondary pmc-btn--sm justify-self-start" onClick={() => rm(w.listing_id)} data-testid={`buyer-watch-remove-${w.listing_id}`}>Remove</button>
        </div>))}</div>
    </div>);
}

const PAGES = { "": Home, watchlist: Watchlist, bids: Bids, orders: Orders, payments: Payments, notifications: Notifications, team: BuyerTeam, profile: BuyerProfile };

export default function BuyerPortalE() {
  const loc = useLocation();
  const key = loc.pathname.replace(/^\/buyer\/?/, "").split("/")[0];
  const Page = PAGES[key] || Home;
  return <BuyerChrome><Page /></BuyerChrome>;
}
