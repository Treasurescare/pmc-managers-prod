import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { analyticsApi, bidApi, formatApiError } from "@/lib/api";

export default function AnalyticsPanel() {
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
    } catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const runAnomaly = async () => {
    if (!bidId) return toast.error("Pick a bid");
    try {
      const r = await analyticsApi.bidAnomaly(bidId);
      setAnomaly(r);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!data) return <div className="p-6 text-slate-500 text-sm">Loading dashboard…</div>;
  const t = data.totals || {};
  return (
    <div data-testid="admin-analytics-panel" className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ["Published Notices", t.published_notices, "/" + t.notices],
          ["Vendors", t.vendors, ""],
          ["Bids", t.bids, ""],
          ["Awarded", t.awarded, ""],
          ["Pending EMD", t.pending_emd, ""],
          ["EMD Collected", (t.emd_collected || 0).toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }), ""],
          ["Active Contracts", t.active_contracts, ""],
        ].map(([label, val, suf]) => (
          <div key={label} className="bg-white border p-4" data-testid={`kpi-${label.toLowerCase().replace(/ /g, "-")}`}>
            <div className="text-xs text-slate-500 uppercase tracking-widest">{label}</div>
            <div className="text-2xl font-serif mt-1">{val ?? "—"}<span className="text-xs text-slate-400">{suf}</span></div>
          </div>
        ))}
      </div>

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">Pipeline funnel</div>
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2 text-xs">
          {Object.entries(data.funnel || {}).map(([k, v]) => (
            <div key={k} className="border p-2 text-center">
              <div className="text-slate-500">{k}</div>
              <div className="text-lg">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">Top-priced bids</div>
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500">
            <tr><th className="text-left">Bid</th><th className="text-left">Vendor</th>
              <th className="text-right">Price</th><th className="text-left">Status</th></tr>
          </thead>
          <tbody>
            {data.top_bids?.map((b) => (
              <tr key={b.bid_ref} className="border-t">
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
        <div className="pmc-label mb-2">AI Bid Anomaly Check</div>
        <div className="flex gap-2 items-end">
          <label className="flex-1">
            <span className="text-xs">Bid</span>
            <select value={bidId} onChange={(e) => setBidId(e.target.value)}
              className="mt-1 w-full px-3 py-2 border" data-testid="anomaly-bid-select">
              <option value="">Select bid…</option>
              {bids.map((b) => (
                <option key={b.id} value={b.id}>{b.bid_ref} — {b.company_name} — {b.price_amount}</option>
              ))}
            </select>
          </label>
          <button onClick={runAnomaly} data-testid="anomaly-run"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            Run AI Check
          </button>
        </div>
        {anomaly && (
          <div className="mt-3 p-3 bg-slate-50 border text-sm" data-testid="anomaly-result">
            <div>Anomaly score: <strong>{anomaly.score}%</strong> · Deviation {anomaly.deviation_pct}%</div>
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
