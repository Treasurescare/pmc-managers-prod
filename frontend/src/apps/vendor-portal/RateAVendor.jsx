import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { vendorRatingsApi, showApiError } from "@/lib/api";
import { VendorTrustBadge } from "@/components/VendorTrustBadge";

/**
 * v46y — Rate a peer vendor.
 *
 * Flow: pick a tender you co-participated in → pick a co-participant vendor →
 * score them on each criterion (1-10 range from the platform rubric) → submit.
 * Backend enforces the co-participation gate independently.
 */
export default function RateAVendor({ me }) {
  const [tenders, setTenders]         = useState([]);
  const [tenderRef, setTenderRef]     = useState("");
  const [vendors, setVendors]         = useState([]);
  const [q, setQ]                     = useState("");
  const [selected, setSelected]       = useState(null);
  const [aggregate, setAggregate]     = useState(null);
  const [criteriaSet, setCriteriaSet] = useState(null);
  const [scores, setScores]           = useState({});
  const [comment, setComment]         = useState("");
  const [busy, setBusy]               = useState(false);
  const [myReviews, setMyReviews]     = useState([]);

  const loadTenders = useCallback(async () => {
    try { setTenders(await vendorRatingsApi.peerMyTenders() || []); }
    catch { setTenders([]); }
  }, []);

  const loadDirectory = useCallback(async () => {
    if (!tenderRef) { setVendors([]); return; }
    try { setVendors(await vendorRatingsApi.peerDirectory(null, tenderRef) || []); }
    catch (e) { showApiError(e); setVendors([]); }
  }, [tenderRef]);

  const loadRubric = useCallback(async () => {
    try {
      const rub = await vendorRatingsApi.publicRubric();
      setCriteriaSet(rub);
      const init = {};
      (rub.criteria || []).forEach((c) => { init[c.code] = c.scale_min; });
      setScores(init);
    } catch { setCriteriaSet(null); }
  }, []);

  const loadMine = useCallback(async () => {
    try { setMyReviews(await vendorRatingsApi.peerListMine()); }
    catch { setMyReviews([]); }
  }, []);

  useEffect(() => { loadTenders(); loadRubric(); loadMine(); },
           [loadTenders, loadRubric, loadMine]);
  useEffect(() => { loadDirectory(); setSelected(null); setAggregate(null); },
           [loadDirectory]);

  const loadAggregate = async (ref) => {
    try { setAggregate(await vendorRatingsApi.publicAggregate(ref)); }
    catch (e) { showApiError(e); }
  };

  const submit = async () => {
    if (!tenderRef)  return toast.error("Pick the tender you co-participated on first.");
    if (!selected)   return toast.error("Pick a vendor to rate.");
    if (!criteriaSet) return toast.error("No rating rubric configured. Ask PMC admin.");
    setBusy(true);
    try {
      const res = await vendorRatingsApi.peerSubmit({
        vendor_ref: selected.vendor_ref,
        criteria_set_id: criteriaSet.id,
        tender_ref: tenderRef,
        scores,
        comment: comment.trim() || null,
      });
      toast.success(res.status === "approved"
        ? "Review published anonymously. Thank you!"
        : "Review submitted — pending PMC moderation.");
      setComment("");
      await loadAggregate(selected.vendor_ref);
      await loadMine();
    } catch (e) { showApiError(e, { fallbackTitle: "Could not submit review" }); }
    finally { setBusy(false); }
  };

  const filteredVendors = vendors.filter((v) => {
    if (!q.trim()) return true;
    const s = q.trim().toLowerCase();
    return (v.company_name || "").toLowerCase().includes(s)
        || (v.vendor_ref || "").toLowerCase().includes(s);
  });

  return (
    <div className="space-y-5" data-testid="rate-a-vendor">
      {/* Tender picker */}
      <section className="bg-white border p-4">
        <div className="pmc-label mb-2">Step 1 · Which tender did you co-participate on?</div>
        {tenders.length === 0 ? (
          <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 p-3">
            You haven't submitted a bid on any live tender yet, so there is no
            peer to rate. Once you and another vendor both bid on the same
            notice you can rate each other here.
          </div>
        ) : (
          <select value={tenderRef} onChange={(e) => setTenderRef(e.target.value)}
                  data-testid="rav-tender-picker"
                  className="w-full px-3 py-2 border text-sm">
            <option value="">— Select tender —</option>
            {tenders.map((t) => (
              <option key={t.notice_ref} value={t.notice_ref}>
                {t.notice_ref} · {t.title} · {t.co_participant_count} co-bidder{t.co_participant_count === 1 ? "" : "s"}
              </option>
            ))}
          </select>
        )}
      </section>

      {tenderRef && (
        <div className="grid gap-5 lg:grid-cols-[3fr_5fr]">
          {/* Directory */}
          <section className="bg-white border">
            <div className="p-3 border-b">
              <div className="pmc-label mb-1">Step 2 · Pick a co-participant</div>
              <input value={q} onChange={(e) => setQ(e.target.value)}
                     data-testid="rav-search"
                     placeholder="Filter by name or ref"
                     className="w-full px-3 py-2 border text-sm" />
            </div>
            <div className="max-h-[520px] overflow-y-auto">
              {filteredVendors.length === 0 && (
                <div className="p-6 text-sm text-slate-500">
                  No other vendors bid on this tender yet.
                </div>
              )}
              {filteredVendors.map((v) => (
                <button key={v.vendor_ref}
                        onClick={() => { setSelected(v); loadAggregate(v.vendor_ref); }}
                        data-testid={`rav-vendor-${v.vendor_ref}`}
                        className={`w-full text-left p-3 border-b hover:bg-slate-50 transition ${selected?.vendor_ref === v.vendor_ref ? "bg-slate-50" : ""}`}>
                  <div className="text-sm font-semibold text-brand-navy">{v.company_name}</div>
                  <div className="text-xs text-slate-500 font-mono">{v.vendor_ref}</div>
                </button>
              ))}
            </div>
          </section>

          {/* Rating form */}
          <section className="bg-white border">
            {!selected ? (
              <div className="p-8 text-sm text-slate-500">
                Select a vendor on the left to score them. All reviews are anonymous —
                only your reviewer type ("peer vendor") is shown publicly.
              </div>
            ) : (
              <div className="p-5 space-y-5">
                <div className="flex flex-wrap items-baseline gap-3">
                  <div>
                    <div className="text-xs uppercase tracking-widest text-brand-navy-soft">{selected.vendor_ref}</div>
                    <div className="font-display text-2xl text-brand-navy">{selected.company_name}</div>
                  </div>
                  {aggregate && (
                    <VendorTrustBadge tier={aggregate.badge}
                                        score={aggregate.average_score ?? "—"}
                                        count={aggregate.count}
                                        testid="rav-current-badge" />
                  )}
                </div>

                {!criteriaSet ? (
                  <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 p-3">
                    No rating rubric configured yet. Ask PMC admin to publish
                    one (Masters → Rating &amp; Fees).
                  </div>
                ) : (
                  <div className="grid gap-2">
                    <div className="pmc-label">Step 3 · Score each parameter (1–{(criteriaSet.criteria || [{scale_max:10}])[0]?.scale_max ?? 10})</div>
                    {(criteriaSet.criteria || []).map((c) => (
                      <div key={c.code} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 border-b border-brand-navy/5 py-2">
                        <div>
                          <div className="text-sm text-brand-navy">{c.label}</div>
                          {c.description && <div className="text-xs text-brand-navy/50">{c.description}</div>}
                        </div>
                        <input type="range" min={c.scale_min} max={c.scale_max} step={1}
                               value={scores[c.code] ?? c.scale_min}
                               onChange={(e) => setScores({ ...scores, [c.code]: parseInt(e.target.value, 10) })}
                               data-testid={`rav-score-${c.code}`}
                               className="w-40" />
                        <span className="font-mono text-brand-navy w-14 text-right">
                          {scores[c.code] ?? c.scale_min}/{c.scale_max}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <label className="block text-xs uppercase tracking-widest text-brand-navy/60">
                  Comment (optional)
                  <textarea value={comment} onChange={(e) => setComment(e.target.value)}
                            rows={3} maxLength={2000}
                            data-testid="rav-comment"
                            className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
                </label>

                <div className="flex justify-end">
                  <button onClick={submit} disabled={busy || !criteriaSet}
                          data-testid="rav-submit"
                          className="px-6 py-3 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                    {busy ? "Submitting…" : "Submit anonymous review"}
                  </button>
                </div>
              </div>
            )}

            {myReviews.length > 0 && (
              <div className="border-t p-5">
                <div className="pmc-label mb-2">Your recent reviews</div>
                <div className="space-y-2">
                  {myReviews.slice(0, 5).map((r) => (
                    <div key={r.id} className="text-sm border-b py-2" data-testid={`rav-history-${r.id}`}>
                      <div className="flex justify-between text-xs text-slate-500">
                        <span className="font-mono">{r.vendor_ref}</span>
                        <span>{(r.created_at || "").slice(0, 10)}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-3">
                        <span className="font-mono">{r.score_out_of_100}/100</span>
                        <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 ${r.status === "approved" ? "bg-emerald-100 text-emerald-800" : r.status === "pending" ? "bg-amber-100 text-amber-800" : "bg-slate-200 text-slate-600"}`}>
                          {r.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
