/**
 * EscrowDashboardChart — v52f. Monthly transaction volume line chart +
 * currency breakdown pie, with an account picker (all / specific). Used
 * on the signed-in escrow institution dashboard; a lighter admin variant
 * sits on the admin pipeline page.
 *
 * Backend: GET /api/v1/escrow-accounts/me/chart?account_id=all|<id>&months=12
 * Returns { series:[{month,volume_by_currency:{USD:N,EUR:M,...}}], accounts:[], institution:{} }
 */
import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, PieChart, Pie, Cell,
} from "recharts";
import { api, showApiError } from "@/lib/api";

const COLORS = ["#0F3B2E", "#B08E4A", "#5A5A57", "#8B2E2E",
                 "#2E5A8B", "#2E8B5A", "#8B5A2E", "#5A2E8B"];

export default function EscrowDashboardChart() {
  const [accountFilter, setAccountFilter] = useState("all");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/api/v1/escrow-accounts/me/chart",
             { params: { account_id: accountFilter, months: 12 } })
      .then((r) => setData(r.data))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [accountFilter]);

  const flat = useMemo(() => {
    if (!data?.series) return { months: [], currencies: [], pie: [] };
    const currencies = new Set();
    data.series.forEach((m) => Object.keys(m.volume_by_currency || {}).forEach((c) => currencies.add(c)));
    const cList = Array.from(currencies);
    const months = data.series.map((m) => {
      const row = { month: m.month };
      cList.forEach((c) => { row[c] = m.volume_by_currency?.[c] || 0; });
      return row;
    });
    const totals = {};
    data.series.forEach((m) => {
      Object.entries(m.volume_by_currency || {}).forEach(([c, v]) => {
        totals[c] = (totals[c] || 0) + v;
      });
    });
    const pie = Object.entries(totals).map(([name, value]) => ({ name, value }));
    return { months, currencies: cList, pie };
  }, [data]);

  const hasData = flat.months.some((m) => flat.currencies.some((c) => m[c] > 0));

  return (
    <div className="bg-white border border-brand-navy/15 p-5"
         data-testid="escrow-dashboard-chart">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="font-serif text-lg text-brand-navy">
          Transaction volume · last 12 months
        </h2>
        <select value={accountFilter}
                onChange={(e) => setAccountFilter(e.target.value)}
                data-testid="escrow-chart-account-filter"
                className="px-3 py-1.5 text-xs border border-brand-navy/20 bg-white">
          <option value="all">All joint accounts</option>
          {(data?.accounts || []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} · {a.currency}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="h-56 flex items-center justify-center text-sm text-brand-navy/50">
          Loading chart…
        </div>
      )}

      {!loading && !hasData && (
        <div className="h-56 flex items-center justify-center text-sm text-brand-navy/50"
             data-testid="escrow-chart-empty">
          No transaction history yet. The chart populates once PMC opens a
          joint escrow account with your institution and EMD starts flowing.
        </div>
      )}

      {!loading && hasData && (
        <div className="grid gap-6 md:grid-cols-5">
          <div className="md:col-span-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={flat.months} margin={{ top: 10, right: 8, bottom: 0, left: -8 }}>
                <CartesianGrid stroke="#B08E4A22" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {flat.currencies.map((c, i) => (
                  <Line key={c} type="monotone" dataKey={c}
                        stroke={COLORS[i % COLORS.length]} strokeWidth={2}
                        dot={{ r: 3 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="md:col-span-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={flat.pie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                     outerRadius={70} label={{ fontSize: 10 }}>
                  {flat.pie.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
