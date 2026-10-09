import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, comparisonApi, formatApiError, showApiError} from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";

/** Wave 41 — L1 Auto-Comparison Engine (rule-based lowest-price shortlist). */
export default function L1ComparisonPanel() {
  const [notices, setNotices] = useState([]);
  const [pickedRef, setPickedRef] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Bug #37 fix — v50m. Was `publicApi.listNotices({limit:200})` which only
    // returned PUBLISHED notices; L1 can be run on any notice regardless of
    // publish state (including drafts admin wants to dry-run against). Switch
    // to admin all-notices endpoint and raise the cap.
    adminApi.listAllNotices({ limit: 500 })
      .then((d) => setNotices(d.items || []))
      .catch(() => {});
  }, []);

  const run = async () => {
    if (!pickedRef) { toast.error("Pick a notice"); return; }
    setBusy(true);
    try {
      // Bug #11 fix — hard 45-second timeout so the panel can never "hang".
      // If the backend is slow, we abort with a user-visible error instead.
      const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("L1 comparison timed out — the tender has no compliant bids or the backend is slow. Try again shortly.")), 45000));
      const r = await Promise.race([comparisonApi.runL1(pickedRef), timeout]);
      setResult(r);
      toast.success(r.l1_winner
        ? `L1: ${r.l1_winner.company_name} @ ${r.l1_winner.price_currency} ${r.l1_winner.price_amount?.toLocaleString()}`
        : `${r.eligible_count} eligible · no compliant L1 found`);
    } catch (e) { showApiError(e); }
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
        <label className="text-xs uppercase tracking-widest text-brand-navy/60">
          Notice<InfoDot tip="Which tender to shortlist. The engine will only rank bids on this notice whose technical envelope has been cleared." />
          <select value={pickedRef} onChange={(e) => { setPickedRef(e.target.value); setResult(null); }}
                  data-testid="l1-notice-picker"
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 normal-case tracking-normal">
            <option value="">— pick a notice —</option>
            {notices.map((n) => (
              <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={run} disabled={!pickedRef || busy}
                data-testid="l1-run"
                className="self-end px-6 py-3 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Running…" : "Run L1 comparison"}
          <InfoDot tip="Executes the lowest-price-compliant algorithm. Bids missing docs, above 150% budget or below 40% budget are flagged, not ranked." />
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
            {(result.ranked || []).length === 0 && (
              <div className="p-8 text-brand-navy/60 text-sm text-center border border-dashed border-brand-navy/20"
                   data-testid="l1-empty-state">
                <div className="pmc-label mb-2">No eligible bids to rank</div>
                <div>
                  Reasons a bid may be excluded from L1 ranking:
                </div>
                <ul className="mt-2 text-xs text-brand-navy/60 space-y-1 max-w-md mx-auto text-left list-disc list-inside">
                  <li>Technical envelope not scored yet (two-cover gate)</li>
                  <li>Bid marked non-compliant during evaluation</li>
                  <li>Vendor withdrew before deadline</li>
                  <li>Notice status is not 'evaluation_complete' yet</li>
                </ul>
                <div className="mt-3 text-[11px] text-brand-navy/50">
                  Active ranking rule: lowest compliant commercial price wins (L1). Ties broken by earlier submission.
                </div>
              </div>
            )}
            {(result.ranked || []).map((r) => (
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
                {(r.compliance_flags || []).length > 0 && (
                  <div className="mt-2 ml-12 flex flex-wrap gap-2">
                    {(r.compliance_flags || []).map((f) => (
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
              {(result.ineligible || []).map((i) => (
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
