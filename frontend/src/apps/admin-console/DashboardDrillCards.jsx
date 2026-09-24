import { useEffect, useState } from "react";
import { toast } from "sonner";
import { dashboardDrillApi } from "@/lib/api";

export function BidRow({ b }) {
  return (
    <tr className="border-t border-brand-navy/10">
      <td className="px-2 py-1 font-mono text-xs">{b.bid_ref || "—"}</td>
      <td className="px-2 py-1 text-xs">{b.vendor}</td>
      <td className="px-2 py-1 text-right font-mono">{(b.price || 0).toLocaleString()} {b.currency}</td>
      <td className="px-2 py-1 text-xs">{b.status || b.reason || ""}</td>
    </tr>
  );
}

export default function DashboardDrillCards() {
  const [anom, setAnom] = useState({ items: [], count: 0 });
  const [pipe, setPipe] = useState({ items: [], count: 0 });
  const [topP, setTopP] = useState({ items: [], count: 0 });
  const [tab, setTab] = useState(null); // "anom" | "pipe" | "top"

  useEffect(() => {
    Promise.allSettled([
      dashboardDrillApi.anomalies(),
      dashboardDrillApi.pipeline(),
      dashboardDrillApi.topPriced(10),
    ]).then(([a, p, t]) => {
      if (a.status === "fulfilled") setAnom(a.value); else toast.error("Anomalies load failed");
      if (p.status === "fulfilled") setPipe(p.value); else toast.error("Pipeline load failed");
      if (t.status === "fulfilled") setTopP(t.value); else toast.error("Top-priced load failed");
    });
  }, []);

  const Card = ({ id, kicker, count, label, hint, active }) => (
    <button type="button" onClick={() => setTab(active ? null : id)}
      data-testid={`drill-card-${id}`}
      className={`text-left border p-4 bg-white transition-colors ${
        active ? "border-brand-navy bg-brand-navy/5"
               : "border-brand-navy/20 hover:border-brand-navy"}`}>
      <div className="pmc-label">{kicker}</div>
      <div className="text-2xl font-serif mt-1">{count}</div>
      <div className="text-xs text-brand-navy/60 mt-1">{label}</div>
      <div className="text-[10px] uppercase tracking-widest mt-2 text-brand-navy/50">{hint}</div>
    </button>
  );

  const rows = tab === "anom" ? anom.items
             : tab === "pipe" ? pipe.items
             : tab === "top"  ? topP.items
             : [];

  return (
    <div className="space-y-4" data-testid="dashboard-drill-cards">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card id="anom" kicker="AI Anomaly" count={anom.count}
              active={tab === "anom"}
              label={anom.count ? "Flagged bids" : "No anomalies detected"}
              hint="Click to see flagged bids" />
        <Card id="pipe" kicker="Pipeline Funnel" count={pipe.count}
              active={tab === "pipe"}
              label="Bids across the pipeline"
              hint="Click to drill through" />
        <Card id="top"  kicker="Top-Priced Bids" count={topP.count}
              active={tab === "top"}
              label="Highest-value submissions"
              hint="Click to see top 10" />
      </div>

      {tab && rows.length > 0 && (
        <div className="border border-brand-navy/10 bg-white overflow-x-auto"
             data-testid="drill-result-table">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white text-[10px] uppercase tracking-widest">
              <tr>
                <th className="px-2 py-2 text-left">Bid</th>
                <th className="px-2 py-2 text-left">Vendor</th>
                <th className="px-2 py-2 text-right">Price</th>
                <th className="px-2 py-2 text-left">{tab === "anom" ? "Reason" : "Status"}</th>
              </tr>
            </thead>
            <tbody>{rows.map((b) => <BidRow key={b.bid_id} b={b} />)}</tbody>
          </table>
        </div>
      )}
      {tab && rows.length === 0 && (
        <div className="border border-brand-navy/10 bg-white p-4 text-sm text-brand-navy/60"
             data-testid="drill-empty">
          {tab === "anom" ? "No AI-flagged bids — the copilot hasn't found any anomalies yet."
                          : "No rows returned for this drill."}
        </div>
      )}
    </div>
  );
}
