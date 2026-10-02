import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { reverseAuctionApi, adminApi, showApiError } from "@/lib/api";
import AdminEShell from "./AdminEShell";

/**
 * v50m — Admin Reverse-Auctions tab (bug #39-41).
 * Lists every auction (draft / live / closed) with inline Start / Close
 * buttons that call the live backend; also provides a Create form bound
 * to a notice picker so new drafts actually appear in the list.
 */
export default function AdminAuctionsE() {
  const [rows, setRows] = useState([]);
  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    notice_ref: "", title: "", starting_price: 0, floor_price: 0,
    duration_minutes: 60, bid_decrement: 1000, currency: "USD",
  });
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, n] = await Promise.all([
        reverseAuctionApi.list(),
        adminApi.listAllNotices({ limit: 500 }).catch(() => ({ items: [] })),
      ]);
      setRows(a.items || []);
      setNotices(n.items || []);
    } catch (e) { showApiError(e); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!draft.notice_ref) { toast.error("Pick a notice first."); return; }
    if (!draft.title.trim()) { toast.error("Give the auction a title."); return; }
    if (Number(draft.floor_price) >= Number(draft.starting_price)) {
      toast.error("Floor price must be lower than starting price."); return;
    }
    try {
      await reverseAuctionApi.create({
        ...draft,
        starting_price: Number(draft.starting_price),
        floor_price: Number(draft.floor_price),
        duration_minutes: Number(draft.duration_minutes),
        bid_decrement: Number(draft.bid_decrement),
      });
      toast.success("Auction created as draft. Register ≥2 participants, then Start.");
      setShowNew(false);
      setDraft({ notice_ref: "", title: "", starting_price: 0, floor_price: 0,
                 duration_minutes: 60, bid_decrement: 1000, currency: "USD" });
      load();
    } catch (e) { showApiError(e); }
  };

  const start = async (aid) => {
    setBusyId(aid);
    try {
      await reverseAuctionApi.start(aid);
      toast.success("Auction is now LIVE.");
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot start auction" }); }
    finally { setBusyId(null); }
  };
  const close = async (aid) => {
    setBusyId(aid);
    try {
      const res = await reverseAuctionApi.close(aid);
      toast.success(res.already_closed ? "Auction was already closed." : "Auction closed.");
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot close auction" }); }
    finally { setBusyId(null); }
  };

  const pill = (s) => {
    const cls = { draft: "pmc-pill", live: "pmc-pill pmc-pill--success",
                  closed: "pmc-pill pmc-pill--info" }[s] || "pmc-pill";
    return <span className={cls} data-testid={`auction-status-${s}`}>{s}</span>;
  };

  return (
    <AdminEShell active="Reverse auctions"
                 crumb={<>Money &amp; compliance / <b>Reverse auctions</b></>}>
      <div className="p-6" data-testid="admin-auctions-e">
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl font-serif">Reverse auctions</h1>
            <div className="text-sm text-brand-navy/60 mt-1">
              Live descending-price rounds. Draft → ≥2 participants registered → Start → bidders drive price down → Close.
            </div>
          </div>
          <button type="button" onClick={() => setShowNew((v) => !v)}
                  data-testid="admin-auction-new-toggle"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showNew ? "Cancel" : "New auction"}
          </button>
        </div>

        {showNew && (
          <div className="border border-brand-navy/20 bg-white p-5 grid gap-3 md:grid-cols-3 mb-5"
               data-testid="admin-auction-new-form">
            <label className="md:col-span-2"><span className="pmc-label">Notice</span>
              <select value={draft.notice_ref}
                      onChange={(e) => setDraft({ ...draft, notice_ref: e.target.value })}
                      data-testid="auction-notice-picker"
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-brand-navy">
                <option value="">— pick a notice —</option>
                {notices.map((n) => (
                  <option key={n.id || n.notice_ref} value={n.notice_ref}>
                    {n.notice_ref} — {n.title}
                  </option>
                ))}
              </select>
            </label>
            <label><span className="pmc-label">Currency</span>
              <select value={draft.currency}
                      onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-brand-navy">
                {["USD","EUR","GBP","INR","KZT","AED"].map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label className="md:col-span-3"><span className="pmc-label">Title</span>
              <input value={draft.title}
                     onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                     placeholder="e.g. OPD Renovation — Round 1"
                     data-testid="auction-title-input"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Starting price</span>
              <input type="number" value={draft.starting_price}
                     onChange={(e) => setDraft({ ...draft, starting_price: e.target.value })}
                     data-testid="auction-start-price"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Floor price</span>
              <input type="number" value={draft.floor_price}
                     onChange={(e) => setDraft({ ...draft, floor_price: e.target.value })}
                     data-testid="auction-floor-price"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Bid decrement</span>
              <input type="number" value={draft.bid_decrement}
                     onChange={(e) => setDraft({ ...draft, bid_decrement: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Duration (minutes)</span>
              <input type="number" value={draft.duration_minutes}
                     onChange={(e) => setDraft({ ...draft, duration_minutes: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <div className="md:col-span-3 flex justify-end">
              <button onClick={create} data-testid="auction-create-btn"
                      className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
                Create draft auction
              </button>
            </div>
          </div>
        )}

        {loading && <div className="p-6 text-sm text-brand-navy/50">Loading auctions…</div>}
        {!loading && rows.length === 0 && (
          <div className="p-8 text-sm text-brand-navy/50 bg-white border border-brand-navy/10 text-center"
               data-testid="admin-auction-empty">
            No reverse auctions yet. Click "New auction" to create your first one.
          </div>
        )}

        {!loading && rows.length > 0 && (
          <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10"
               data-testid="admin-auction-list">
            {rows.map((a) => (
              <div key={a.id} className="p-4 grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto] items-center"
                   data-testid={`auction-row-${a.id}`}>
                <div className="min-w-0">
                  <div className="font-semibold text-brand-navy">{a.title}</div>
                  <div className="text-xs text-brand-navy/60 font-mono">
                    {a.notice_ref} · created {a.created_at?.slice(0, 10)}
                  </div>
                </div>
                <div className="text-xs">
                  <div className="pmc-label">Start → Floor</div>
                  <div className="font-mono">
                    {a.currency} {Number(a.starting_price).toLocaleString()} →{" "}
                    {Number(a.floor_price).toLocaleString()}
                  </div>
                </div>
                <div>{pill(a.status)}</div>
                <div className="flex gap-2 justify-end">
                  {a.status === "draft" && (
                    <button type="button" onClick={() => start(a.id)}
                            disabled={busyId === a.id}
                            data-testid={`auction-start-${a.id}`}
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50">
                      {busyId === a.id ? "…" : "Start"}
                    </button>
                  )}
                  {a.status === "live" && (
                    <button type="button" onClick={() => close(a.id)}
                            disabled={busyId === a.id}
                            data-testid={`auction-close-${a.id}`}
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">
                      {busyId === a.id ? "…" : "Close"}
                    </button>
                  )}
                  <a href={`/auctions/${a.id}/live`}
                     target="_blank" rel="noopener noreferrer"
                     data-testid={`auction-open-${a.id}`}
                     className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                    Open room
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminEShell>
  );
}
