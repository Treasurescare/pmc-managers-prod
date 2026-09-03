import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { reverseAuctionApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/** Wave 40 — Admin live-auction management. */
export default function LiveAuctionsPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [notices, setNotices] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    notice_ref: "", title: "", currency: "USD",
    starting_price: 1000000, floor_price: 800000,
    min_decrement: 5000, duration_minutes: 30, anti_snipe_seconds: 120,
  });

  const load = useCallback(() => {
    reverseAuctionApi.list().then((d) => setItems(d.items || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, []);

  useEffect(() => {
    load();
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=200`)
      .then((r) => r.json())
      .then((d) => setNotices(d.items || []))
      .catch(() => {});
  }, [load]);

  const create = async () => {
    if (!draft.notice_ref) { toast.error("Pick a notice"); return; }
    if (!draft.title) { toast.error("Title required"); return; }
    try {
      const r = await reverseAuctionApi.create(draft);
      toast.success(`Auction drafted · ${r.id}`);
      setShowNew(false);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const start = async (aid) => {
    try {
      const r = await reverseAuctionApi.start(aid);
      toast.success(`Started · ends ${r.end_at?.slice(11, 16)} UTC`);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const close = async (aid) => {
    if (!window.confirm(t("panels.live_auctions.close_confirm"))) return;
    try {
      const r = await reverseAuctionApi.close(aid);
      toast.success(r.winner ? `Closed · winner ${r.winner.alias} @ ${r.winner.winning_price}` : "Closed (no bids)");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const badge = (status) => ({
    draft: "bg-gray-100 text-gray-700 border-gray-300",
    live:  "bg-emerald-100 text-emerald-800 border-emerald-300",
    closed:"bg-slate-200 text-slate-700 border-slate-400",
  }[status] || "");

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
          <label className="col-span-2"><span className="pmc-label">{t("panels.live_auctions.notice")}</span>
            <select value={draft.notice_ref} onChange={(e) => setDraft({ ...draft, notice_ref: e.target.value })}
                    data-testid="ra-notice"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">{t("panels.live_auctions.pick_notice")}</option>
              {notices.map((n) => (
                <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
              ))}
            </select>
          </label>
          <label className="col-span-2"><span className="pmc-label">{t("panels.live_auctions.title_public")}</span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                   data-testid="ra-title"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.currency")}</span>
            <select value={draft.currency} onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              {["USD","GBP","EUR","KZT","INR","AED","SAR"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label><span className="pmc-label">{t("panels.live_auctions.starting_price")}</span>
            <input type="number" value={draft.starting_price}
                   onChange={(e) => setDraft({ ...draft, starting_price: parseFloat(e.target.value) })}
                   data-testid="ra-start-price"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.floor_price")}</span>
            <input type="number" value={draft.floor_price}
                   onChange={(e) => setDraft({ ...draft, floor_price: parseFloat(e.target.value) })}
                   data-testid="ra-floor"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.min_decrement")}</span>
            <input type="number" value={draft.min_decrement}
                   onChange={(e) => setDraft({ ...draft, min_decrement: parseFloat(e.target.value) })}
                   data-testid="ra-decrement"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.duration_min")}</span>
            <input type="number" value={draft.duration_minutes}
                   onChange={(e) => setDraft({ ...draft, duration_minutes: parseInt(e.target.value, 10) })}
                   data-testid="ra-duration"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">{t("panels.live_auctions.antisnipe_sec")}</span>
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

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">{t("panels.live_auctions.empty")}</div>}
        {items.map((a) => {
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
              <div className="mt-2 flex items-center gap-3 text-xs">
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
                  <button type="button" onClick={() => start(a.id)}
                          data-testid={`ra-start-${a.id}`}
                          className="text-[10px] uppercase tracking-widest px-3 py-1 bg-emerald-600 text-white hover:bg-emerald-700">
                    {t("panels.live_auctions.start")}
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
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
