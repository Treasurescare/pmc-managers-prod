import { useEffect, useState } from "react";
import { toast } from "sonner";
import { TrendingUp, Award, DollarSign, Clock, ShieldOff } from "lucide-react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";

function Kpi({ icon: Icon, label, value, sub, testid, tone = "default" }) {
  const toneClass = {
    default: "border-foreground/20",
    good: "border-l-4 border-l-success",
    warn: "border-l-4 border-l-warning",
    bad: "border-l-4 border-l-destructive",
    primary: "border-l-4 border-l-primary",
  }[tone];
  return (
    <div className={`border ${toneClass} bg-white p-5`} data-testid={testid}>
      <div className="flex items-start justify-between">
        <div>
          <div className="pmc-label">{label}</div>
          <div className="font-serif text-3xl mt-2">{value}</div>
          {sub && <div className="text-xs text-muted-foreground mt-1 font-mono">{sub}</div>}
        </div>
        {Icon && <Icon className="h-5 w-5 text-muted-foreground" />}
      </div>
    </div>
  );
}

export default function VendorKpi() {
  const [kpi, setKpi] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/vendor/kpi"); setKpi(data); }
      catch (e) { toast.error(formatApiError(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <DashboardLayout title="Performance"><div className="pmc-progress" /></DashboardLayout>;
  if (!kpi) return <DashboardLayout title="Performance"><div className="p-6">No data.</div></DashboardLayout>;

  const total = kpi.total_bids || 0;
  const winTone = kpi.win_rate >= 30 ? "good" : kpi.win_rate >= 10 ? "warn" : "bad";

  return (
    <DashboardLayout title="Vendor Performance" subtitle="Your bidding scorecard on the PMC Global Tender Board">
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="vendor-kpi-grid">
        <Kpi icon={Award} label="Win rate" value={`${kpi.win_rate}%`} sub={`${kpi.awarded} awarded / ${total} bids`} testid="kpi-win-rate" tone={winTone} />
        <Kpi icon={TrendingUp} label="Total bids" value={total} sub={`${kpi.submitted} pending · ${kpi.rejected} lost`} testid="kpi-total-bids" tone="primary" />
        <Kpi icon={DollarSign} label="Avg. bid price" value={kpi.avg_price_amount ? `$${Number(kpi.avg_price_amount).toLocaleString()}` : "—"} sub="Across all your submitted bids" testid="kpi-avg-price" />
        <Kpi icon={Clock} label="Avg. delivery quoted" value={kpi.avg_delivery_days ? `${kpi.avg_delivery_days} days` : "—"} sub="Your median promise" testid="kpi-avg-delivery" />
      </div>

      <div className="grid md:grid-cols-2 gap-4 mt-4">
        <Kpi icon={ShieldOff} label="EMD forfeitures" value={kpi.emd_forfeited} sub={`${kpi.emd_refunded} refunded successfully`} testid="kpi-emd" tone={kpi.emd_forfeited > 0 ? "bad" : "good"} />
        <div className="border bg-white p-5" data-testid="kpi-by-category">
          <div className="pmc-label">Top categories · last 12 months</div>
          {(kpi.by_category || []).length === 0 ? (
            <div className="text-sm text-muted-foreground mt-4">No bids in the last year.</div>
          ) : (
            <ul className="mt-3 space-y-2">
              {kpi.by_category.map((c) => {
                const pct = c.bids ? Math.round((c.wins / c.bids) * 100) : 0;
                return (
                  <li key={c.category} className="text-sm" data-testid={`kpi-cat-${c.category?.replace(/\s+/g, '_')}`}>
                    <div className="flex items-center justify-between">
                      <span>{c.category}</span>
                      <span className="font-mono text-xs">{c.wins}/{c.bids} · {pct}%</span>
                    </div>
                    <div className="h-1.5 bg-muted mt-1">
                      <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="border mt-6 p-5 bg-white" data-testid="kpi-tips">
        <div className="pmc-label text-primary">Suggestions to improve</div>
        <ul className="mt-3 space-y-2 text-sm text-foreground/80 list-disc list-inside">
          {kpi.win_rate < 20 && <li>Your win rate is low — consider revisiting pricing on repeat categories.</li>}
          {kpi.avg_delivery_days > 45 && <li>Average delivery quote is high — faster turnarounds win more contracts.</li>}
          {kpi.emd_forfeited > 0 && <li>You have forfeited EMDs — always confirm you can meet post-award commitments before bidding.</li>}
          {total === 0 && <li>No bids yet. Head to <strong>Open Tenders</strong> in the sidebar to submit your first proposal.</li>}
          {total > 0 && kpi.win_rate >= 30 && <li>Strong win rate. Keep an eye on the Q&A section — timely clarifications signal seriousness to buyers.</li>}
        </ul>
      </div>
    </DashboardLayout>
  );
}
