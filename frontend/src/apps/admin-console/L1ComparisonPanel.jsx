import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { comparisonApi, formatApiError } from "@/lib/api";

/** Wave 41 — L1 Auto-Comparison Engine (rule-based lowest-price shortlist). */
export default function L1ComparisonPanel() {
  const [notices, setNotices] = useState([]);
  const [pickedRef, setPickedRef] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=200`)
      .then((r) => r.json()).then((d) => setNotices(d.items || []))
      .catch(() => {});
  }, []);

  const run = async () => {
    if (!pickedRef) { toast.error("Pick a notice"); return; }
    setBusy(true);
    try {
      const r = await comparisonApi.runL1(pickedRef);
      setResult(r);
      toast.success(r.l1_winner
        ? `L1: ${r.l1_winner.company_name} @ ${r.l1_winner.price_currency} ${r.l1_winner.price_amount?.toLocaleString()}`
        : `${r.eligible_count} eligible · no compliant L1 found`);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const flagLabel = (f) => ({
    technical_not_cleared: "Technical envelope not cleared",
    missing_price: "Price missing",
    no_documents: "No documents",
    no_technical_docs: "Missing technical documents",
    no_commercial_docs: "Missing commercial documents",
    above_budget_150pct: "Above 150% of budget",
    suspiciously_low: "Below 40% of budget",
  }[f] || f);

  return (
    <div data-testid="admin-l1-panel">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">
          Rule-based lowest-price shortlist · filters withdrawn / non-cleared bids · flags compliance issues.
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[1fr_auto] mb-6">
        <select value={pickedRef} onChange={(e) => { setPickedRef(e.target.value); setResult(null); }}
                data-testid="l1-notice-picker"
                className="px-4 py-3 border border-brand-navy/20">
          <option value="">— pick a notice —</option>
          {notices.map((n) => (
            <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
          ))}
        </select>
        <button type="button" onClick={run} disabled={!pickedRef || busy}
                data-testid="l1-run"
                className="px-6 py-3 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Running…" : "Run L1 comparison"}
        </button>
      </div>

      {result && (
        <>
          <div className="grid gap-4 md:grid-cols-3 mb-6">
            {["l1_winner", "l2", "l3"].map((k, i) => {
              const r = result[k];
              const label = ["L1 · winner", "L2 · runner-up", "L3 · third"][i];
              return (
                <div key={k} className={`border p-4 ${r ? "border-brand-navy/30 bg-white" : "border-brand-navy/10 bg-brand-pale/50"}`}
                     data-testid={`l1-card-${k}`}>
                  <div className="pmc-label">{label}</div>
                  {r ? (
                    <>
                      <div className="mt-1 text-lg font-semibold text-brand-navy">{r.company_name}</div>
                      <div className="mt-1 font-mono text-xs text-brand-navy/60">{r.bid_ref}</div>
                      <div className="mt-2 font-mono text-2xl text-brand-navy tabular-nums">
                        {r.price_currency} {r.price_amount?.toLocaleString()}
                      </div>
                    </>
                  ) : (
                    <div className="mt-2 text-brand-navy/40 italic">No compliant candidate</div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="border border-brand-navy/10 bg-white">
            <div className="p-3 border-b border-brand-navy/10 bg-brand-pale text-xs uppercase tracking-widest text-brand-navy/70 flex gap-4">
              <span className="w-8">Rank</span>
              <span className="flex-1">Company</span>
              <span className="w-40">Bid ref</span>
              <span className="w-40 text-right">Price</span>
              <span className="w-24 text-center">Compliant?</span>
            </div>
            {result.ranked.length === 0 && (
              <div className="p-6 text-brand-navy/50 text-sm">No eligible bids to rank.</div>
            )}
            {result.ranked.map((r) => (
              <div key={r.bid_id} className={`p-3 border-b border-brand-navy/5 ${!r.compliant ? "bg-amber-50/50" : ""}`}
                   data-testid={`l1-row-${r.rank}`}>
                <div className="flex items-center gap-4">
                  <span className="w-8 font-mono text-brand-navy-soft font-bold">L{r.rank}</span>
                  <span className="flex-1 text-brand-navy font-semibold">{r.company_name}</span>
                  <span className="w-40 font-mono text-xs text-brand-navy/60">{r.bid_ref}</span>
                  <span className="w-40 text-right font-mono tabular-nums text-brand-navy">
                    {r.price_currency} {r.price_amount?.toLocaleString()}
                  </span>
                  <span className="w-24 text-center">
                    {r.compliant
                      ? <span className="text-emerald-700 text-xs uppercase tracking-widest">Yes</span>
                      : <span className="text-amber-700 text-xs uppercase tracking-widest">Flagged</span>}
                  </span>
                </div>
                {r.compliance_flags.length > 0 && (
                  <div className="mt-2 ml-12 flex flex-wrap gap-2">
                    {r.compliance_flags.map((f) => (
                      <span key={f} className="text-[10px] uppercase tracking-widest px-2 py-0.5 border border-amber-400 bg-amber-100 text-amber-900">
                        {flagLabel(f)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {result.ineligible_count > 0 && (
            <div className="mt-6 border border-brand-navy/10 bg-slate-50">
              <div className="p-3 border-b border-brand-navy/10 text-xs uppercase tracking-widest text-brand-navy/60">
                Ineligible ({result.ineligible_count})
              </div>
              {result.ineligible.map((i) => (
                <div key={i.bid_id} className="p-2 text-sm text-brand-navy/70 flex gap-4 border-b border-brand-navy/5">
                  <span className="flex-1">{i.company_name}</span>
                  <span className="font-mono text-xs text-brand-navy/50">{i.bid_ref}</span>
                  <span className="w-40 text-xs text-brand-navy/60 uppercase tracking-widest">{i.reason}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
