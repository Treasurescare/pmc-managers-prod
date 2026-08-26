import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { reverseAuctionApi, formatApiError } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";

/** Wave 40 — Live reverse-auction room (vendor).
 *
 * Polls /state-mine every 2s. Shows countdown, current lowest price, my alias,
 * my rank vs leader, bid history with masked aliases, place-bid form, and an
 * auto-bid setup. Anti-snipe extension flashes when it happens. */
export default function AuctionRoom() {
  const { aid } = useParams();
  const [state, setState] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [bidPrice, setBidPrice] = useState("");
  const [autoFloor, setAutoFloor] = useState("");
  const [autoOn, setAutoOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const pollTimer = useRef(null);

  const pollState = useCallback(async () => {
    try {
      const s = await reverseAuctionApi.stateMine(aid);
      setState(s);
      if (s.me?.autobid_floor && !autoFloor) setAutoFloor(String(s.me.autobid_floor));
      if (s.me?.autobid_enabled) setAutoOn(true);
    } catch {
      // silent — auction may not exist yet
    }
  }, [aid, autoFloor]);

  useEffect(() => {
    pollState();
    pollTimer.current = setInterval(pollState, 2000);
    const clock = setInterval(() => setNow(Date.now()), 500);
    return () => { clearInterval(pollTimer.current); clearInterval(clock); };
  }, [pollState]);

  const register = async () => {
    setBusy(true);
    try {
      const r = await reverseAuctionApi.register(aid);
      toast.success(`You joined as ${r.alias}`);
      pollState();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const placeBid = async () => {
    if (!bidPrice) { toast.error("Enter a price"); return; }
    setBusy(true);
    try {
      const r = await reverseAuctionApi.bid(aid, parseFloat(bidPrice));
      toast.success(`Bid accepted at ${r.currency} ${r.current_price?.toLocaleString()}`);
      setBidPrice("");
      setState(r);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const setAutobid = async () => {
    if (!autoFloor) { toast.error("Set an auto-bid floor"); return; }
    setBusy(true);
    try {
      await reverseAuctionApi.autobid(aid, { floor: parseFloat(autoFloor), enabled: autoOn });
      toast.success(autoOn ? `Auto-bid armed with floor ${autoFloor}` : "Auto-bid disabled");
      pollState();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const secondsLeft = state?.status === "live"
    ? Math.max(0, Math.floor(((state.end_at ? new Date(state.end_at).getTime() : now) - now) / 1000))
    : 0;
  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const ss = String(secondsLeft % 60).padStart(2, "0");
  const cur = state?.current_price ?? state?.starting_price;
  const suggested = state ? Math.max(state.floor_price, (cur || 0) - (state.min_decrement || 0)) : 0;
  const iAmLeader = !!state?.me?.is_leader;
  const nextBidValid = bidPrice && parseFloat(bidPrice) <= cur - state.min_decrement + 1e-9 && parseFloat(bidPrice) >= state.floor_price;

  if (!state) {
    return (
      <div className="min-h-screen bg-brand-pale">
        <TopBar />
        <div className="max-w-4xl mx-auto px-6 py-16 text-brand-navy/60">Loading auction…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-pale" data-testid="vendor-auction-room">
      <TopBar />
      <main className="max-w-5xl mx-auto px-6 lg:px-10 py-8">
        <div className="pmc-label">Reverse Auction · {state.notice_ref}</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-1 text-brand-navy">{state.title}</h1>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Status</div>
            <div className={`mt-1 text-xl font-semibold ${state.status === "live" ? "text-emerald-700" : state.status === "closed" ? "text-slate-500" : "text-brand-navy"}`}>
              {state.status.toUpperCase()}
            </div>
            {state.status === "live" && (
              <div className="mt-2 font-mono text-2xl text-brand-navy tabular-nums" data-testid="ra-countdown">
                {mm}:{ss}
              </div>
            )}
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Current lowest</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy font-mono tabular-nums">
              {state.currency} {(cur ?? 0).toLocaleString()}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">Δ {state.min_decrement?.toLocaleString()} · floor {state.floor_price?.toLocaleString()}</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Leader</div>
            <div className={`mt-1 text-2xl font-semibold ${iAmLeader ? "text-emerald-700" : "text-brand-navy"}`}>
              {state.leader_alias || "—"}
              {iAmLeader && <span className="text-xs ml-2 uppercase tracking-widest text-emerald-700">(you)</span>}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">{state.participant_count} bidders registered</div>
          </div>
          <div className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">Your identity</div>
            <div className="mt-1 text-2xl font-semibold text-brand-navy">
              {state.me?.alias || "—"}
            </div>
            <div className="text-xs text-brand-navy/60 mt-1">Names are masked · nobody sees your company</div>
          </div>
        </div>

        {!state.me?.registered && state.status !== "closed" && (
          <div className="mt-6 border-2 border-amber-500 bg-amber-50 p-5 flex items-center justify-between flex-wrap gap-4">
            <div className="text-amber-900 text-sm">
              You are not yet registered for this auction. Click "Join" to receive a masked alias.
            </div>
            <button type="button" onClick={register} disabled={busy}
                    data-testid="ra-join"
                    className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-40">
              Join auction
            </button>
          </div>
        )}

        {state.me?.registered && state.status === "live" && (
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="border border-brand-navy/10 bg-white p-5">
              <div className="pmc-label">Place a manual bid</div>
              <input type="number" value={bidPrice}
                     onChange={(e) => setBidPrice(e.target.value)}
                     placeholder={`Suggested: ${suggested.toLocaleString()}`}
                     data-testid="ra-bid-price"
                     className="mt-2 w-full px-4 py-3 border border-brand-navy/20 font-mono tabular-nums text-lg" />
              <div className="text-xs text-brand-navy/60 mt-1">
                Must be ≤ {(cur - state.min_decrement).toLocaleString()} and ≥ {state.floor_price.toLocaleString()}
              </div>
              <button type="button" onClick={placeBid} disabled={busy || !nextBidValid}
                      data-testid="ra-bid-submit"
                      className="mt-3 w-full px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                {busy ? "Sending…" : "Place bid"}
              </button>
            </div>
            <div className="border border-brand-navy/10 bg-white p-5">
              <div className="pmc-label">Auto-bid — walk-away floor</div>
              <input type="number" value={autoFloor}
                     onChange={(e) => setAutoFloor(e.target.value)}
                     placeholder="e.g. 850000"
                     data-testid="ra-auto-floor"
                     className="mt-2 w-full px-4 py-3 border border-brand-navy/20 font-mono tabular-nums" />
              <label className="mt-2 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={autoOn} onChange={(e) => setAutoOn(e.target.checked)}
                       data-testid="ra-auto-enable" />
                Enable — auto-undercut competitors as long as I'm above this floor
              </label>
              <button type="button" onClick={setAutobid} disabled={busy}
                      data-testid="ra-auto-submit"
                      className="mt-3 w-full px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
                Save auto-bid config
              </button>
            </div>
          </div>
        )}

        <div className="mt-8 border border-brand-navy/10 bg-white">
          <div className="p-4 border-b border-brand-navy/10 text-sm text-brand-navy/70">
            Recent bids (masked)
          </div>
          {state.bids.length === 0 && <div className="p-6 text-brand-navy/40 text-sm">No bids yet.</div>}
          {state.bids.map((b, i) => (
            <div key={`${b.at}-${b.alias}-${b.price}`} className="p-3 border-b border-brand-navy/5 flex items-baseline gap-4"
                 data-testid={`ra-bid-row-${i}`}>
              <span className="font-mono text-xs text-brand-navy/50 w-32">{b.at?.slice(11, 19)}</span>
              <span className="text-sm font-semibold w-24">{b.alias}</span>
              <span className="font-mono tabular-nums text-brand-navy flex-1">
                {state.currency} {b.price?.toLocaleString()}
              </span>
              {b.auto && (
                <span className="text-[10px] uppercase tracking-widest text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5">
                  auto
                </span>
              )}
            </div>
          ))}
        </div>

        {state.status === "closed" && (
          <div className="mt-6 border-2 border-emerald-500 bg-emerald-50 p-6 text-emerald-900">
            <div className="pmc-label">Auction closed</div>
            <div className="mt-1 text-lg">
              Final price: <b>{state.currency} {(state.current_price ?? 0).toLocaleString()}</b>
              {" · "}Leader: <b>{state.leader_alias || "—"}</b>
              {iAmLeader && <span className="ml-2 text-emerald-700 font-semibold">— you won 🏆</span>}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
