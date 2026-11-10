import { useEffect, useState } from "react";
import { marketApi } from "@/lib/marketApi";

// Explains who may take part and where to sign in / apply, instead of a bare HTTP 403.
export function WhoCanBuy({ l, onBlocked }) {
  const [me, setMe] = useState(null);
  useEffect(() => { marketApi.whoami().then(setMe).catch(() => setMe({ kind: null })); }, []);
  const buyersOnly = l.eligibility === "verified_buyers";
  const own = me?.kind === "supplier" && me.id && me.id === l.seller_id;
  const blocked = !!me && (own || !me.kind || me.kind === "staff" || (buyersOnly && me.kind !== "buyer") || (me.kind === "supplier" && !me.verified));
  useEffect(() => { if (me) onBlocked(blocked); }, [me, blocked, onBlocked]);
  if (!me) return null;
  if (own) return <p className="text-sm border border-black/10 rounded p-3" data-testid="market-who-own">This is your own listing. Buyers see the buttons below; you can manage it in <a className="underline" href="/vendor/market">Sell products</a>.</p>;
  if (!blocked) return <p className="text-xs opacity-70" data-testid="market-who-ok">Signed in as <b>{me.name}</b> ({me.kind === "buyer" ? "verified buyer organisation" : "verified supplier"}).</p>;
  const next = encodeURIComponent(window.location.pathname);
  return (
    <div className="text-sm border border-amber-600/40 bg-amber-50 text-amber-950 rounded p-3 space-y-2" data-testid="market-who-blocked">
      <b>{buyersOnly ? "Only verified buyer organisations can buy this product." : "Verified buyers and suppliers can take part."}</b>
      {me.kind === "supplier" && <p>You are signed in as the supplier <b>{me.name}</b>. This seller only sells to buyer organisations.</p>}
      {me.kind === "staff" && <p>You are signed in as PMC staff. Staff accounts cannot buy.</p>}
      <ol className="list-decimal ml-5 space-y-1">
        <li>Your organisation applies once as a buyer: <a className="underline" href="/buyers/apply" data-testid="market-who-apply">Apply as a buyer organisation</a>.</li>
        <li>PMC verifies the organisation and sends your buyer sign-in.</li>
        <li><a className="underline" href={`/login?next=${next}`} data-testid="market-who-signin">Sign in as a buyer</a>, come back to this page and bid, offer or buy.</li>
      </ol>
      {!buyersOnly && !me.kind && <p>Suppliers: <a className="underline" href={`/vendor/login?next=${next}`} data-testid="market-who-supplier-signin">sign in to the supplier portal</a> or <a className="underline" href="/register" data-testid="market-who-register">register as a supplier</a>.</p>}
    </div>);
}
