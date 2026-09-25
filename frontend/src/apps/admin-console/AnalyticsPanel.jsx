import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { analyticsApi, bidApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import DashboardDrillCards from "./DashboardDrillCards";
import { InfoDot } from "@/components/InfoDot";

export default function AnalyticsPanel() {
  const { t: tt } = useI18n();
  const nav = useNavigate();
  const go = (tab) => nav(`/admin?tab=${tab}`);
  const [data, setData] = useState(null);
  const [anomaly, setAnomaly] = useState(null);
  const [bidId, setBidId] = useState("");
  const [bids, setBids] = useState([]);

  const load = useCallback(async () => {
    try {
      const [d, b] = await Promise.all([
        analyticsApi.dashboard(),
        bidApi.list().catch(() => []),
      ]);
      setData(d); setBids(b);
    } catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const runAnomaly = async () => {
    if (!bidId) return toast.error(tt("panels.analytics.pick_bid_toast"));
    try {
      const r = await analyticsApi.bidAnomaly(bidId);
      setAnomaly(r);
    } catch (e) { showApiError(e); }
  };

  if (!data) return <div className="p-6 text-slate-500 text-sm">{tt("panels.analytics.loading")}</div>;
  const t = data.totals || {};
  return (
    <div data-testid="admin-analytics-panel" className="space-y-6">
      <DashboardDrillCards />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          [tt("panels.analytics.kpi_published_notices"), t.published_notices, "/" + t.notices, "notices"],
          [tt("panels.analytics.kpi_vendors"), t.vendors, "", "vendors"],
          [tt("panels.analytics.kpi_bids"), t.bids, "", "bidding"],
          [tt("panels.analytics.kpi_awarded"), t.awarded, "", "awards"],
          [tt("panels.analytics.kpi_pending_emd"), t.pending_emd, "", "escrow"],
          [tt("panels.analytics.kpi_emd_collected"), (t.emd_collected || 0).toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }), "", "billing"],
          [tt("panels.analytics.kpi_active_contracts"), t.active_contracts, "", "boq"],
        ].map(([label, val, suf, target]) => (
          <button key={label} type="button" onClick={() => go(target)}
            title={`Open ${label}`}
            className="bg-white border p-4 text-left cursor-pointer transition-colors hover:border-brand-navy hover:bg-brand-navy/5 group"
            data-testid={`kpi-${label.toLowerCase().replace(/ /g, "-")}`}>
            <div className="text-xs text-slate-500 uppercase tracking-widest group-hover:text-brand-navy">{label}</div>
            <div className="text-2xl font-serif mt-1">{val ?? "—"}<span className="text-xs text-slate-400">{suf}</span></div>
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/0 group-hover:text-brand-navy-soft mt-1 transition-colors">Open →</div>
          </button>
        ))}
      </div>

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">{tt("panels.analytics.funnel_title")}</div>
        {/* Bug #79 fix — mobile overlap. 4 cols was too tight for long
            stage labels like "certifier_cleared"; use 2/4/8 responsive
            steps and let labels wrap. */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-xs">
          {Object.entries(data.funnel || {}).map(([k, v]) => (
            <button key={k} type="button" onClick={() => go("bidding")}
              title="Open bid pipeline"
              className="border p-2 text-center min-w-0 cursor-pointer hover:border-brand-navy hover:bg-brand-navy/5 transition-colors"
              data-testid={`funnel-stage-btn-${k}`}>
              <div className="text-slate-500 break-words leading-tight" data-testid={`funnel-stage-${k}`}>{k}</div>
              <div className="text-lg mt-1">{v}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">{tt("panels.analytics.top_bids_title")}</div>
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500">
            <tr><th className="text-left">{tt("panels.analytics.col_bid")}</th><th className="text-left">{tt("panels.analytics.col_vendor")}</th>
              <th className="text-right">{tt("panels.analytics.col_price")}</th><th className="text-left">{tt("panels.analytics.col_status")}</th></tr>
          </thead>
          <tbody>
            {data.top_bids?.map((b) => (
              <tr key={b.bid_ref} className="border-t cursor-pointer hover:bg-brand-navy/5"
                onClick={() => go("bidding")} title="Open bid pipeline"
                data-testid={`top-bid-row-${b.bid_ref}`}>
                <td className="py-1 font-mono text-xs">{b.bid_ref}</td>
                <td className="py-1">{b.vendor}</td>
                <td className="py-1 text-right">{(b.price || 0).toLocaleString()}</td>
                <td className="py-1 text-xs">{b.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">{tt("panels.analytics.ai_anomaly_title")}</div>
        <div className="flex gap-2 items-end">
          <label className="flex-1">
            <span className="text-xs">{tt("panels.analytics.bid_label")}<InfoDot tip="Which bid to run the AI anomaly-detector against. Only bids with a commercial envelope are eligible." /></span>
            <select value={bidId} onChange={(e) => setBidId(e.target.value)}
              className="mt-1 w-full px-3 py-2 border" data-testid="anomaly-bid-select">
              <option value="">{tt("panels.analytics.select_bid")}</option>
              {bids.map((b) => (
                <option key={b.id} value={b.id}>{b.bid_ref} — {b.company_name} — {b.price_amount}</option>
              ))}
            </select>
          </label>
          <button onClick={runAnomaly} data-testid="anomaly-run"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            {tt("panels.analytics.run_ai_check")}
            <InfoDot tip="Runs Emergent LLM copilot: compares bid price to peer distribution and vendor's history to flag potential collusion or dumping." />
          </button>
        </div>
        {anomaly && (
          <div className="mt-3 p-3 bg-slate-50 border text-sm" data-testid="anomaly-result">
            <div>{tt("panels.analytics.anomaly_score")}: <strong>{anomaly.score}%</strong> · {tt("panels.analytics.deviation")} {anomaly.deviation_pct}%</div>
            {anomaly.flags?.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-red-700 text-xs">
                {anomaly.flags.map((f, i) => <li key={`anom-${f}-${i}`}>{f}</li>)}
              </ul>
            )}
            {anomaly.narrative && (
              <div className="mt-2 text-xs text-slate-600 italic">{anomaly.narrative}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
