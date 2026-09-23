import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { vendorRatingsApi, showApiError } from "@/lib/api";
import { VendorTrustBadge } from "@/components/VendorTrustBadge";

/**
 * v46 — "Rate a peer" tab embedded on the vendor dashboard.
 *
 * A signed-in vendor can rate ANY other vendor. Self-rating is blocked by both
 * frontend guard and backend. Reviews from verified vendors are auto-approved.
 */
export default function RateAVendor({ me }) {
  const [vendors, setVendors]         = useState([]);
  const [q, setQ]                     = useState("");
  const [selected, setSelected]       = useState(null);
  const [aggregate, setAggregate]     = useState(null);
  const [criteriaSet, setCriteriaSet] = useState(null);
  const [scores, setScores]           = useState({});
  const [comment, setComment]         = useState("");
  const [busy, setBusy]               = useState(false);
  const [myReviews, setMyReviews]     = useState([]);

  const loadDirectory = useCallback(async () => {
    try {
      const list = await vendorRatingsApi.peerDirectory();
      setVendors(list || []);
    } catch (e) {
      showApiError(e);
      setVendors([]);
    }
  }, []);

  const loadRubric = useCallback(async () => {
    try {
      const rub = await vendorRatingsApi.publicRubric();
      setCriteriaSet(rub);
      const init = {};
      (rub.criteria || []).forEach((c) => { init[c.code] = c.scale_min; });
      setScores(init);
    } catch {
      setCriteriaSet(null);
    }
  }, []);

  const loadMine = useCallback(async () => {
    try { setMyReviews(await vendorRatingsApi.peerListMine()); }
    catch { setMyReviews([]); }
  }, []);

  useEffect(() => { loadDirectory(); loadRubric(); loadMine(); },
           [loadDirectory, loadRubric, loadMine]);

  const loadAggregate = async (ref) => {
    try { setAggregate(await vendorRatingsApi.publicAggregate(ref)); }
    catch (e) { showApiError(e); }
  };

  const submit = async () => {
    if (!selected) return toast.error("Pick a vendor to rate first");
    if (!criteriaSet) return toast.error("No rating rubric configured");
    setBusy(true);
    try {
      const res = await vendorRatingsApi.peerSubmit({
        vendor_ref: selected.vendor_ref,
        criteria_set_id: criteriaSet.id,
        scores,
        comment: comment.trim() || null,
      });
      toast.success(res.status === "approved"
        ? "Review published anonymously. Thank you!"
        : "Review submitted — pending PMC moderation.");
      setComment("");
      await loadAggregate(selected.vendor_ref);
      await loadMine();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const filteredVendors = vendors.filter((v) => {
    if (!q.trim()) return true;
    const s = q.trim().toLowerCase();
    return (v.company_name || "").toLowerCase().includes(s)
        || (v.vendor_ref || "").toLowerCase().includes(s)
        || (v.email || "").toLowerCase().includes(s);
  }).slice(0, 50);

  return (
    <div className="grid gap-6 lg:grid-cols-[3fr_5fr]" data-testid="rate-a-vendor">
      {/* Directory */}
      <section className="bg-white border">
        <div className="p-3 border-b">
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 data-testid="rav-search"
                 placeholder="Search vendors by name, ref or email"
                 className="w-full px-3 py-2 border text-sm" />
        </div>
        <div className="max-h-[520px] overflow-y-auto">
          {filteredVendors.length === 0 && (
            <div className="p-6 text-sm text-slate-500">
              No vendors to display. Ask PMC admin to share vendor references if
              you're rating from outside the directory.
            </div>
          )}
          {filteredVendors.map((v) => (
            <button key={v.vendor_ref}
                    onClick={() => { setSelected(v); loadAggregate(v.vendor_ref); }}
                    data-testid={`rav-vendor-${v.vendor_ref}`}
                    className={`w-full text-left p-3 border-b hover:bg-slate-50 transition ${selected?.vendor_ref === v.vendor_ref ? "bg-slate-50" : ""}`}>
              <div className="text-sm font-semibold text-brand-navy">{v.company_name || v.email}</div>
              <div className="text-xs text-slate-500 font-mono">{v.vendor_ref}</div>
            </button>
          ))}
        </div>
      </section>

      {/* Rating form */}
      <section className="bg-white border">
        {!selected ? (
          <div className="p-8 text-sm text-slate-500">
            Select a vendor from the left to rate them. All submissions are anonymous:
            only your reviewer type ("peer vendor") is shown publicly.
          </div>
        ) : (
          <div className="p-5 space-y-5">
            <div className="flex flex-wrap items-baseline gap-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-brand-navy-soft">
                  {selected.vendor_ref}
                </div>
                <div className="font-display text-2xl text-brand-navy">{selected.company_name || selected.email}</div>
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
                No rating rubric configured yet. Ask PMC admin to publish a rubric
                (Masters → Rating &amp; Fees).
              </div>
            ) : (
              <div className="grid gap-2">
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
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} maxLength={2000}
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

        {/* History */}
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
  );
}
