/**
 * StakeholderReportsPanel — G4 rebuild.
 *
 * Four live stakeholder reports keyed off the platform's real collections:
 *   1. Tenders   — pipeline snapshot per notice
 *   2. Awards    — awarded bids with PO number + contract value
 *   3. Escrow    — accounts + transactions with aging + SLA breach flag
 *   4. SLA       — active contracts + milestone hit-rate + variation orders
 *
 * Every report is available inline (JSON → table) *and* as a CSV download so
 * stakeholders can circulate the file without needing portal access.
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;
const REPORTS = [
  { id: "tenders", label: "Tenders" },
  { id: "awards",  label: "Awards" },
  { id: "escrow",  label: "Escrow" },
  { id: "sla",     label: "SLA / Contracts" },
];

function Table({ rows, columns }) {
  if (!rows?.length) return (
    <div className="p-6 text-center text-brand-navy/50 text-sm">No rows.</div>
  );
  return (
    <div className="overflow-x-auto border border-brand-navy/10">
      <table className="w-full text-sm">
        <thead className="bg-brand-navy text-white text-[10px] uppercase tracking-widest">
          <tr>{columns.map((c) => <th key={c} className="px-3 py-2 text-left">{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-brand-navy/10">
              {columns.map((c) => (
                <td key={c} className="px-3 py-2 align-top text-xs">
                  {typeof r[c] === "boolean" ? (r[c] ? "✓" : "—") : String(r[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function StakeholderReportsPanel() {
  const [tab, setTab] = useState("tenders");
  const [data, setData] = useState({ items: [], count: 0 });
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/stakeholder-reports/${tab}`,
                            { credentials: "include" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) { toast.error(`Load failed: ${e.message}`); }
    finally { setLoading(false); }
  }, [tab]);

  useEffect(() => { reload(); }, [reload]);

  const downloadCsv = () => {
    window.open(`${API}/api/v1/stakeholder-reports/${tab}?format=csv`, "_blank",
                "noopener");
  };

  const rows =
    tab === "escrow" ? [...(data.accounts || []), ...(data.transactions || [])]
                     : data.items || [];
  const columns = rows[0] ? Object.keys(rows[0]) : [];

  return (
    <div className="space-y-6" data-testid="stakeholder-reports-panel">
      <section>
        <div className="pmc-label">Governance G4 · Stakeholder Reports</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">
          Tenders · Awards · Escrow · SLAs
        </h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
          Live snapshots of every substantive workflow. Each report is streamable
          to CSV — stakeholders can circulate the file without portal access.
        </p>
      </section>

      <div className="flex flex-wrap items-center gap-2">
        {REPORTS.map((r) => (
          <button key={r.id} onClick={() => setTab(r.id)}
                  data-testid={`stakeholder-tab-${r.id}`}
                  className={`px-4 py-1.5 text-[11px] uppercase tracking-widest border ${
                    tab === r.id ? "bg-brand-navy text-white border-brand-navy"
                                  : "text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy"}`}>
            {r.label}
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={downloadCsv} data-testid="stakeholder-download-csv"
                className="px-4 py-2 text-[11px] uppercase tracking-widest border-2 border-emerald-500 text-emerald-700 hover:bg-emerald-50">
          ⬇ Download CSV
        </button>
      </div>

      {tab === "escrow" && data.sla_threshold_days && (
        <div className="border border-amber-500 bg-amber-50 p-3 text-sm text-amber-900"
             data-testid="stakeholder-escrow-sla">
          SLA threshold: <b>{data.sla_threshold_days} days</b> · SLA breaches:
          <b className={data.sla_breaches ? " text-red-700" : " text-emerald-700"}>
            {" "}{data.sla_breaches || 0}
          </b>
        </div>
      )}

      {loading ? (
        <div className="text-brand-navy/60 py-10 text-center">Loading…</div>
      ) : (
        <Table rows={rows} columns={columns} />
      )}

      <div className="text-xs text-brand-navy/50">
        Generated at {data.generated_at || "—"} · {rows.length} rows
      </div>
    </div>
  );
}
