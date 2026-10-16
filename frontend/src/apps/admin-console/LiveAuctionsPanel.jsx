import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { reverseAuctionApi, publicApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import AuctionInvitations from "./auction/AuctionInvitations";
import { useListPager } from "@/components/ListPager";
import CreatorDateFilterBar, { matchCreatorDate, creatorDateParams } from "@/components/CreatorDateFilterBar";

/** Wave 40 — Admin live-auction management. */
export default function LiveAuctionsPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [notices, setNotices] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [summaryFor, setSummaryFor] = useState(null);  // RA-01 fix
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState({
    notice_ref: "", title: "", currency: "USD",
    starting_price: 1000000, floor_price: 800000,
    min_decrement: 5000, duration_minutes: 30, anti_snipe_seconds: 120,
  });

  // v52w — Created by / from / to pushed to the API (client-side match below
  // kept as an instant fallback while the refetch is in flight).
  const [cdf, setCdf] = useState({ createdBy: "", from: "", to: "" });
  const load = useCallback(() => {
    reverseAuctionApi.list(creatorDateParams(cdf)).then((d) => setItems(d.items || []))
      .catch((e) => showApiError(e));
  }, [cdf]);

  useEffect(() => {
    load();
    publicApi.listNotices({ limit: 200 })
      .then((d) => setNotices(d.items || []))
      .catch(() => {});
  }, [load]);

  const create = async () => {
    if (!draft.notice_ref) { toast.error("Pick a notice"); return; }
    if (!draft.title || draft.title.length < 3) { toast.error("Title must be at least 3 characters"); return; }
    // v52by — coerce every numeric field to a valid number so the backend's
    // Pydantic validator never sees NaN (was returning 'field required' when
    // the admin cleared a field). Zero/empty floor_price is accepted now.
    const payload = {
      ...draft,
      starting_price: Number(draft.starting_price) || 0,
      floor_price:    Number(draft.floor_price) || 0,
      min_decrement:  Number(draft.min_decrement) || 1,
      duration_minutes: Number(draft.duration_minutes) || 30,
      anti_snipe_seconds: Number(draft.anti_snipe_seconds) || 0,
    };
    if (payload.starting_price <= 0) { toast.error("Starting price must be > 0"); return; }
    if (payload.floor_price >= payload.starting_price) { toast.error("Floor price must be lower than starting price"); return; }
    try {
      const r = await reverseAuctionApi.create(payload);
      toast.success(`Auction drafted · ${r.id}`);
      setShowNew(false);
      // v52by — pre-pend the new draft so admins see it instantly without
      // waiting for the refetch (addresses "draft not listed").
      setItems((cur) => [{ ...r, participant_count: 0 }, ...cur.filter((x) => x.id !== r.id)]);
      load();
    } catch (e) { showApiError(e); }
  };

  const start = async (aid) => {
    try {
      const r = await reverseAuctionApi.start(aid);
      toast.success(`Started · ends ${r.end_at?.slice(11, 16)} UTC`);
      load();
    } catch (e) { showApiError(e); }
  };

  const close = async (aid) => {
    if (!window.confirm(t("panels.live_auctions.close_confirm"))) return;
    try {
      const r = await reverseAuctionApi.close(aid);
      toast.success(r.winner ? `Closed · winner ${r.winner.alias} @ ${r.winner.winning_price}` : "Closed (no bids)");
      load();
    } catch (e) { showApiError(e); }
  };

  const badge = (status) => ({
    draft: "bg-gray-100 text-gray-700 border-gray-300",
    live:  "bg-emerald-100 text-emerald-800 border-emerald-300",
    closed:"bg-slate-200 text-slate-700 border-slate-400",
  }[status] || "");

  const q = search.trim().toLowerCase();
  // v52v — Created by / from / to added alongside the existing status + search.
  const auctionCreators = useMemo(() => items.map((a) => a.created_by_email || a.created_by).filter(Boolean), [items]);
  const matchCdf = useMemo(() => matchCreatorDate(cdf), [cdf]);
  const filtered = items.filter((a) =>
    (statusFilter === "all" || a.status === statusFilter)
    && (!q || (a.title || "").toLowerCase().includes(q)
          || (a.notice_ref || "").toLowerCase().includes(q))
    && matchCdf(a)
  );
  const { paged, controls } = useListPager(filtered, { testid: "ra-pager" });

  return (
    <div data-testid="admin-live-auctions">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">
          {t("panels.live_auctions.hint")}
        </div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="ra-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? t("panels.live_auctions.cancel") : t("panels.live_auctions.new_button")}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2"
             data-testid="ra-new-form">
          <label className="col-span-2"><span className="pmc-label">{t("panels.live_auctions.notice")}<InfoDot tip="Which notice this reverse auction serves. Only bidders who submitted a bid on that notice can join." /></span>
            <select value={draft.notice_ref} onChange={(e) => setDraft({ ...draft, notice_ref: e.target.value })}
                    data-testid="ra-notice"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">{t("panels.live_auctions.pick_notice")}</option>
              {notices.map((n) => (
                <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
              ))}
            </select>
          </label>
          <label className="col-span-2"><span className="pmc-label">{t("panels.live_auctions.title_public")}<InfoDot tip="Public title bidders will see in the live room. Keep it short (e.g. 'Round-2 e-Auction · Substation SS-401')." /></span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                   data-testid="ra-title"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.currency")}<InfoDot tip="Currency for all price fields below. Cannot be changed once the auction goes live." /></span>
            <select value={draft.currency} onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              {["USD","GBP","EUR","KZT","INR","AED","SAR"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.live_auctions.starting_price")}<InfoDot tip="Opening ceiling price. Bidders must bid strictly below this to place a valid bid." /></span>
            <input type="number" value={draft.starting_price}
                   onChange={(e) => setDraft({ ...draft, starting_price: parseFloat(e.target.value) })}
                   data-testid="ra-start-price"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.floor_price")}<InfoDot tip="Absolute minimum price. Bids at or below this trigger a floor-reached alert; below this the bid is rejected." /></span>
            <input type="number" value={draft.floor_price}
                   onChange={(e) => setDraft({ ...draft, floor_price: parseFloat(e.target.value) })}
                   data-testid="ra-floor"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.min_decrement")}<InfoDot tip="Smallest allowed step-down from the current leading price. Prevents shill bids of ±1." /></span>
            <input type="number" value={draft.min_decrement}
                   onChange={(e) => setDraft({ ...draft, min_decrement: parseFloat(e.target.value) })}
                   data-testid="ra-decrement"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.duration_min")}<InfoDot tip="Auction duration in minutes from the moment you press Start." /></span>
            <input type="number" value={draft.duration_minutes}
                   onChange={(e) => setDraft({ ...draft, duration_minutes: parseInt(e.target.value, 10) })}
                   data-testid="ra-duration"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.antisnipe_sec")}<InfoDot tip="If a valid bid arrives within this many seconds of the end, the clock is extended. Prevents last-second sniping." /></span>
            <input type="number" value={draft.anti_snipe_seconds}
                   onChange={(e) => setDraft({ ...draft, anti_snipe_seconds: parseInt(e.target.value, 10) })}
                   data-testid="ra-antisnipe"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" />
            <span className="text-xs text-brand-navy/50 mt-1 block">
              {t("panels.live_auctions.antisnipe_hint_prefix")} {draft.anti_snipe_seconds}{t("panels.live_auctions.antisnipe_hint_suffix")}
            </span>
          </label>
          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={create} data-testid="ra-create"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              {t("panels.live_auctions.draft_button")}
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-center mb-3" data-testid="ra-filter-bar">
        {[["all","All"],["draft","Draft"],["live","Live"],["closed","Closed"]].map(([k,l]) => (
          <button key={k} type="button" onClick={() => setStatusFilter(k)}
            data-testid={`ra-filter-${k}`}
            className={`px-3 py-1 text-[11px] uppercase tracking-widest border ${
              statusFilter === k ? "bg-brand-navy text-white border-brand-navy"
                : "border-brand-navy/20 text-brand-navy/70 hover:border-brand-navy"}`}>
            {l}
          </button>
        ))}
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title or notice ref…"
          data-testid="ra-search"
          className="flex-1 min-w-[220px] px-3 py-1.5 border border-brand-navy/20 text-sm bg-white" />
      </div>

      <CreatorDateFilterBar value={cdf} onChange={setCdf} creators={auctionCreators} testid="ra-cdf" />

      <div className="border border-brand-navy/10 bg-white">
        {filtered.length === 0 ? (
          <div className="p-6 text-brand-navy/50 text-sm">
            {items.length === 0 ? t("panels.live_auctions.empty") : "No matches"}
          </div>
        ) : paged.map((a) => {
          const url = `${window.location.origin}/vendor/auction/${a.id}`;
          return (
            <div key={a.id} className="p-4 border-b border-brand-navy/10" data-testid={`ra-row-${a.id}`}>
              <div className="flex items-baseline gap-4 flex-wrap">
                <span className={`text-[10px] uppercase tracking-widest px-2 py-1 border ${badge(a.status)}`}>{a.status}</span>
                <span className="font-mono text-xs text-brand-navy-soft">{a.notice_ref}</span>
                <span className="text-sm font-semibold text-brand-navy flex-1">{a.title}</span>
                <span className="text-xs text-brand-navy/60 font-mono">
                  {a.currency} · start {a.starting_price?.toLocaleString()} → floor {a.floor_price?.toLocaleString()} · Δ {a.min_decrement?.toLocaleString()}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 gap-y-2 text-xs">
                {a.status === "draft" ? (
                  <span className="text-[11px] text-brand-navy/50 italic flex-1">
                    Bidder link is hidden until you Start the auction — vendors will
                    only receive the public URL after it goes live.
                  </span>
                ) : (
                  <>
                    <span className="text-brand-navy/60">{t("panels.live_auctions.bidder_link")}</span>
                    <input readOnly value={url}
                           className="flex-1 px-2 py-1 border border-brand-navy/15 font-mono text-[11px] bg-brand-pale" />
                    <button type="button"
                            onClick={() => { navigator.clipboard?.writeText(url); toast.success(t("panels.live_auctions.link_copied")); }}
                            className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 hover:bg-brand-navy hover:text-white">
                      {t("panels.live_auctions.copy")}
                    </button>
                  </>
                )}
                {a.status === "draft" && (
                  <button type="button"
                          onClick={() => start(a.id)}
                          title={((a.participant_count ?? a.participants?.length ?? 0) < 2) ? "Only 0-1 vendor has registered. You can still Start — the backend will refuse with a clear message naming the gate." : "Start the auction now"}
                          data-testid={`ra-start-${a.id}`}
                          className="text-[10px] uppercase tracking-widest px-3 py-1 text-white bg-emerald-600 hover:bg-emerald-700">
                    {t("panels.live_auctions.start")} · {(a.participant_count ?? a.participants?.length ?? 0)}/2
                  </button>
                )}
                {a.status === "live" && (
                  <button type="button" onClick={() => close(a.id)}
                          data-testid={`ra-close-${a.id}`}
                          className="text-[10px] uppercase tracking-widest px-3 py-1 bg-red-600 text-white hover:bg-red-700">
                    {t("panels.live_auctions.close")}
                  </button>
                )}
                {a.status === "closed" && a.winner && (
                  <span className="text-[11px] text-emerald-800 font-mono">
                    {t("panels.live_auctions.winner_prefix")} {a.winner.alias} · {a.currency} {a.winner.winning_price?.toLocaleString()}
                  </span>
                )}
                {/* v53b — award hand-off: push the winner into the standard
                    bid pipeline (emd_paid → escrow → certifier → legal →
                    accounting → awarded). Idempotent on the backend. */}
                {a.status === "closed" && a.winner && !a.awarded_bid_id && (
                  <button type="button"
                          onClick={async () => {
                            try {
                              const r = await reverseAuctionApi.award(a.id);
                              toast.success(r.already_awarded
                                ? `Already awarded — bid ${r.bid_id}`
                                : `Bid ${r.bid_ref} created at emd_paid — continue in Bidding Ops`);
                              load();
                            } catch (e) { showApiError(e); }
                          }}
                          data-testid={`ra-award-${a.id}`}
                          className="text-[10px] uppercase tracking-widest px-3 py-1 text-white bg-brand-navy hover:bg-brand-navy-deep">
                    Award winner
                  </button>
                )}
                {a.status === "closed" && a.awarded_bid_id && (
                  <span className="text-[10px] uppercase tracking-widest px-2 py-1 border border-emerald-600 text-emerald-700"
                        data-testid={`ra-awarded-${a.id}`}>
                    Awarded · in pipeline
                  </span>
                )}
                {/* RA-01 fix — post-auction summary report */}
                {a.status === "closed" && (
                  <button type="button" onClick={() => setSummaryFor(summaryFor === a.id ? null : a.id)}
                          data-testid={`ra-summary-${a.id}`}
                          className="text-[10px] uppercase tracking-widest px-3 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                    {summaryFor === a.id ? "Hide summary" : "View summary"}
                  </button>
                )}
              </div>
              {a.status === "closed" && summaryFor === a.id && (
                <div className="mt-3 border-t border-brand-navy/10 pt-3 grid gap-3 md:grid-cols-4 text-xs"
                     data-testid={`ra-summary-panel-${a.id}`}>
                  <div><div className="pmc-label">Starting</div><div className="font-mono">{a.currency} {a.starting_price?.toLocaleString()}</div></div>
                  <div><div className="pmc-label">Floor</div><div className="font-mono">{a.currency} {a.floor_price?.toLocaleString()}</div></div>
                  <div><div className="pmc-label">Winning bid</div><div className="font-mono text-emerald-800">{a.currency} {(a.winner?.winning_price ?? "—").toLocaleString?.() ?? "—"}</div></div>
                  <div><div className="pmc-label">Savings vs start</div><div className="font-mono">
                    {a.winner?.winning_price
                      ? `${(((a.starting_price - a.winner.winning_price) / a.starting_price) * 100).toFixed(1)}%`
                      : "—"}
                  </div></div>
                  <div className="md:col-span-4"><div className="pmc-label mb-1">Winner</div>
                    <div>{a.winner ? `${a.winner.alias} — awarded at ${a.winner.winning_price?.toLocaleString()} ${a.currency}` : "No participants"}</div>
                  </div>
                  <div className="md:col-span-4"><div className="pmc-label mb-1">Timing</div>
                    <div className="text-brand-navy/70">
                      Duration {a.duration_minutes} min · anti-snipe {a.anti_snipe_seconds}s · closed {a.closed_at?.slice(0, 19).replace("T", " ") || "—"} UTC
                    </div>
                  </div>
                </div>
              )}
              {a.status !== "closed" && <AuctionInvitations auctionId={a.id} />}
            </div>
          );
        })}
        {controls}
      </div>
    </div>
  );
}
