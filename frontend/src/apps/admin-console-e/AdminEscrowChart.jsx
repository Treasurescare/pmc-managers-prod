/**
 * AdminEscrowChart — v52f. Admin cross-institution version of
 * EscrowDashboardChart with a multi-select institution filter (all /
 * pick any subset of approved institutions). Mounted inside the
 * admin Escrow institutions page.
 */
import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, PieChart, Pie, Cell,
} from "recharts";
import { api, showApiError } from "@/lib/api";

const COLORS = ["#0F3B2E", "#B08E4A", "#5A5A57", "#8B2E2E",
                 "#2E5A8B", "#2E8B5A", "#8B5A2E", "#5A2E8B"];

export default function AdminEscrowChart() {
  const [picked, setPicked] = useState([]); // ids; [] = all
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/api/v1/escrow/admin/chart",
             { params: { institution_ids: picked.length ? picked.join(",") : undefined, months: 12 } })
      .then((r) => setData(r.data))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [picked]);

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

  const toggle = (id) => setPicked((p) =>
    p.includes(id) ? p.filter((x) => x !== id) : [...p, id]);

  const hasData = flat.months.some((m) => flat.currencies.some((c) => m[c] > 0));

  return (
    <div className="bg-white border border-brand-navy/15 p-5"
         data-testid="admin-escrow-chart">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="font-serif text-lg text-brand-navy">
          Escrow volume · last 12 months
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-brand-navy/60">
            {picked.length === 0 ? "All approved institutions" : `${picked.length} selected`}
          </span>
          {picked.length > 0 && (
            <button type="button" onClick={() => setPicked([])}
                    data-testid="admin-escrow-chart-clear"
                    className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-pale">
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-1 max-h-20 overflow-auto"
           data-testid="admin-escrow-chart-picker">
        {(data?.all_approved || []).map((i) => {
          const on = picked.includes(i.id);
          return (
            <button key={i.id} type="button" onClick={() => toggle(i.id)}
                    data-testid={`admin-escrow-chart-pick-${i.id}`}
                    className={"px-2 py-1 text-[10px] uppercase tracking-widest border " +
                                (on
                                   ? "bg-brand-navy text-white border-brand-navy"
                                   : "bg-white text-brand-navy border-brand-navy/20 hover:bg-brand-pale")}>
              {i.legal_name}
            </button>
          );
        })}
        {(data?.all_approved || []).length === 0 && (
          <span className="text-xs text-brand-navy/50">No approved institutions yet.</span>
        )}
      </div>

      {loading && (
        <div className="h-56 flex items-center justify-center text-sm text-brand-navy/50">Loading…</div>
      )}
      {!loading && !hasData && (
        <div className="h-56 flex items-center justify-center text-sm text-brand-navy/50"
             data-testid="admin-escrow-chart-empty">
          No transaction history for the current selection.
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
