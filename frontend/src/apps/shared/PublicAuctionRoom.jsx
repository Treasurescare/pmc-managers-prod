import { useEffect, useRef, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { reverseAuctionApi } from "@/lib/api";
import PublicChrome from "@/apps/shared/PublicChrome";

const money = (cur, v) => `${cur || "USD"} ${Number(v || 0).toLocaleString()}`;

function viewerId() {
  try {
    let v = localStorage.getItem("ra_viewer_id");
    if (!v) {
      v = "anon-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem("ra_viewer_id", v);
    }
    return v;
  } catch {
    return "anon-" + Math.random().toString(36).slice(2);
  }
}

/** Descending-price chart built from the masked bid ledger (oldest→newest). */
function PriceChart({ bids, starting, floor, currency }) {
  const pts = [...(bids || [])].reverse().map((b) => Number(b.price)).filter((n) => !isNaN(n));
  const series = [Number(starting), ...pts].filter((n) => !isNaN(n));
  if (series.length < 2) {
    return <div className="text-brand-navy/40 text-sm p-6" data-testid="price-chart-empty">Chart appears once bidding starts.</div>;
  }
  const W = 640, H = 160, PAD = 8;
  const max = Math.max(...series), min = Math.min(floor || Math.min(...series), ...series);
  const span = max - min || 1;
  const x = (i) => PAD + (i * (W - 2 * PAD)) / (series.length - 1);
  const y = (v) => PAD + ((max - v) / span) * (H - 2 * PAD);
  const line = series.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(series.length - 1).toFixed(1)},${H - PAD} L${PAD},${H - PAD} Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="160" data-testid="price-chart" preserveAspectRatio="none">
      <path d={area} fill="rgba(5,95,70,0.08)" />
      <path d={line} fill="none" stroke="#065f46" strokeWidth="2" />
      {series.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r="2.5" fill="#065f46" />)}
      <title>{`${money(currency, max)} → ${money(currency, series[series.length - 1])}`}</title>
    </svg>
  );
}

const AWARD_COPY = {
  in_approvals: {
    tone: "#92400e", bg: "#fffbeb", border: "#fcd34d",
    title: "Result gone for approvals",
    body: "The auction has closed. The winning bid is now moving through PMC's governance sign-off (escrow, legal, accounting). The winning company is published only after the award is approved.",
  },
  awarded_published: {
    tone: "#1d4ed8", bg: "#eff6ff", border: "#93c5fd",
    title: "Award published",
    body: "This auction has been awarded and approved.",
  },
  closed_unawarded: {
    tone: "#475569", bg: "#f8fafc", border: "#cbd5e1",
    title: "Auction closed with no award",
    body: "The auction closed without a winning bid.",
  },
};

export default function PublicAuctionRoom() {
  const { aid } = useParams();
  const [state, setState] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [transport, setTransport] = useState("connecting");
  const esRef = useRef(null);
  const pollRef = useRef(null);
  const stateRef = useRef(null);
  const vid = useRef(viewerId());

  const applyState = useCallback((s) => { stateRef.current = s; setState(s); setError(null); }, []);

  // Live transport: SSE with polling fallback. Stops entirely once closed.
  useEffect(() => {
    let cancelled = false;
    let retried = false;
    const stopPoll = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    const startPolling = () => {
      if (pollRef.current || cancelled) return;
      setTransport("polling");
      const tick = () => reverseAuctionApi.state(aid)
        .then((s) => { if (cancelled) return; applyState(s); if (s.status === "closed") stopPoll(); })
        .catch((e) => setError(e?.response?.data?.detail || "Auction not found"));
      tick();
      pollRef.current = setInterval(tick, 2500);
    };
    const connect = () => {
      if (cancelled) return;
      try {
        const es = new EventSource(reverseAuctionApi.streamUrl(aid));
        esRef.current = es;
        es.onmessage = (ev) => {
          if (cancelled) return;
          try {
            const s = JSON.parse(ev.data);
            applyState(s);
            setTransport("live");
            if (s.status === "closed") { try { es.close(); } catch { /* noop */ } esRef.current = null; }
          } catch { /* ignore */ }
        };
        es.addEventListener("gone", () => { if (!cancelled) setError("Auction not found"); });
        es.onerror = () => {
          try { es.close(); } catch { /* noop */ }
          esRef.current = null;
          if (cancelled) return;
          if (stateRef.current?.status === "closed") return;  // done — no need to reconnect
          if (!retried) { retried = true; setTimeout(connect, 1500); }  // one SSE retry
          else startPolling();                                          // then fall back
        };
      } catch {
        startPolling();
      }
    };
    connect();
    return () => {
      cancelled = true;
      if (esRef.current) { try { esRef.current.close(); } catch { /* noop */ } }
      stopPoll();
    };
  }, [aid, applyState]);

  // Anonymous presence heartbeat.
  useEffect(() => {
    const beat = () => reverseAuctionApi.heartbeat(aid, vid.current).catch(() => {});
    beat();
    const t = setInterval(beat, 10000);
    return () => clearInterval(t);
  }, [aid]);

  // Hash-chained public timeline.
  useEffect(() => {
    const load = () => reverseAuctionApi.events(aid).then((r) => setEvents(r.items || [])).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [aid]);

  // Local clock for countdown.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);

  if (error) return (
    <PublicChrome active="auctions" testid="public-auction-spectator-error">
      <div className="max-w-3xl mx-auto px-6 py-16 border-2 border-red-500 bg-red-50 mt-8" data-testid="spectator-error">
        <div className="pmc-label mb-1">Auction unavailable</div>
        <div className="text-sm text-red-900">{error}</div>
      </div>
    </PublicChrome>
  );

  if (!state) return (
    <PublicChrome active="auctions" testid="public-auction-spectator-loading">
      <div className="p-16 text-center text-brand-navy/60" data-testid="spectator-loading">Loading auction…</div>
    </PublicChrome>
  );

  const secondsLeft = state.status === "live"
    ? Math.max(0, Math.floor(((state.end_at ? new Date(state.end_at).getTime() : now) - now) / 1000))
    : 0;
  const hh = Math.floor(secondsLeft / 3600);
  const mm = String(Math.floor((secondsLeft % 3600) / 60)).padStart(2, "0");
  const ss = String(secondsLeft % 60).padStart(2, "0");
  const cur = state.current_price ?? state.starting_price;
  const savings = state.status === "closed" && state.current_price
    ? (((state.starting_price - state.current_price) / state.starting_price) * 100).toFixed(1)
    : null;
  const award = state.status === "closed" ? AWARD_COPY[state.award_status] : null;

  return (
    <PublicChrome active="auctions" testid="public-auction-spectator">
      <main className="max-w-5xl mx-auto px-6 lg:px-10 py-8">
        <div className="mb-4 flex items-center justify-between" data-testid="spectator-back">
          <Link to="/auctions"
                className="text-[11px] uppercase tracking-widest text-brand-navy/70 hover:text-brand-navy border-b border-brand-navy/30">
            ← All auctions
          </Link>
          <span className="text-[11px] uppercase tracking-widest text-brand-navy/50 flex items-center gap-2"
                data-testid="spectator-transport">
            <span className={`inline-block w-2 h-2 rounded-full ${transport === "live" ? "bg-emerald-500" : transport === "polling" ? "bg-amber-500" : "bg-slate-400"}`} />
            {transport === "live" ? "Live" : transport === "polling" ? "Auto-refresh" : "Connecting"}
            <span className="ml-3" data-testid="spectator-viewers">{state.viewer_count ?? 0} watching</span>
          </span>
        </div>

        <div className="pmc-label">Reverse Auction · Public spectator view</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-1 text-brand-navy" data-testid="spectator-title">{state.title}</h1>
        <div className="text-sm text-brand-navy-soft font-mono mt-1">
          {state.notice_ref}{state.is_standalone ? " · standalone" : ""}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Status</div>
            <div className={`mt-1 text-xl font-semibold ${state.status === "live" ? "text-emerald-700" : state.status === "closed" ? "text-slate-500" : "text-brand-navy"}`}
                 data-testid="spectator-status">
              {state.status.toUpperCase()}
            </div>
            {state.status === "live" && (
              <div className="mt-2 font-mono text-2xl text-brand-navy tabular-nums" data-testid="spectator-countdown">
                {hh > 0 ? `${hh}:` : ""}{mm}:{ss}
              </div>
            )}
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Current lowest</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy font-mono tabular-nums" data-testid="spectator-current-price">
              {money(state.currency, cur)}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">Δ {state.min_decrement?.toLocaleString()} · floor {state.floor_price?.toLocaleString()}</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Leader</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy" data-testid="spectator-leader">
              {state.leader_alias || "—"}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1" data-testid="spectator-counts">
              {state.participant_count} bidders · {state.invite_count} invited
            </div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">{state.status === "closed" ? "Final / compliant" : "Starting price"}</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy font-mono tabular-nums">
              {money(state.currency, state.status === "closed" ? state.current_price : state.starting_price)}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1" data-testid="spectator-compliant">
              {savings ? `−${savings}% saved · ` : ""}{state.compliant_bidder_count ?? 0} compliant bidder{(state.compliant_bidder_count ?? 0) === 1 ? "" : "s"}
            </div>
          </div>
        </div>

        <div className="mt-6 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid="spectator-notice">
          You are viewing this auction as a public spectator. Bidder identities are
          masked as "Bidder A", "Bidder B" etc — company names are never shown
          during the live round. Only registered vendors can place bids.
        </div>

        <div className="mt-8 border border-brand-navy/10 bg-white p-4" data-testid="spectator-chart-panel">
          <div className="text-sm text-brand-navy/70 mb-2">Price descent</div>
          <PriceChart bids={state.bids} starting={state.starting_price} floor={state.floor_price} currency={state.currency} />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="border border-brand-navy/10 bg-white">
            <div className="p-4 border-b border-brand-navy/10 text-sm text-brand-navy/70">Live bid ladder (masked)</div>
            {state.bids.length === 0 && <div className="p-6 text-brand-navy/40 text-sm" data-testid="spectator-no-bids">No bids yet.</div>}
            {state.bids.map((b, i) => (
              <div key={`${b.at}-${b.alias}-${b.price}`} className="p-3 border-b border-brand-navy/5 flex items-baseline gap-4"
                   data-testid={`spectator-bid-${i}`}>
                <span className="font-mono text-xs text-brand-navy/50 w-20">{b.at?.slice(11, 19)}</span>
                <span className="text-sm font-semibold w-24">{b.alias}</span>
                <span className="font-mono tabular-nums text-brand-navy flex-1">{money(state.currency, b.price)}</span>
                {b.auto && <span className="text-[10px] uppercase tracking-widest text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5">auto</span>}
              </div>
            ))}
          </div>

          <div className="border border-brand-navy/10 bg-white">
            <div className="p-4 border-b border-brand-navy/10 text-sm text-brand-navy/70 flex items-center justify-between">
              <span>Audit timeline</span>
              <span className="text-[10px] uppercase tracking-widest text-brand-navy/40">SHA-256 chained</span>
            </div>
            {events.length === 0 && <div className="p-6 text-brand-navy/40 text-sm" data-testid="spectator-no-events">No events yet.</div>}
            <div className="max-h-80 overflow-auto">
              {events.slice().reverse().map((e) => (
                <div key={e.seq} className="p-3 border-b border-brand-navy/5 text-sm" data-testid={`spectator-event-${e.seq}`}>
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-xs text-brand-navy/50 w-16">#{e.seq}</span>
                    <span className="uppercase tracking-widest text-[10px] text-brand-navy/70 w-20">{e.kind}</span>
                    <span className="font-mono text-xs text-brand-navy/50">{e.at?.slice(11, 19)}</span>
                  </div>
                  <div className="font-mono text-[10px] text-brand-navy/30 mt-1 truncate">{e.hash}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {state.status === "closed" && award && (
          <div className="mt-6 p-6" style={{ border: `2px solid ${award.border}`, background: award.bg, color: award.tone }}
               data-testid="spectator-closed">
            <div className="pmc-label">{award.title}</div>
            <div className="mt-2 text-sm">{award.body}</div>
            <div className="mt-3 text-lg">
              Final: <b data-testid="spectator-final-price">{money(state.currency, state.current_price)}</b>
              {savings && <span className="ml-2">({savings}% saved vs start)</span>}
            </div>
            {state.award_status === "awarded_published" && state.winner && (
              <div className="mt-2 text-lg" data-testid="spectator-winner">
                Winner: <b>{state.winner.company_name}</b>
              </div>
            )}
          </div>
        )}
      </main>
    </PublicChrome>
  );
}
