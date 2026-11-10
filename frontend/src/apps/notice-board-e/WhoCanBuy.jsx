import { useEffect, useState } from "react";
import { marketApi } from "@/lib/marketApi";

// Explains who may take part and where to sign in / apply, instead of a bare HTTP 403.
export function WhoCanBuy({ l }) {
  const [me, setMe] = useState(null);
  useEffect(() => { marketApi.whoami().then(setMe).catch(() => setMe({ kind: null })); }, []);
  if (!me) return null;
  const buyersOnly = l.eligibility === "verified_buyers";
  const blocked = (buyersOnly && me.kind !== "buyer") || me.kind === "staff" || (me.kind === "supplier" && !me.verified);
  if (!blocked && me.kind) return <p className="text-xs opacity-70" data-testid="market-who-ok">Signed in as <b>{me.name}</b> ({me.kind === "buyer" ? "verified buyer organisation" : "verified supplier"}).</p>;
  return (
    <div className="text-sm border border-amber-600/40 bg-amber-50 text-amber-950 rounded p-3 space-y-2" data-testid="market-who-blocked">
      <b>{buyersOnly ? "Only verified buyer organisations can buy this product." : "Only verified buyers and suppliers can take part."}</b>
      {me.kind === "supplier" && <p>You are signed in as the supplier <b>{me.name}</b>. Supplier accounts can sell, but this seller only sells to buyer organisations.</p>}
      {me.kind === "staff" && <p>You are signed in as PMC staff. Staff accounts cannot buy.</p>}
      <ol className="list-decimal ml-5 space-y-1">
        <li>Your organisation applies once as a buyer: <a className="underline" href="/buyers/apply" data-testid="market-who-apply">Apply as a buyer organisation</a>.</li>
        <li>PMC verifies the organisation and sends your buyer sign-in.</li>
        <li><a className="underline" href={`/login?next=${encodeURIComponent(window.location.pathname)}`} data-testid="market-who-signin">Sign in as a buyer</a>, come back to this page and bid, offer or buy.</li>
      </ol>
    </div>);
}
