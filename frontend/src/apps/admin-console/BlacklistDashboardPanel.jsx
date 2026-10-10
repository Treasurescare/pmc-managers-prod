import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { vendorIntelApi, showApiError } from "@/lib/api";

/**
 * v51bd — Admin triage dashboard for every blacklisted vendor.
 * Shows reason, blacklist date, evidence count, total appeals + pending
 * appeals. Clicking a row opens the full VendorIntelPanel manage modal
 * (via a parent callback) so compliance can act in one click.
 */
export default function BlacklistDashboardPanel({ onOpenVendor }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all"); // all | pending | untouched | with_evidence

  const load = () => {
    setLoading(true);
    vendorIntelApi.blacklistDashboard()
      .then(setRows)
      .catch((e) => showApiError(e, { fallbackTitle: "Could not load dashboard" }))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (q && !(
        (r.company_name || "").toLowerCase().includes(q)
        || (r.vendor_ref || "").toLowerCase().includes(q)
        || (r.email || "").toLowerCase().includes(q)
      )) return false;
      if (filter === "pending" && (r.pending_appeal_count || 0) === 0) return false;
      if (filter === "untouched" && (r.evidence_count || 0) !== 0) return false;
      if (filter === "with_evidence" && (r.evidence_count || 0) === 0) return false;
      return true;
    });
  }, [rows, search, filter]);

  const kpi = useMemo(() => ({
    total: rows.length,
    pending: rows.reduce((a, r) => a + (r.pending_appeal_count || 0), 0),
    with_evidence: rows.filter((r) => (r.evidence_count || 0) > 0).length,
    appeals: rows.reduce((a, r) => a + (r.appeal_count || 0), 0),
  }), [rows]);

  const Pill = ({ label, value, tone = "slate", testId }) => (
    <div className={`border px-3 py-2 bg-white border-${tone}-200`} data-testid={testId}>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-xl font-serif text-${tone}-700`}>{value}</div>
    </div>
  );

  const fmt = (iso) => (iso || "").slice(0, 19).replace("T", " ");

  return (
    <div data-testid="blacklist-dashboard-panel" className="bg-white border">
      <div className="px-3 py-3 border-b flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[240px]">
          <div className="pmc-label mb-1">Compliance · blacklist triage</div>
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by company, email, vendor ref…"
            data-testid="bld-search"
            className="w-full px-3 py-2 border border-slate-300 text-sm" />
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}
          className="px-3 py-2 border border-slate-300 text-sm bg-white"
          data-testid="bld-filter">
          <option value="all">All ({rows.length})</option>
          <option value="pending">Pending appeals</option>
          <option value="with_evidence">With admin evidence</option>
          <option value="untouched">No evidence yet</option>
        </select>
        <button type="button" onClick={load}
          className="px-3 py-2 text-[11px] uppercase tracking-widest border border-slate-800 text-slate-800 hover:bg-slate-800 hover:text-white"
          data-testid="bld-refresh">Refresh</button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 p-3 bg-slate-50 border-b">
        <Pill label="Blacklisted" value={kpi.total} testId="bld-kpi-total" />
        <Pill label="Pending appeals" value={kpi.pending} tone="amber" testId="bld-kpi-pending" />
        <Pill label="With evidence" value={kpi.with_evidence} tone="emerald" testId="bld-kpi-evidence" />
        <Pill label="Total appeals" value={kpi.appeals} testId="bld-kpi-appeals" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[840px]">
          <thead className="text-xs text-slate-600 bg-slate-50 border-b">
            <tr>
              <th className="text-left px-3 py-2">Vendor</th>
              <th className="text-left px-3 py-2">Ref</th>
              <th className="text-left px-3 py-2">Reason</th>
              <th className="text-left px-3 py-2">Blacklisted</th>
              <th className="px-3 py-2">Evidence</th>
              <th className="px-3 py-2">Appeals</th>
              <th className="px-3 py-2">Pending</th>
              <th className="px-3 py-2">Latest appeal</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="p-6 text-center text-slate-500">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={9} className="p-6 text-center text-slate-500">
                {rows.length === 0 ? "No vendors on the blacklist." : "No matches with current filters."}
              </td></tr>
            ) : filtered.map((r) => (
              <tr key={r.vendor_ref} className="border-t hover:bg-slate-50"
                  data-testid={`bld-row-${r.vendor_ref}`}>
                <td className="px-3 py-2">
                  <div className="font-medium text-slate-800">{r.company_name || "—"}</div>
                  <div className="text-[11px] text-slate-500">{r.email || ""}</div>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{r.vendor_ref}</td>
                <td className="px-3 py-2 text-xs text-slate-700 max-w-[260px] truncate" title={r.reason}>
                  {r.reason || "—"}
                </td>
                <td className="px-3 py-2 text-xs text-slate-600">{fmt(r.blacklisted_at)}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`inline-block min-w-[28px] px-2 py-0.5 border text-xs ${
                    (r.evidence_count || 0) > 0 ? "border-emerald-500 text-emerald-700" : "border-slate-300 text-slate-500"
                  }`}>{r.evidence_count || 0}</span>
                </td>
                <td className="px-3 py-2 text-center text-xs">{r.appeal_count || 0}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`inline-block min-w-[28px] px-2 py-0.5 border text-xs ${
                    (r.pending_appeal_count || 0) > 0 ? "border-amber-500 text-amber-700 bg-amber-50 font-semibold" : "border-slate-300 text-slate-400"
                  }`} data-testid={`bld-pending-${r.vendor_ref}`}>
                    {r.pending_appeal_count || 0}
                  </span>
                </td>
                <td className="px-3 py-2 text-[11px] text-slate-600">
                  {fmt(r.latest_appeal_at) || "—"}
                  {r.latest_appeal_status && (
                    <span className="ml-1 text-slate-400">· {r.latest_appeal_status}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <button type="button"
                    onClick={() => onOpenVendor?.(r)}
                    data-testid={`bld-manage-${r.vendor_ref}`}
                    className="text-[11px] uppercase tracking-widest px-2 py-1 border border-slate-800 text-slate-800 hover:bg-slate-800 hover:text-white">
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
