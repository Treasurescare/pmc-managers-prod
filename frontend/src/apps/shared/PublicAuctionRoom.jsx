import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { reverseAuctionApi } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";

/**
 * v46c — Public read-only spectator view for a reverse auction.
 *
 * Route: /auctions/:aid/live (public — no auth required)
 * Polls /state every 2s. Shows masked bid history, countdown, leader alias,
 * anti-snipe extensions. No bid/register controls — pure view.
 */
export default function PublicAuctionRoom() {
  const { aid } = useParams();
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [now, setNow] = useState(Date.now());
  const timer = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      reverseAuctionApi.state(aid)
        .then((s) => { if (!cancelled) { setState(s); setError(null); } })
        .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || "Auction not found"); });
    };
    poll();
    timer.current = setInterval(poll, 2000);
    const clock = setInterval(() => setNow(Date.now()), 500);
    return () => { cancelled = true; clearInterval(timer.current); clearInterval(clock); };
  }, [aid]);

  if (error) return (
    <div className="min-h-screen bg-brand-pale">
      <TopBar />
      <div className="max-w-3xl mx-auto px-6 py-16 border-2 border-red-500 bg-red-50 mt-8" data-testid="spectator-error">
        <div className="pmc-label mb-1">Auction unavailable</div>
        <div className="text-sm text-red-900">{error}</div>
      </div>
    </div>
  );

  if (!state) return (
    <div className="min-h-screen bg-brand-pale"><TopBar />
      <div className="p-16 text-center text-brand-navy/60">Loading auction…</div>
    </div>
  );

  const secondsLeft = state.status === "live"
    ? Math.max(0, Math.floor(((state.end_at ? new Date(state.end_at).getTime() : now) - now) / 1000))
    : 0;
  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const ss = String(secondsLeft % 60).padStart(2, "0");
  const cur = state.current_price ?? state.starting_price;
  const savings = state.status === "closed" && state.current_price
    ? (((state.starting_price - state.current_price) / state.starting_price) * 100).toFixed(1)
    : null;

  return (
    <div className="min-h-screen bg-brand-pale" data-testid="public-auction-spectator">
      <TopBar />
      <main className="max-w-5xl mx-auto px-6 lg:px-10 py-8">
        <div className="pmc-label">Reverse Auction · Public spectator view</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-1 text-brand-navy">{state.title}</h1>
        <div className="text-sm text-brand-navy-soft font-mono mt-1">{state.notice_ref}</div>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Status</div>
            <div className={`mt-1 text-xl font-semibold ${state.status === "live" ? "text-emerald-700" : state.status === "closed" ? "text-slate-500" : "text-brand-navy"}`}>
              {state.status.toUpperCase()}
            </div>
            {state.status === "live" && (
              <div className="mt-2 font-mono text-2xl text-brand-navy tabular-nums" data-testid="spectator-countdown">
                {mm}:{ss}
              </div>
            )}
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Current lowest</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy font-mono tabular-nums" data-testid="spectator-current-price">
              {state.currency} {(cur ?? 0).toLocaleString()}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">Δ {state.min_decrement?.toLocaleString()} · floor {state.floor_price?.toLocaleString()}</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Leader</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy" data-testid="spectator-leader">
              {state.leader_alias || "—"}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">{state.participant_count} bidders</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Starting price</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy font-mono tabular-nums">
              {state.currency} {state.starting_price?.toLocaleString()}
            </div>
            {savings && <div className="text-xs text-emerald-700 mt-1">−{savings}% saved</div>}
          </div>
        </div>

        <div className="mt-6 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid="spectator-notice">
          You are viewing this auction as a public spectator. Bidder identities are
          masked as "Bidder A", "Bidder B" etc — company names are never shown
          during the live round. Only registered vendors can place bids.
        </div>

        <div className="mt-8 border border-brand-navy/10 bg-white">
          <div className="p-4 border-b border-brand-navy/10 text-sm text-brand-navy/70">
            Live bid activity (masked)
          </div>
          {state.bids.length === 0 && <div className="p-6 text-brand-navy/40 text-sm">No bids yet.</div>}
          {state.bids.map((b, i) => (
            <div key={`${b.at}-${b.alias}-${b.price}`} className="p-3 border-b border-brand-navy/5 flex items-baseline gap-4"
                 data-testid={`spectator-bid-${i}`}>
              <span className="font-mono text-xs text-brand-navy/50 w-32">{b.at?.slice(11, 19)}</span>
              <span className="text-sm font-semibold w-24">{b.alias}</span>
              <span className="font-mono tabular-nums text-brand-navy flex-1">
                {state.currency} {b.price?.toLocaleString()}
              </span>
              {b.auto && <span className="text-[10px] uppercase tracking-widest text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5">auto</span>}
            </div>
          ))}
        </div>

        {state.status === "closed" && (
          <div className="mt-6 border-2 border-emerald-500 bg-emerald-50 p-6 text-emerald-900" data-testid="spectator-closed">
            <div className="pmc-label">Auction closed</div>
            <div className="mt-1 text-lg">
              Final: <b>{state.currency} {(state.current_price ?? 0).toLocaleString()}</b>
              {" · "}Winner: <b>{state.leader_alias || "—"}</b>
              {savings && <span className="ml-2">({savings}% saved vs start)</span>}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
